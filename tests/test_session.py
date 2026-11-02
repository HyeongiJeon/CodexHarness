from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from harness import session
from harness.measure import measure
from harness.roles import ROOT, ROLES

ALL = {"lead": 0}
CATALOG_FULL = {"source": "test", "slugs": sorted({m for m, *_ in ROLES.values()})}


def make_project(directory: str, git: bool = True) -> Path:
    project = Path(directory) / "task"
    project.mkdir()
    (project / "AGENTS.md").write_text("Original rules")
    (project / "package.json").write_text('{"dependencies":{"vite":"1"}}')
    (project / "data.csv").write_text("a,b\n1,2\n")
    if git:
        for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"]):
            subprocess.run(["git", *cmd], cwd=project, check=True, capture_output=True)
    return project


class SessionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = session.STATE_ROOT
        session.STATE_ROOT = Path(self._tmp.name) / "state"
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(setattr, session, "STATE_ROOT", self._old)

    def prep(self, mode, project, **kw):
        kw.setdefault("catalog", CATALOG_FULL)
        kw.setdefault("dry_run", True)
        return session.prepare(mode, project, **kw)

    def test_every_mode_dry_run_builds_command_without_touching_project(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            before = sorted(p.name for p in project.iterdir())
            for mode in session.MODES:
                if mode == "optimize":
                    continue
                r = self.prep(mode, project)
                self.assertEqual(r["command"][:3], ["codex", "-C", str(project)])
                self.assertIn(mode, r["command"][-1])
            self.assertEqual(before, sorted(p.name for p in project.iterdir()))

    def test_explain_is_read_only_sandbox_and_installs_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            r = self.prep("explain", project, dry_run=False)
            self.assertIn("-s", r["command"])
            self.assertEqual(r["command"][r["command"].index("-s") + 1], "read-only")
            self.assertNotIn("--add-dir", r["command"])
            self.assertFalse((project / ".agents").exists())

    def test_non_explain_modes_do_not_force_a_sandbox(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            for mode in ("dev", "qa", "preview"):
                self.assertNotIn("-s", self.prep(mode, project)["command"])

    def test_routing_falls_back_to_inherited_without_models(self):
        self.assertEqual(session.resolve_routing("auto", {"source": "t", "slugs": ["gpt-x"]})["mode"], "inherited")
        self.assertEqual(session.resolve_routing("routed", {"source": "t", "slugs": []})["mode"], "inherited")
        self.assertEqual(session.resolve_routing("auto", CATALOG_FULL)["mode"], "routed")
        self.assertIn("not proof", session.resolve_routing("auto", CATALOG_FULL)["limitation"])
        with self.assertRaises(ValueError):
            session.resolve_routing("auto", CATALOG_FULL, "gpt-6-astra")

    def test_routed_and_inherited_bundles_selected(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            routed = self.prep("dev", project)["command"]
            self.assertIn('model="gpt-6.1-sol"', routed)
            inherited = self.prep("dev", project, catalog={"source": "t", "slugs": []})["command"]
            self.assertFalse(any(x.startswith("model=") for x in inherited))

    def test_skill_install_is_idempotent_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            existing = project / ".agents/skills/requirement-discovery"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text("mine")
            first = self.prep("dev", project, dry_run=False)
            second = self.prep("dev", project, dry_run=False)
            self.assertIn("requirement-discovery", first["skills"]["preserved_existing"])
            self.assertEqual(second["skills"]["installed"], [])
            self.assertEqual((existing / "SKILL.md").read_text(), "mine")
            self.assertEqual((project / "AGENTS.md").read_text(), "Original rules")
            self.assertIn("web-runtime-debugging", first["skills"]["installed"])  # web stack detected
            self.assertIn("data-processing", first["skills"]["installed"])

    def test_dry_run_does_not_claim_recognition(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.prep("dev", make_project(d))
            self.assertNotIn("recognition", r["skills"])

    def test_project_detection_from_other_cwd_and_refuses_harness(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            sub = project / "src"
            sub.mkdir()
            self.assertEqual(session.find_project(None, sub), project.resolve())
            self.assertEqual(session.find_project(project), project.resolve())
            with self.assertRaises(ValueError):
                session.find_project(ROOT)
            with self.assertRaises(ValueError):
                session.find_project(None, ROOT / "tests")

    def test_optimize_uses_isolated_worktree_and_requires_in_place_otherwise(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            session_state = session.STATE_ROOT
            try:
                session.STATE_ROOT = Path(d) / "state"
                r = self.prep("optimize", project, dry_run=False)
                wt = Path(r["isolation"]["path"])
                self.assertTrue(wt.is_dir() and wt != project)
                self.assertEqual(r["command"][2], str(wt))
                self.assertTrue((wt / ".agents/skills/performance-optimization/SKILL.md").is_file())
                self.assertFalse((project / ".agents").exists())  # live project untouched
                again = self.prep("optimize", project, dry_run=False)
                self.assertTrue(again["isolation"]["reused"])
                plain = make_project(str(Path(d) / "x") if (Path(d) / "x").mkdir() is None else d, git=False)
                with self.assertRaises(ValueError):
                    self.prep("optimize", plain)
                self.assertTrue(self.prep("optimize", plain, in_place=True)["notes"])
            finally:
                session.STATE_ROOT = session_state
                subprocess.run(["git", "worktree", "prune"], cwd=project, capture_output=True)

    def test_state_commands_work_inside_optimize_worktree(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            r = self.prep("optimize", project, dry_run=False)
            wt = Path(r["isolation"]["path"])
            self.assertEqual(session.find_project(None, wt), project.resolve())
            session.state_add(project, "optimize", "perf", "x", workdir=wt)
            (wt / "new.py").write_text("y=1")
            self.assertTrue(session.state_show(project, workdir=wt)["records"][-1].get("stale"))
            (project / "later.py").write_text("")
            subprocess.run(["git", "add", "-A"], cwd=project)
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "2"], cwd=project)
            again = self.prep("optimize", project, dry_run=False)
            self.assertIn("ahead", again["isolation"]["warning"])
            subprocess.run(["git", "worktree", "prune"], cwd=project)

    def test_exam_flag_uses_exam_start_gate(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.prep("dev", make_project(d), exam=True)
            self.assertIn("EXAM_START.md", r["command"][-1])

    def test_state_marks_verification_stale_after_code_change(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            old = session.STATE_ROOT
            try:
                session.STATE_ROOT = Path(d) / "state"
                session.state_add(project, "qa", "qa-result", "login PASS")
                session.state_add(project, "dev", "decision", "use sqlite")
                self.assertFalse(any(r.get("stale") for r in session.state_show(project)["records"]))
                (project / "new.py").write_text("x=1")
                recs = {r["kind"]: r for r in session.state_show(project)["records"]}
                self.assertTrue(recs["qa-result"]["stale"])
                self.assertNotIn("stale", recs["decision"])
                with self.assertRaises(ValueError):
                    session.state_add(project, "qa", "bogus", "x")
            finally:
                session.STATE_ROOT = old

    def test_validate_covers_session_docs(self):
        from harness.validate import validate
        self.assertEqual(validate(), [])

    def test_cli_start_dry_run_from_foreign_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            env = {**os.environ, "PYTHONPATH": str(ROOT)}
            out = subprocess.run([sys.executable, "-m", "harness", "start", "qa", "--dry-run"], cwd=project, env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(json.loads(out.stdout)["project"], str(project.resolve()))


class MeasureTests(unittest.TestCase):
    def test_baseline_and_output_change_detection(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "out.txt"
            f.write_text("42")
            cmd = [sys.executable, "-c", "import sys;print(open(sys.argv[1]).read())", str(f)]
            base = measure(cmd, repeat=3, warmup=0, label="a")
            self.assertEqual(base["status"], "baseline")
            self.assertTrue(base["output_stable"])
            same = measure(cmd, repeat=3, warmup=0, baseline=base)
            self.assertEqual(same["status"], "ok")
            self.assertIn("caveat", same)
            f.write_text("43")
            self.assertEqual(measure(cmd, repeat=2, warmup=0, baseline=base)["status"], "output_changed")

    def test_nondeterministic_or_failing_command_is_not_a_measurement(self):
        self.assertEqual(measure([sys.executable, "-c", "import random;print(random.random())"], repeat=3, warmup=0)["status"], "failed")
        self.assertEqual(measure([sys.executable, "-c", "raise SystemExit(3)"], repeat=1, warmup=0)["status"], "failed")

    def test_invalid_baseline_and_missing_exe_and_orphans(self):
        cmd = [sys.executable, "-c", "print(1)"]
        self.assertEqual(measure(cmd, repeat=1, warmup=0, baseline={"status": "timeout"})["status"], "invalid_baseline")
        base = measure(cmd, repeat=1, warmup=0)
        self.assertEqual(measure([sys.executable, "-c", "print(2)"], repeat=1, warmup=0, baseline=base)["status"], "invalid_baseline")
        self.assertEqual(measure(["/nonexistent/exe"], repeat=1, warmup=0)["status"], "failed")

    def test_timeout(self):
        self.assertEqual(measure([sys.executable, "-c", "import time;time.sleep(5)"], repeat=1, warmup=0, timeout=0.3)["status"], "timeout")


class ProbeExtensionTests(unittest.TestCase):
    def test_baseline_server_and_probe_host_header_bind(self):
        import socket
        from harness.web_probe import probe, serve_baseline
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        t = threading.Thread(target=serve_baseline, args=("127.0.0.1", port), daemon=True)
        t.start()
        import time
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), 0.1).close()
                break
            except OSError:
                time.sleep(0.05)
        r = probe(f"http://127.0.0.1:{port}/", ["/api/ping"], host_header="preview.example", cors_origin="http://o")
        self.assertEqual(r["verdict"], "server_and_assets_ok", r)
        self.assertEqual(r["host_header_check"]["status"], 200)
        if r["bind_addresses"] is not None:
            self.assertIn("127.0.0.1", r["bind_addresses"])
            self.assertTrue(any("bound only" in f["message"] for f in r["findings"]))


class DataExtensionTests(unittest.TestCase):
    def test_sqlite_inspect_is_read_only_and_select_only(self):
        import sqlite3
        from harness.large_data import sqlite_inspect
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "t.db"
            c = sqlite3.connect(db)
            c.executescript("create table a(id integer primary key, n text); insert into a values(1,null),(2,'x');")
            c.commit()
            c.close()
            rep = sqlite_inspect(db, "select count(*) from a")
            self.assertEqual(rep["tables"][0]["rows"], 2)
            self.assertEqual(rep["tables"][0]["null_counts"]["n"], 1)
            self.assertEqual(rep["query"]["rows"], [[2]])
            for bad in ("delete from a", "select 1; delete from a"):
                with self.assertRaises(ValueError):
                    sqlite_inspect(db, bad)
            self.assertEqual(sqlite_inspect(db)["tables"][0]["rows"], 2)

    def test_sqlite_path_with_special_characters(self):
        import sqlite3
        from harness.large_data import sqlite_inspect
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "a#b c.db"
            c = sqlite3.connect(db); c.execute("create table t(x)"); c.commit(); c.close()
            self.assertEqual(sqlite_inspect(db)["tables"][0]["table"], "t")
            self.assertFalse((Path(d) / "a").exists())

    def test_profile_reports_outliers_and_duplicates(self):
        from harness.large_data import profile_file
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            p.write_text("id,v\n" + "\n".join(f"{i},{i}" for i in range(1, 9)) + "\n9,1000\n9,1000\n")
            rep = profile_file(p)
            self.assertEqual(rep["duplicate_rows_in_sample"], 1)
            v = next(f for f in rep["schema"] if f["name"] == "v")
            self.assertGreaterEqual(v["numeric"]["iqr_outliers"], 1)


if __name__ == "__main__":
    unittest.main()
