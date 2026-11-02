"""Repeat-run measurement of a command: wall time, per-child peak RSS, output hash.

A speed-up only counts when the command's stdout is byte-identical to the baseline's.
No single run is called an improvement; the report states repeat count and spread.
"""
from __future__ import annotations

import hashlib
import os
import statistics
import subprocess
import tempfile
import time
from pathlib import Path


def _one(argv: list[str], timeout: float, cwd: Path | None) -> dict:
    with tempfile.TemporaryFile() as out:
        start = time.perf_counter()
        try:
            proc = subprocess.Popen(argv, stdout=out, stderr=subprocess.DEVNULL, cwd=cwd, start_new_session=True)
        except OSError as exc:
            return {"error": str(exc), "exit": -1, "seconds": 0.0, "max_rss_kb": 0, "stdout_sha256": "", "stdout_bytes": 0}
        deadline = start + timeout
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                break
            if time.perf_counter() > deadline:
                try:
                    os.killpg(proc.pid, 9)
                except OSError:
                    proc.kill()
                os.wait4(proc.pid, 0)
                proc.returncode = -9
                return {"timeout": True, "seconds": timeout}
            time.sleep(0.001)
        seconds = time.perf_counter() - start
        proc.returncode = os.waitstatus_to_exitcode(status)
        out.seek(0)
        digest, size = hashlib.sha256(), 0
        for chunk in iter(lambda: out.read(1 << 20), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"seconds": seconds, "exit": proc.returncode, "max_rss_kb": usage.ru_maxrss,
            "stdout_sha256": digest.hexdigest(), "stdout_bytes": size}


def measure(argv: list[str], repeat: int = 5, warmup: int = 1, timeout: float = 300, label: str = "run",
            cwd: Path | None = None, baseline: dict | None = None) -> dict:
    if not 1 <= repeat <= 100 or not 0 <= warmup <= 10:
        raise ValueError("repeat must be 1..100 and warmup 0..10")
    for _ in range(warmup):
        _one(argv, timeout, cwd)
    runs = [_one(argv, timeout, cwd) for _ in range(repeat)]
    report: dict = {"label": label, "argv": argv, "cwd": str(cwd) if cwd else os.getcwd(), "repeat": repeat, "warmup": warmup,
                    "platform": os.uname().sysname, "runs": runs}
    if any(r.get("timeout") for r in runs):
        report.update(status="timeout")
        return report
    secs = [r["seconds"] for r in runs]
    report["seconds"] = {"min": min(secs), "median": statistics.median(secs), "max": max(secs),
                         "stdev": statistics.pstdev(secs) if len(secs) > 1 else 0.0}
    report["max_rss_kb"] = max(r["max_rss_kb"] for r in runs)
    if any("error" in r for r in runs):
        report.update(status="failed", reason=runs[0]["error"])
        return report
    report["exit_codes"] = sorted({r["exit"] for r in runs})
    hashes = {r["stdout_sha256"] for r in runs}
    report["output_stable"] = len(hashes) == 1
    report["stdout_sha256"] = runs[0]["stdout_sha256"] if len(hashes) == 1 else None
    if report["exit_codes"] != [0] or not report["output_stable"]:
        report["status"] = "failed"
        report["reason"] = "non-zero exit or nondeterministic stdout: not a valid measurement"
        return report
    if baseline is None:
        report["status"] = "baseline"
        return report
    if baseline.get("status") not in {"baseline", "ok"} or "seconds" not in baseline or not baseline.get("stdout_sha256"):
        report.update(status="invalid_baseline", reason="baseline file is not a successful measurement")
        return report
    if baseline.get("argv") != argv or baseline.get("cwd") != report["cwd"]:
        report.update(status="invalid_baseline", reason="baseline was measured with a different command or cwd")
        return report
    if baseline.get("stdout_sha256") != report["stdout_sha256"]:
        report.update(status="output_changed", reason="stdout differs from baseline: optimization changed behavior = FAIL")
        return report
    b = baseline["seconds"]["median"]
    report["comparison"] = {"baseline_label": baseline.get("label"), "baseline_median_s": b,
                            "median_ratio": report["seconds"]["median"] / b if b else None,
                            "baseline_max_rss_kb": baseline.get("max_rss_kb"), "baseline_repeat": baseline.get("repeat"),
                            "distinguishable": report["seconds"]["max"] < baseline["seconds"]["min"] or report["seconds"]["min"] > baseline["seconds"]["max"]}
    report["status"] = "ok"
    report["caveat"] = "same machine/input only; if distinguishable=false the difference is within run-to-run noise"
    return report
