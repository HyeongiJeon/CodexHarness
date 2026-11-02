"""One-command session launcher for the five specialist modes.

Everything here runs BEFORE Codex starts: it resolves paths, links skills, picks
routing from observed evidence and builds the launch command. It never edits
user/managed Codex configuration, authentication or permissions, and it never
claims a configuration applies to an already running session.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from .install import install_skills
from .roles import ROOT, ROLES, launch_overrides

STATE_ROOT = ROOT / ".harness" / "sessions"
BASE_DEV = ["requirement-discovery", "completion-verification", "decision-and-evidence-recording",
            "independent-code-review", "parallel-implementation", "rapid-mvp-development", "systematic-debugging"]
WEB = ["web-application-development", "web-runtime-debugging", "web-flow-verification", "web-ui-patterns", "frontend-design"]

MODES = {
    "dev": {"skills": BASE_DEV, "doc": "sessions/dev.md", "writes_project": True,
            "purpose": "collaborative development with the specialist agent team"},
    "explain": {"skills": [], "doc": "sessions/explain.md", "writes_project": False, "sandbox": "read-only",
                "purpose": "read-only explanation of the existing system"},
    "optimize": {"skills": ["performance-optimization", "completion-verification", "systematic-debugging",
                            "decision-and-evidence-recording"], "doc": "sessions/optimize.md", "writes_project": True,
                 "isolate": True, "purpose": "measured algorithm/performance optimization in an isolated worktree"},
    "qa": {"skills": ["completion-verification", "independent-code-review", "web-flow-verification",
                      "systematic-debugging", "decision-and-evidence-recording"], "doc": "sessions/qa.md",
           "writes_project": True, "purpose": "QA lead; tests and reports defects, does not fix product code"},
    "preview": {"skills": ["web-runtime-debugging", "web-flow-verification", "systematic-debugging"],
                "doc": "sessions/preview.md", "writes_project": True,
                "purpose": "layered diagnosis of web server / preview failures"},
}


def find_project(arg: Path | None, cwd: Path | None = None) -> Path:
    """Explicit --project wins; otherwise the git root (or cwd) of the caller. Never the harness itself."""
    cwd = (cwd or Path.cwd()).resolve()
    if arg is None and STATE_ROOT in cwd.parents:  # inside an OPTIMIZE worktree: the project is the recorded original
        marker = STATE_ROOT / cwd.relative_to(STATE_ROOT).parts[0] / "project.txt"
        if marker.is_file():
            return Path(marker.read_text().strip())
    if arg is not None:
        project = Path(arg).expanduser().resolve()
        if not project.is_dir():
            raise ValueError(f"--project is not a directory: {project}")
    else:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True)
        project = Path(top.stdout.strip()).resolve() if top.returncode == 0 and top.stdout.strip() else cwd
    if project == ROOT or ROOT in project.parents:
        raise ValueError("project resolves to the CodexHarness repository itself; run from your task project "
                         "or pass --project <task project root>")
    return project


def detect_stack(project: Path) -> set[str]:
    """Cheap, bounded hint used only to choose skills; never authoritative."""
    found: set[str] = set()
    seen = 0
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".agents"}
    stack = [project]
    while stack and seen < 2000:
        try:
            entries = list(stack.pop().iterdir())
        except OSError:
            continue
        for item in entries:
            seen += 1
            if item.is_dir():
                if item.name not in skip and not item.name.startswith(".") and len(item.relative_to(project).parts) < 3:
                    stack.append(item)
                continue
            name, suffix = item.name.lower(), item.suffix.lower()
            if name == "package.json" or suffix in {".html", ".jsx", ".tsx", ".vue", ".svelte"}:
                found.add("web")
            if name in {"requirements.txt", "pyproject.toml", "package.json", "pom.xml", "build.gradle"} and seen < 2000:
                try:
                    text = item.read_text(errors="ignore")[:20000].lower()
                except OSError:
                    continue
                if any(re.search(rf'(?<![a-z]){k}(?![a-z])', text) for k in ("flask", "fastapi", "django", "express", "koa", "spring", "vite", "react", "next")):
                    found.add("web")
                if any(re.search(rf'(?<![a-z]){k}(?![a-z])', text) for k in ("flask", "fastapi", "django", "express", "koa", "spring", "sqlalchemy")):
                    found.add("api")
            if suffix in {".csv", ".tsv", ".jsonl", ".ndjson", ".sqlite", ".sqlite3", ".db"}:
                found.add("data")
    return found


def skills_for(mode: str, stack: set[str]) -> list[str]:
    names = list(MODES[mode]["skills"])
    if mode in {"dev", "qa", "preview"} and "web" in stack:
        names += WEB if mode == "dev" else ["web-runtime-debugging", "web-flow-verification"]
    if mode in {"dev", "qa"} and "api" in stack:
        names.append("api-backend-development")
    if mode in {"dev", "optimize"} and "data" in stack:
        names.append("data-processing")
    return list(dict.fromkeys(names))


def model_catalog() -> dict:
    """Model slugs from `codex debug models` (fallback: local cache). Evidence of a catalog, not of entitlement."""
    if shutil.which("codex"):
        try:
            p = subprocess.run(["codex", "debug", "models"], capture_output=True, text=True, timeout=30)
            if p.returncode == 0:
                data = json.loads(p.stdout)
                items = data.get("models", data) if isinstance(data, dict) else data
                return {"source": "codex debug models", "slugs": sorted(m["slug"] for m in items if isinstance(m, dict) and m.get("slug"))}
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    return {"source": None, "slugs": []}


def resolve_routing(requested: str, catalog: dict, model: str | None = None) -> dict:
    """routed only when every role model is in the observed catalog; otherwise inherited."""
    slugs = set(catalog["slugs"])
    needed = sorted({m for m, *_ in ROLES.values()})
    missing = [m for m in needed if m not in slugs]
    if model and "astra" in model.lower():
        raise ValueError("Astra is prohibited")
    if requested == "inherited":
        return {"mode": "inherited", "reason": "requested"}
    if not slugs:
        return {"mode": "inherited", "reason": "no model catalog could be read (codex absent or `debug models` failed)"}
    if missing:
        if requested == "routed":
            return {"mode": "inherited", "reason": f"routed requested but catalog lacks {missing}", "downgraded": True}
        return {"mode": "inherited", "reason": f"catalog lacks {missing}"}
    return {"mode": "routed", "reason": f"catalog ({catalog['source']}) lists all role models {needed}",
            "limitation": "catalog listing is not proof of entitlement or effective routing; observe a real agent run"}


def _git(project: Path, *args: str) -> str | None:
    p = subprocess.run(["git", *args], cwd=project, capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def fingerprint(project: Path) -> str:
    """Changes whenever tracked/untracked project content changes; used to mark old verification stale."""
    h = hashlib.sha256()
    head = _git(project, "rev-parse", "HEAD")
    if head is not None:
        h.update(head.encode())
        h.update((_git(project, "diff", "HEAD") or "").encode())
        for rel in sorted((_git(project, "ls-files", "-o", "--exclude-standard") or "").splitlines()):
            try:
                st = (project / rel).stat()
                h.update(f"{rel}:{st.st_size}:{st.st_mtime_ns}".encode())
            except OSError:
                pass
        return "git:" + h.hexdigest()[:16]
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__"}
    count = 0
    for path in sorted(project.rglob("*")):
        if skip & set(path.relative_to(project).parts) or not path.is_file():
            continue
        count += 1
        if count > 20000:
            h.update(b"truncated")
            break
        st = path.stat()
        h.update(f"{path.relative_to(project)}:{st.st_size}:{st.st_mtime_ns}".encode())
    return "fs:" + h.hexdigest()[:16]


def state_dir(project: Path) -> Path:
    digest = hashlib.sha256(str(project).encode()).hexdigest()[:8]
    return STATE_ROOT / f"{project.name}-{digest}"


VERIFY_KINDS = {"qa-result", "defect", "perf", "preview"}
KINDS = {"command", "decision", "change", "qa-result", "defect", "perf", "preview", "open-item", "note"}


def state_add(project: Path, session: str, kind: str, text: str, workdir: Path | None = None) -> dict:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}")
    if session not in MODES:
        raise ValueError(f"session must be one of {sorted(MODES)}")
    if not text.strip() or len(text) > 4000:
        raise ValueError("text must be 1..4000 characters (concise facts, not transcripts)")
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session": session,
              "kind": kind, "text": text.strip(), "fingerprint": fingerprint(workdir or project)}
    directory = state_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "state.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def state_show(project: Path, kind: str | None = None, limit: int = 50, workdir: Path | None = None) -> dict:
    path = state_dir(project) / "state.jsonl"
    current = fingerprint(workdir or project)
    records = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            if kind and rec.get("kind") != kind:
                continue
            if rec.get("kind") in VERIFY_KINDS and rec.get("fingerprint") != current:
                rec["stale"] = True
            records.append(rec)
    return {"project": str(project), "current_fingerprint": current, "records": records[-limit:],
            "note": "stale=true = made against different tracked/untracked content (gitignored files such as build output or .env are NOT fingerprinted); decision/change/note records are never marked stale"}


def ensure_worktree(project: Path, dry_run: bool) -> dict:
    """Isolated git worktree outside the project for OPTIMIZE; reused on repeat runs."""
    if _git(project, "rev-parse", "--is-inside-work-tree") is None or _git(project, "rev-parse", "HEAD") is None:
        return {"isolated": False, "reason": "project is not a git repository with a commit"}
    path = state_dir(project) / "optimize-worktree"
    branch = "harness/optimize"
    info = {"isolated": True, "path": str(path), "branch": branch}
    dirty = bool((_git(project, "status", "--porcelain") or "").strip())
    if dirty:
        info["warning"] = "project has uncommitted changes; the worktree starts from the last commit and excludes them"
    info["limitations"] = ("worktree has tracked files from the last commit only: untracked/ignored inputs (.env, data files, node_modules, "
                           "untracked AGENTS.md) are absent, so copy what you need or build there")
    (path.parent).mkdir(parents=True, exist_ok=True)
    if not dry_run:
        (path.parent / "project.txt").write_text(str(project))
    if path.exists():
        current = _git(path, "rev-parse", "--abbrev-ref", "HEAD")
        if current is None or current.strip() != branch:
            raise ValueError(f"{path} exists but is not a valid worktree on {branch}; remove it (git worktree remove --force) and retry")
        info["reused"] = True
        behind = (_git(project, "rev-list", "--count", f"{branch}..HEAD") or "0").strip()
        if behind != "0":
            info["warning"] = f"project HEAD is {behind} commit(s) ahead of {branch}; the worktree does NOT include them (merge/rebase deliberately if needed)"
        return info
    if dry_run:
        info["would_create"] = True
        return info
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = subprocess.run(["git", "rev-parse", "--verify", "-q", branch], cwd=project, capture_output=True).returncode == 0
    subprocess.run(["git", "worktree", "prune"], cwd=project, capture_output=True)
    cmd = ["git", "worktree", "add", str(path), branch] if exists else ["git", "worktree", "add", "-b", branch, str(path), "HEAD"]
    p = subprocess.run(cmd, cwd=project, capture_output=True, text=True)
    if p.returncode != 0:
        raise ValueError(f"git worktree add failed: {p.stderr.strip()[:300]}")
    info["created"] = True
    return info


def verify_skills(workdir: Path, names: list[str]) -> dict:
    """Ask Codex itself (no model call) which skills a fresh session in workdir would list."""
    if not names:
        return {"checked": False, "reason": "no project skills requested"}
    if not shutil.which("codex"):
        return {"checked": False, "reason": "codex CLI absent"}
    try:
        p = subprocess.run(["codex", "debug", "prompt-input", "hello"], cwd=workdir, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"checked": False, "reason": str(exc)}
    if p.returncode != 0:
        return {"checked": False, "reason": f"debug prompt-input exit {p.returncode}"}
    listed = [n for n in names if f"- {n}:" in p.stdout or f"{n}/SKILL.md" in p.stdout]
    return {"checked": True, "method": "codex debug prompt-input (no model call)",
            "recognized": listed, "not_listed": [n for n in names if n not in listed]}


def build_prompt(mode: str, project: Path, workdir: Path, exam: bool) -> str:
    if mode == "dev" and exam:
        return f"{ROOT / 'EXAM_START.md'} 읽고 시작해줘. 과제 프로젝트 루트: {project}"
    doc = ROOT / MODES[mode]["doc"]
    extra = f" 작업 디렉터리(격리 worktree): {workdir}. 원본 프로젝트: {project}." if workdir != project else f" 과제 프로젝트: {project}."
    extra += " state 명령은 `--project " + str(project) + "` 없이도 동작하나 필요하면 명시하라." if workdir != project else ""
    return (f"CodexHarness 세션 모드 `{mode}`. 먼저 {doc} 를 읽고 그 지침을 따르라.{extra} "
            f"하네스 경로: {ROOT} (하네스 명령은 `PYTHONPATH={ROOT} python3 -m harness ...`). "
            "프로젝트 AGENTS.md와 과제 지침, 시험 제한이 항상 우선한다. 사용자 승인 없이 구현을 시작하지 말라.")


def prepare(mode: str, project_arg: Path | None = None, *, routing: str = "auto", model: str | None = None,
            dry_run: bool = False, exam: bool = False, in_place: bool = False, skip_skills: bool = False,
            catalog: dict | None = None) -> dict:
    from .validate import validate
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode}")
    spec = MODES[mode]
    project = find_project(project_arg)
    errors = validate()
    if errors:
        raise ValueError(f"harness validation failed: {errors[:3]}")
    report: dict = {"mode": mode, "purpose": spec["purpose"], "project": str(project), "harness": str(ROOT),
                    "dry_run": dry_run, "codex": shutil.which("codex"), "notes": []}
    if not report["codex"] and not dry_run:
        raise ValueError("codex CLI not found in PATH; use --dry-run to inspect the plan")
    report["routing"] = resolve_routing(routing, catalog if catalog is not None else (model_catalog() if report["codex"] else {"source": None, "slugs": []}), model)
    bundle = ROOT / (".codex" if report["routing"]["mode"] == "routed" else "configs/inherited")
    if report["routing"]["mode"] == "inherited":
        report["routing"]["effect"] = "subagents inherit the parent model; role instructions still apply"

    workdir = project
    if spec.get("isolate"):
        iso = ensure_worktree(project, dry_run)
        report["isolation"] = iso
        if iso["isolated"]:
            workdir = Path(iso["path"]) if not iso.get("would_create") else project
        elif not in_place:
            raise ValueError(f"cannot isolate OPTIMIZE: {iso['reason']}. Re-run with --in-place only after backing up / committing your work")
        else:
            report["notes"].append("WARNING: --in-place optimize edits the live project")
    elif mode == "explain":
        report["isolation"] = {"isolated": False, "reason": "read-only sandbox instead"}

    stack = detect_stack(project)
    names = [] if skip_skills else skills_for(mode, stack)
    report["stack_hint"] = sorted(stack)
    if mode == "explain":
        names = []
        report["skills"] = {"installed": [], "note": "read-only: nothing is written into the project; the brief points at the harness skill files to read directly"}
    elif dry_run:
        report["skills"] = {"would_install_if_missing": names}
    else:
        report["skills"] = install_skills(workdir, names)
        report["skills"]["recognition"] = verify_skills(workdir, names)
        report["skills"]["note"] = "recognition = what a NEW session lists; it does not retroactively apply to an already running Codex"

    cmd = ["codex", "-C", str(workdir), *launch_overrides(bundle)]
    if model:
        cmd += ["-m", model]
    if spec.get("sandbox"):
        cmd += ["-s", spec["sandbox"]]
        report["sandbox"] = {"mode": spec["sandbox"], "enforced_by": "codex -s flag; platform-managed policy may be stricter"}
    else:
        report["sandbox"] = {"mode": "platform default", "limitation": f"{mode} read-only/no-product-edit rules are instructions only" if mode == "qa" else "unchanged"}
    if mode != "explain":
        sdir = state_dir(project)
        cmd += ["--add-dir", str(sdir)]
        report["state_dir"] = str(sdir)
        if not dry_run:
            sdir.mkdir(parents=True, exist_ok=True)
    cmd.append(build_prompt(mode, project, workdir, exam))
    report["command"] = cmd
    report["not_verified"] = ["real model calls / effective model routing (only a live agent run proves it)",
                              "Cofa-specific behaviour (this launcher only prepares before Codex starts)"]
    for key in ("warning", "limitations"):
        if report.get("isolation", {}).get(key):
            report["notes"].append(f"{mode}: {report['isolation'][key]}")
    if not dry_run and mode != "explain":
        state_add(project, mode, "note", f"session prepared: routing={report['routing']['mode']} skills={names}")
    return report
