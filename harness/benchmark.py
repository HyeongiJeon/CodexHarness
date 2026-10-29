"""Real CLI coding exercises and evidence extraction; no simulated agent results.

Raw CLI/session evidence remains ignored under .harness. Published reports must
be curated from summary.json, never copied wholesale from personal sessions.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .roles import ROOT, launch_overrides

SPEC = """Synthetic benchmark, not an exam answer. Python stdlib only. Work only here.
No network, external uploads, git push, browser/GUI automation, credentials or CLI updates.
Task A (web/server.py): implement create_server(host='127.0.0.1', port=0) returning
a stdlib HTTP server. GET / serves semantic HTML with a labeled title input,
add button, status filter and JS fetching the task API (no external assets).
GET /api/tasks returns JSON list; POST /api/tasks JSON {title} creates {id,title,status:'todo'},
returns 201. Blank title returns JSON 400. PATCH /api/tasks/ID JSON {status:'done'}
updates status, returns 200; nonexistent ID ->404; invalid status ->400.
Task B (analysis/report.py): summarize(text) accepts CSV id,region,amount. Trim values;
skip rows with empty required fields, duplicates by id (first VALID wins), malformed,
negative or nonfinite amount; return dict region -> amount string exactly two decimals.
Use Decimal and reject more than two fractional digits, output sorted by region.
Task C (repair/tickets.py): fix summarize(tickets) to return counts by status,
with no state retained across calls and unknown statuses counted as 'unknown'.
Supported statuses are 'open','closed'; do not mutate input.
"""

CHECKER = r'''
import importlib.util, json, pathlib, threading, urllib.request, urllib.error, unittest

def load(relative):
    path = pathlib.Path(relative)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Acceptance(unittest.TestCase):
    def test_A_web_flow(self):
        mod = load('web/server.py')
        server = mod.create_server('127.0.0.1', 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(server.server_address[1])
        def request(path, data=None, method=None):
            body = json.dumps(data).encode() if data is not None else None
            req = urllib.request.Request(base+path, data=body, method=method,
                 headers={'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(req, timeout=3) as r:
                    return r.status, r.read().decode()
            except urllib.error.HTTPError as e:
                with e:
                    return e.code, e.read().decode()
        try:
            status, html = request('/')
            self.assertEqual(status, 200)
            for token in ('<label', '<button', 'fetch(', '/api/tasks'):
                self.assertIn(token, html)
            self.assertEqual(request('/api/tasks', {'title':'   '})[0], 400)
            status, raw = request('/api/tasks', {'title':'Acceptance demo'})
            self.assertEqual(status, 201)
            item = json.loads(raw)
            self.assertEqual(item['status'], 'todo')
            self.assertEqual(request('/api/tasks/'+str(item['id']), {'status':'done'}, 'PATCH')[0], 200)
            self.assertEqual(json.loads(request('/api/tasks')[1])[0]['status'], 'done')
            self.assertEqual(request('/api/tasks/999', {'status':'done'}, 'PATCH')[0], 404)
            self.assertEqual(request('/api/tasks/'+str(item['id']), {'status':'invalid'}, 'PATCH')[0], 400)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_B_csv_accuracy(self):
        mod = load('analysis/report.py')
        csv = 'id,region,amount\n1, East ,0.10\n2,East,0.20\n1,East,99\n3,West,NaN\n3,West,2.00\n4,West,-1\n5,,4\n6,West,1.234\n7,West,3.00\n'
        self.assertEqual(mod.summarize(csv), {'East':'0.30', 'West':'5.00'})
        self.assertEqual(mod.summarize('id,region,amount\n'), {})

    def test_C_regression(self):
        mod = load('repair/tickets.py')
        rows = [{'status':'open'}, {'status':'closed'}, {'status':'open'}, {'status':'other'}, {}]
        original = json.loads(json.dumps(rows))
        self.assertEqual(mod.summarize(rows), {'open':2,'closed':1,'unknown':2})
        empty = mod.summarize([])
        # The contract requires no retained counts, not a zero-valued unknown key.
        self.assertEqual({k: v for k, v in empty.items() if v}, {})
        self.assertEqual(empty.get('open', 0), 0)
        self.assertEqual(empty.get('closed', 0), 0)
        self.assertEqual(empty.get('unknown', 0), 0)
        self.assertEqual(rows, original)

suite = unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance)
result = unittest.TextTestRunner(verbosity=2).run(suite)
failed = {test._testMethodName.split('_')[1] for test, _ in result.failures + result.errors + result.skipped}
print('HARNESS_SCENARIOS=' + json.dumps({name: result.testsRun == 3 and name not in failed for name in ('A','B','C')}))
raise SystemExit(0 if result.wasSuccessful() else 1)
'''


def evaluate(project: Path) -> tuple[dict, bool, str]:
    """Run the same offline acceptance suite with structured per-scenario results."""
    try:
        check = subprocess.run([sys.executable, "-c", CHECKER], cwd=project, capture_output=True, text=True, timeout=30)
        log = check.stdout + check.stderr
        markers = [line.removeprefix("HARNESS_SCENARIOS=") for line in check.stdout.splitlines() if line.startswith("HARNESS_SCENARIOS=")]
        scenarios = json.loads(markers[-1]) if markers else {}
        checks = {"acceptance_exit_code": check.returncode, "scenarios": scenarios}
        passed = check.returncode == 0 and all(scenarios.get(name) is True for name in ("A", "B", "C"))
    except (subprocess.TimeoutExpired, ValueError):
        log = "Acceptance timed out or did not produce valid structured results.\n"
        checks = {"acceptance_exit_code": None, "error": "acceptance evidence incomplete"}
        passed = False
    return checks, passed, log


def initialize(project: Path, smoke: bool) -> None:
    project.mkdir(parents=True)
    if smoke:
        (project / "input.txt").write_text("synthetic input: 2 + 3 = 5\n")
        return
    for name in ("web", "analysis", "repair"):
        (project / name).mkdir()
    (project / "TASK.md").write_text(SPEC)
    (project / "web/server.py").write_text("def create_server(host='127.0.0.1', port=0):\n    raise NotImplementedError\n")
    (project / "analysis/report.py").write_text("def summarize(text):\n    raise NotImplementedError\n")
    (project / "repair/tickets.py").write_text("def summarize(tickets, counts={'open': 0, 'closed': 0}):\n    for ticket in tickets:\n        counts[ticket['status']] = 1\n    return counts\n")


def extract_events(path: Path) -> dict:
    """Count actual structured collaboration events, never agent prose."""
    calls = []
    usages = []
    root_id = None
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "thread.started":
            root_id = event.get("thread_id")
        if event.get("type") == "turn.completed":
            usages.append(event.get("usage", {}))
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "collab_tool_call":
            calls.append({k: item.get(k) for k in ("tool", "sender_thread_id", "receiver_thread_ids", "status", "agents_states")})
    spawned = sorted({i for c in calls if c.get("tool") == "spawn_agent" for i in c.get("receiver_thread_ids", [])})
    # A running second agent observed before the first completed is actual overlap.
    overlap = any(sum(s.get("status") == "running" for s in (c.get("agents_states") or {}).values()) >= 2 for c in calls)
    return {"root_thread_id": root_id, "spawned_thread_ids": spawned, "subagent_count": len(spawned), "parallel_observed_in_cli_states": overlap, "collaboration_events": calls, "root_usage": usages}


def session_metadata(thread_ids: list[str]) -> list[dict]:
    """Select only known synthetic sessions and public configuration fields."""
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    output = []
    for thread_id in thread_ids:
        files = list((home / "sessions").glob(f"**/*{thread_id}.jsonl"))
        record = {"thread_id": thread_id, "available": bool(files)}
        for path in files:
            for line in path.open():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                data = event.get("payload", {})
                if event.get("type") == "session_meta":
                    for key in ("agent_role", "model_provider", "forked_from_id"):
                        if key in data:
                            record[key] = data[key]
                    record["source"] = data.get("source")
                elif event.get("type") == "turn_context":
                    record["model"] = data.get("model")
                    record["effort"] = data.get("effort")
        output.append(record)
    return output


def augment_local_sessions(evidence: dict) -> dict:
    """Hosted tool adapters can omit spawn events from exec JSONL.

    In that case use actual session ancestry + spawn requests, not final prose.
    Never export session content; select IDs, timing, models and token counters.
    """
    root_id = evidence.get("root_thread_id")
    if not root_id:
        return evidence
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    files = list((home / "sessions").glob(f"**/*{root_id}.jsonl"))
    if not files:
        return evidence
    requests = []
    day_dir = files[0].parent
    for line in files[0].open():
        try:
            event = json.loads(line)
            data = event.get("payload", {})
            if data.get("type") == "function_call" and data.get("name", "").split(".")[-1] == "spawn_agent":
                args = json.loads(data.get("arguments", "{}"))
                requests.append({k: args[k] for k in ("agent_type", "fork_turns", "fork_context", "model", "reasoning_effort") if k in args})
        except (ValueError, TypeError):
            continue
    children = []
    for path in day_dir.glob("*.jsonl"):
        try:
            with path.open() as handle:
                first = json.loads(handle.readline()).get("payload", {})
            source = first.get("source", {})
            spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
            if spawn.get("parent_thread_id") != root_id:
                continue
            record = {"thread_id": first["id"], "agent_role": first.get("agent_role"), "forked_from_id": first.get("forked_from_id"), "started": first.get("timestamp"), "finished": None, "parent_marker_present_in_log": False}
            for line in path.open():
                if "LEAD_PRIVATE_CONTEXT_47C9" in line:
                    record["parent_marker_present_in_log"] = True
                event = json.loads(line)
                data = event.get("payload", {})
                if event.get("type") == "turn_context":
                    record.update(model=data.get("model"), effort=data.get("effort"))
                if event.get("type") == "event_msg":
                    if data.get("type") == "token_count":
                        record["usage"] = (data.get("info") or {}).get("total_token_usage")
                    if data.get("type") in ("task_complete", "turn_complete", "task_completed"):
                        record["finished"] = event.get("timestamp")
            children.append(record)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if children:
        evidence["spawned_thread_ids"] = sorted(set(evidence["spawned_thread_ids"]) | {c["thread_id"] for c in children})
        evidence["subagent_count"] = len(evidence["spawned_thread_ids"])
        evidence["child_sessions"] = children
        evidence["spawn_requests"] = requests
        intervals = [(c["started"], c["finished"]) for c in children if c["started"] and c["finished"]]
        evidence["parallel_observed_in_session_timestamps"] = any(a[0] < b[1] and b[0] < a[1] for i, a in enumerate(intervals) for b in intervals[i + 1:])
    return evidence


def run(mode: str, routing: str, model: str, timeout: int) -> int:
    if "astra" in model.lower():
        raise ValueError("Astra is prohibited")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / ".harness/runs" / f"{stamp}-{mode}"
    project = run_dir / "project"
    initialize(project, mode == "smoke")
    bundle = ROOT / (".codex" if routing == "routed" else "configs/inherited")
    if mode == "smoke":
        prompt = """Run a REAL native subagent smoke test here. Do not implement applications.
Spawn requirements and explorer as TWO fresh independent subagents (fork_context=false),
both before waiting. Use their configured agent_type if the tool exposes it.
Requirements agent: read input.txt and the requirement-discovery skill under ancestor
.agents/skills if discovered. Write ONLY requirements.json with {\"sum\":5,\"role\":\"requirements\",\"parent_marker_seen\":false}.
Explorer agent: read input.txt; write ONLY explorer.json with {\"sum\":5,\"role\":\"explorer\",\"parent_marker_seen\":false}.
Ask both to set parent_marker_seen to true only if their context actually contains a
parent-only marker; do not send the marker to children. The parent-only marker is
LEAD_PRIVATE_CONTEXT_47C9. Do not put it in any file. Shared files are expected,
fresh contexts must not inherit this lead conversation. Wait for both and independently
read/validate both JSON files. Do not create files yourself or claim unavailable features work.
No network, browser tools, push, updates, secrets or external services."""
    else:
        prompt = SPEC + "\nRead TASK.md. "
        if mode == "multi":
            prompt += "Spawn three fresh independent agents before waiting: frontend owns ONLY web/, data owns ONLY analysis/, core owns ONLY repair/. Use configured agent_type when available. Do not send one task's output to another worker. Lead integrates and executes focused checks, independently reads actual files. Activate additional fresh QA/reviewer only when a consequential defect or unresolved uncertainty warrants it; keep checks focused and avoid repeating equivalent checks. No nested delegation."
        else:
            prompt += "Execute all three tasks yourself, sequentially. Do not spawn any agents; this is the single-agent baseline."
    cmd = ["codex", "exec", "-C", str(project), "-m", model, "--json", *launch_overrides(bundle)]
    if mode == "single":
        cmd += ["-c", "agents.enabled=false"]
    (run_dir / "prompt.txt").write_text(prompt)
    before = {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest() for p in project.rglob("*") if p.is_file()}
    start = time.monotonic()
    timed_out = False
    with (run_dir / "events.jsonl").open("w") as stdout, (run_dir / "stderr.log").open("w") as stderr:
        process = subprocess.Popen(cmd + ["-"], stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True, start_new_session=True)
        try:
            process.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    elapsed = time.monotonic() - start
    if mode == "smoke":
        checks = {}
        for role in ("requirements", "explorer"):
            try:
                data = json.loads((project / f"{role}.json").read_text())
                checks[role] = data == {"sum": 5, "role": role, "parent_marker_seen": False}
            except (OSError, ValueError):
                checks[role] = False
        passed = all(checks.values())
    else:
        checks, passed, log = evaluate(project)
        (run_dir / "acceptance.log").write_text(log)
    evidence = augment_local_sessions(extract_events(run_dir / "events.jsonl"))
    evidence["session_configuration"] = session_metadata(([evidence["root_thread_id"]] if evidence["root_thread_id"] else []) + evidence["spawned_thread_ids"])
    changed = sorted(str(p.relative_to(project)) for p in project.rglob("*") if p.is_file() and "__pycache__" not in p.parts and before.get(str(p.relative_to(project))) != hashlib.sha256(p.read_bytes()).hexdigest())
    required_spawns = 0 if mode == "single" else (2 if mode == "smoke" else 3)
    orchestration = orchestration_verified(evidence, required_spawns)
    success = passed and not timed_out and process.returncode == 0 and orchestration
    summary = {"mode": mode, "routing_requested": routing, "model_requested": model, "elapsed_seconds": round(elapsed, 3), "cli_exit_code": process.returncode, "timed_out": timed_out, "checks": checks, "acceptance_passed": passed, "orchestration_verified": orchestration, "success": success, "changed_files": changed, "fix_retries": None, "file_conflicts": "not automatically measurable; inspect agent writes and owned paths", **evidence}
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"run_dir": str(run_dir), "success": success, "elapsed_seconds": summary["elapsed_seconds"], "subagent_count": evidence["subagent_count"]}, indent=2), flush=True)
    return 0 if success else 1


def orchestration_verified(evidence: dict, required: int) -> bool:
    if required == 0:
        return evidence.get("subagent_count", 0) == 0
    fresh_requests = sum(r.get("fork_turns") == "none" or r.get("fork_context") is False for r in evidence.get("spawn_requests", []))
    parallel = evidence.get("parallel_observed_in_cli_states") or evidence.get("parallel_observed_in_session_timestamps")
    children = evidence.get("child_sessions", [])
    fresh_children = sum(c.get("forked_from_id") is None and not c.get("parent_marker_present_in_log") for c in children)
    return bool(evidence.get("subagent_count", 0) >= required and fresh_requests >= required and fresh_children >= required and parallel)
