from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from harness import session
from harness.install import install_skills
from harness.measure import measure
from harness.roles import ROOT, ROLES

ALL = {"lead": 0}
SOL = lambda: ["gpt-6.1-sol", "gpt-6-luna"]


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
        kw.setdefault("catalog_reader", SOL)
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

    def test_catalog_is_advisory_and_never_blocks_or_switches_model(self):
        self.assertEqual(session.check_model_available(SOL)["status"], "listed")
        self.assertEqual(session.check_model_available(lambda: None)["status"], "unverified")
        self.assertEqual(session.check_model_available(lambda: [])["status"], "not_listed")
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            for reader in (lambda: ["gpt-6-luna"], lambda: None, lambda: []):
                r = self.prep("dev", project, catalog_reader=reader)
                cmd = r["command"]
                self.assertEqual(cmd[cmd.index("-m") + 1], "gpt-6.1-sol")
                self.assertEqual(r["model"]["model"], "gpt-6.1-sol")
                self.assertNotIn("gpt-6-luna", " ".join(cmd))

    def test_codex_failure_is_reported_without_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            bin_dir = Path(d) / "bin"
            bin_dir.mkdir()
            import shutil
            (bin_dir / "git").symlink_to(shutil.which("git"))
            fake = bin_dir / "codex"
            fake.write_text("#!/bin/sh\necho \"ARGS: $*\" >&2\nexit 7\n")
            fake.chmod(0o755)
            env = {**os.environ, "PYTHONPATH": str(ROOT), "PATH": str(bin_dir), "HARNESS_STATE_ROOT": str(session.STATE_ROOT)}
            out = subprocess.run([sys.executable, "-m", "harness", "start", "qa", "--project", str(project)], env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 7)
            self.assertIn("-m gpt-6.1-sol", out.stderr)
            self.assertIn("no other model was tried", out.stderr)
            self.assertEqual(out.stderr.count("-m gpt-6.1-sol"), 1)

    def test_every_mode_command_pins_sol_for_main_and_all_subagents(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            for mode in ("dev", "explain", "qa", "preview"):
                cmd = self.prep(mode, project)["command"]
                self.assertEqual(cmd[cmd.index("-m") + 1], "gpt-6.1-sol")
                values = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-c"]
                self.assertIn('model="gpt-6.1-sol"', values)
                for name in ROLES:
                    path = next(v.split("=", 1)[1].strip('"') for v in values if v.startswith(f"agents.{name}.config_file="))
                    import tomllib
                    self.assertEqual(tomllib.loads(Path(path).read_text())["model"], "gpt-6.1-sol")
        for flag in ("--routing", "--model"):
            out = subprocess.run([sys.executable, "-m", "harness", "start", "dev", flag, "x"], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(out.returncode, 0)

    def test_preparation_works_without_codex_installed(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            with mock.patch("harness.session.shutil.which", return_value=None):
                r = self.prep("dev", project, dry_run=False, catalog_reader=None)
            self.assertEqual(r["skills"]["recognition"]["checked"], False)
            self.assertEqual(r["model"]["status"], "unverified")
            self.assertIn("command", r)

    def test_missing_codex_is_a_launch_error_not_a_config_error(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            import shutil
            bin_dir = Path(d) / "bin"
            bin_dir.mkdir()
            (bin_dir / "git").symlink_to(shutil.which("git"))
            env = {**os.environ, "PYTHONPATH": str(ROOT), "PATH": str(bin_dir), "HARNESS_STATE_ROOT": str(session.STATE_ROOT)}
            out = subprocess.run([sys.executable, "-m", "harness", "start", "qa", "--project", str(project)], env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 127)
            self.assertIn("launch error", out.stderr)

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

    def test_optimize_dry_run_has_no_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            before = subprocess.run(["git", "worktree", "list"], cwd=project, capture_output=True, text=True).stdout
            r = self.prep("optimize", project)
            self.assertTrue(r["isolation"]["would_create"])
            self.assertFalse(session.STATE_ROOT.exists())
            self.assertEqual(before, subprocess.run(["git", "worktree", "list"], cwd=project, capture_output=True, text=True).stdout)
            self.assertFalse((project / ".agents").exists())
            self.assertEqual(subprocess.run(["git", "branch", "--list", "harness/*"], cwd=project, capture_output=True, text=True).stdout, "")

    def git(self, cwd, *a):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, capture_output=True, text=True).stdout.strip()

    def test_optimize_results_distinguish_stale_from_not_integrated(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            r = self.prep("optimize", project, dry_run=False)
            wt = Path(r["isolation"]["path"])
            self.assertEqual(session.find_project(None, wt), project.resolve())
            (wt / "opt.py").write_text("y=1")
            rec = session.state_add(project, "optimize", "perf", "2x faster", workdir=wt)
            self.assertEqual(rec["workspace"]["kind"], "worktree")
            self.assertEqual(rec["workspace"]["branch"], "harness/optimize")
            self.assertEqual(rec["workspace"]["commit"], self.git(wt, "rev-parse", "HEAD"))
            # DEV reads it: worktree unchanged -> not stale, but not integrated
            got = session.state_show(project)["records"][-1]
            self.assertNotIn("stale", got)
            self.assertTrue(got["not_integrated"])
            # project changes do not make the worktree result stale
            (project / "dev.py").write_text("x=1")
            self.assertNotIn("stale", session.state_show(project)["records"][-1])
            # worktree changes do
            (wt / "opt.py").write_text("y=2")
            self.assertTrue(session.state_show(project)["records"][-1]["stale"])
            # commit in worktree, then merge into project: integrated (and still stale vs. the old fingerprint)
            self.git(wt, "add", "-A"); self.git(wt, "commit", "-qm", "opt")
            session.state_add(project, "optimize", "perf", "committed", workdir=wt)
            self.git(project, "add", "-A"); self.git(project, "commit", "-qm", "dev")
            self.git(project, "merge", "-q", "--no-edit", "harness/optimize")
            last = session.state_show(project)["records"][-1]
            self.assertNotIn("not_integrated", last)
            self.assertNotIn("stale", last)
            self.git(project, "worktree", "prune")

    def test_state_cli_workspace_from_cwd_not_from_project_flag(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            other = Path(d) / "other"
            other.mkdir()
            self.git(other, "init", "-q")
            r = self.prep("optimize", project, dry_run=False)
            wt = Path(r["isolation"]["path"])
            sub = wt / "nested"
            sub.mkdir()
            self.assertEqual(session.detect_workdir(project, wt), wt.resolve())
            self.assertEqual(session.detect_workdir(project, sub), wt.resolve())
            self.assertIsNone(session.detect_workdir(project, project))
            self.assertIsNone(session.detect_workdir(project, other))
            self.assertIsNone(session.detect_workdir(project, Path(d)))
            clone = Path(d) / "clone"
            self.git(Path(d), "clone", "-q", str(project), str(clone))
            import shutil
            fake_project = Path(d) / "q"
            fake_project.mkdir()
            fakewt = session.state_dir(fake_project.resolve()) / "optimize-worktree"
            fakewt.parent.mkdir(parents=True)
            shutil.move(str(clone), str(fakewt))
            self.assertIsNone(session.detect_workdir(fake_project.resolve(), fakewt))  # unrelated clone on wrong branch
            plain = wt.parent / "decoy"
            plain.mkdir()
            self.assertIsNone(session.detect_workdir(project, plain))
            env = {**os.environ, "PYTHONPATH": str(ROOT)}
            # the harness reads STATE_ROOT from the real repo, so run the CLI against the real default only for the shape check below
            for cwd, expect in ((sub, "worktree"), (project, "project"), (other, "project")):
                rec = session.state_add(project, "optimize", "perf", "x", workdir=session.detect_workdir(project, cwd))
                self.assertEqual(rec["workspace"]["kind"], expect)
                if expect == "worktree":
                    self.assertEqual(rec["workspace"]["path"], str(wt.resolve()))
                    self.assertEqual(rec["workspace"]["branch"], "harness/optimize")
                else:
                    self.assertEqual(rec["workspace"]["path"], str(project.resolve()))
            # DEV view: worktree record is not_integrated only if dirty/unmerged; project records never are
            kinds = [(x["workspace"]["kind"], x.get("not_integrated", False)) for x in session.state_show(project)["records"] if x["kind"] == "perf"]
            self.assertEqual(kinds[0], ("worktree", False))  # clean worktree at project HEAD; installed skills do not count as dirty
            self.assertEqual(kinds[1], ("project", False))
            self.git(project, "worktree", "prune")

    def test_state_cli_end_to_end_uses_cwd_worktree_with_explicit_project(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            state = session.STATE_ROOT
            code = ("import sys,os;from pathlib import Path;from harness import session;session.STATE_ROOT=Path(os.environ['ST']);"
                    "from harness.__main__ import main;sys.argv=['harness']+sys.argv[1:];sys.exit(main())")
            env = {**os.environ, "PYTHONPATH": str(ROOT), "ST": str(state)}
            r = self.prep("optimize", project, dry_run=False)
            wt = Path(r["isolation"]["path"])
            (wt / "o.py").write_text("1")
            out = subprocess.run([sys.executable, "-c", code, "state", "add", "--project", str(project), "--session", "optimize", "--kind", "perf", "--text", "t"],
                                 cwd=wt, env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            rec = json.loads(out.stdout)
            self.assertEqual(rec["workspace"]["kind"], "worktree")
            self.assertTrue(rec["workspace"]["dirty"])
            shown = subprocess.run([sys.executable, "-c", code, "state", "show", "--project", str(project)], cwd=project, env=env, capture_output=True, text=True)
            got = json.loads(shown.stdout)
            self.assertNotEqual(got["project_fingerprint"], rec["fingerprint"])
            self.assertTrue(got["records"][-1]["not_integrated"])
            self.assertNotIn("stale", got["records"][-1])
            self.git(project, "worktree", "prune")

    def test_dirty_ignores_only_untracked_harness_skills(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            (project / ".agents").mkdir()
            (project / ".agents/t").write_text("a")
            self.git(project, "add", "-A"); self.git(project, "commit", "-qm", "agents")
            self.assertFalse(session._workspace(project, None)["dirty"])
            (project / ".agents/t").write_text("b")
            self.assertTrue(session._workspace(project, None)["dirty"])

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
                self.assertNotIn("not_integrated", session.state_show(project)["records"][0])
                (project / "new.py").write_text("x=1")
                recs = {r["kind"]: r for r in session.state_show(project)["records"]}
                self.assertTrue(recs["qa-result"]["stale"])
                self.assertNotIn("stale", recs["decision"])
                with self.assertRaises(ValueError):
                    session.state_add(project, "qa", "bogus", "x")
            finally:
                session.STATE_ROOT = old

    def test_nested_state_and_reports_do_not_invalidate_verification(self):
        for use_git in (False, True):
            with self.subTest(git=use_git), tempfile.TemporaryDirectory() as d:
                project = make_project(d, git=use_git)
                with mock.patch.object(session, "STATE_ROOT", project / "CodexHarness/.harness/sessions"):
                    rec = session.state_add(project, "qa", "qa-result", "product check PASS")
                    shown = session.state_show(project)
                    self.assertEqual(shown["project_fingerprint"], rec["fingerprint"])
                    self.assertNotIn("stale", shown["records"][0])
                    session.state_add(project, "dev", "note", "received QA result")
                    (session.state_dir(project) / "report.md").write_text("local evidence")
                    self.assertNotIn("stale", session.state_show(project)["records"][0])
                    (project / "data.csv").write_text("a,b\n3,4\n")
                    self.assertTrue(session.state_show(project)["records"][0]["stale"])

    def test_nested_state_test_restores_state_root_even_on_failure(self):
        # Called directly, so neither setUp nor addCleanup can do the restoring for it.
        name = "test_nested_state_and_reports_do_not_invalidate_verification"
        before = session.STATE_ROOT
        getattr(SessionTests(name), name)()
        self.assertIs(session.STATE_ROOT, before)
        with mock.patch.object(session, "state_add", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                getattr(SessionTests(name), name)()
        self.assertIs(session.STATE_ROOT, before)

    def qa_record(self, project):
        return next(r for r in session.state_show(project)["records"] if r["kind"] == "qa-result")

    def test_optimize_skill_install_keeps_qa_result_fresh_until_product_changes(self):
        for use_git in (False, True):
            with self.subTest(git=use_git), tempfile.TemporaryDirectory() as d:
                project = make_project(d, git=use_git)
                self.prep("dev", project, dry_run=False)
                session.state_add(project, "qa", "qa-result", "login PASS")
                optimized = self.prep("optimize", project, dry_run=False, in_place=not use_git)
                # git: OPTIMIZE installs into its worktree, so also install into the live project directly
                install_skills(project, ["performance-optimization", "task-prioritization"])
                self.assertEqual(optimized["isolation"]["isolated"], use_git)
                self.assertTrue((project / ".agents/skills/performance-optimization/SKILL.md").is_file())
                self.assertNotIn("stale", self.qa_record(project))
                session.state_add(project, "qa", "note", "shared state grows")  # scenario: shared state file
                (session.state_dir(project) / "report.md").write_text("evidence")
                self.assertNotIn("stale", self.qa_record(project))
                (project / "app.py").write_text("x=1\n")
                self.assertTrue(self.qa_record(project)["stale"])
                if use_git:
                    subprocess.run(["git", "worktree", "prune"], cwd=project, capture_output=True)

    def test_user_files_under_agents_still_invalidate_verification(self):
        def add_new_skill(project, skills):
            (skills / "mine").mkdir()
            (skills / "mine/SKILL.md").write_text("mine")

        def edit_installed_skill(project, skills):
            with (skills / "completion-verification/SKILL.md").open("a") as f:
                f.write("\nmy rule\n")

        def add_file_inside_installed_skill(project, skills):
            (skills / "completion-verification/notes.md").write_text("notes")

        def edit_preserved_user_skill(project, skills):
            (skills / "requirement-discovery/SKILL.md").write_text("mine v2")

        def add_other_agents_file(project, skills):
            (project / ".agents/notes.md").write_text("notes")

        for change in (add_new_skill, edit_installed_skill, add_file_inside_installed_skill,
                       edit_preserved_user_skill, add_other_agents_file):
            for use_git in (False, True):
                with self.subTest(change=change.__name__, git=use_git), tempfile.TemporaryDirectory() as d:
                    project = make_project(d, git=use_git)
                    skills = project / ".agents/skills"
                    (skills / "requirement-discovery").mkdir(parents=True)
                    (skills / "requirement-discovery/SKILL.md").write_text("mine")
                    install_skills(project, ["completion-verification", "requirement-discovery"])
                    self.assertEqual((skills / "requirement-discovery/SKILL.md").read_text(), "mine")
                    session.state_add(project, "qa", "qa-result", "PASS")
                    self.assertNotIn("stale", self.qa_record(project))
                    change(project, skills)
                    self.assertTrue(self.qa_record(project)["stale"])

    def test_untracked_non_ascii_product_file_invalidates_verification(self):
        with tempfile.TemporaryDirectory() as d:
            project = make_project(d)
            session.state_add(project, "qa", "qa-result", "PASS")
            (project / "한글 기능.py").write_text("x=1")
            self.assertTrue(self.qa_record(project)["stale"])

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

    def test_start_sh_uses_python_when_python3_is_not_on_path(self):
        with tempfile.TemporaryDirectory() as d:
            bin_dir = Path(d) / "bin"
            bin_dir.mkdir()
            (bin_dir / "dirname").symlink_to("/usr/bin/dirname")
            fake_python = bin_dir / "python"
            fake_python.write_text(
                '#!/bin/sh\n'
                'if [ "$1" = "-c" ]; then exit 0; fi\n'
                'printf "%s\\n" "$@" > "$PYTHON_LAUNCH_LOG"\n'
            )
            fake_python.chmod(0o755)
            log = Path(d) / "launch.txt"
            env = {**os.environ, "PATH": str(bin_dir), "PYTHON_LAUNCH_LOG": str(log)}
            out = subprocess.run(["/bin/bash", str(ROOT / "start.sh"), "qa", "--dry-run"],
                                 cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(log.read_text().splitlines(), ["-m", "harness", "start", "qa", "--dry-run"])

    def test_start_sh_reports_missing_python_cleanly(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "dirname").symlink_to("/usr/bin/dirname")
            env = {**os.environ, "PATH": d}
            out = subprocess.run(["/bin/bash", str(ROOT / "start.sh"), "dev", "--dry-run"],
                                 cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 127)
            self.assertIn("Python 3.11+ not found", out.stderr)

    def test_start_sh_overrides_cp949_for_unicode_project_path(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d) / "한글 프로젝트"
            project_root.mkdir()
            project = make_project(str(project_root))
            env = {**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "cp949"}
            out = subprocess.run(["/bin/bash", str(ROOT / "start.sh"), "dev", "--dry-run"],
                                 cwd=project, env=env, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(out.returncode, 0, out.stderr)
            report = json.loads(out.stdout)
            self.assertEqual(report["project"], str(project.resolve()))
            self.assertEqual(report["model"]["model"], "gpt-6.1-sol")


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

    def test_partial_start_failure_does_not_raise_keyerror(self):
        from unittest import mock
        ok = {"seconds": 0.1, "exit": 0, "max_rss_kb": 1, "stdout_sha256": "a", "stdout_bytes": 1}
        bad = {"error": "boom", "exit": -1, "seconds": 0.0, "max_rss_kb": 0, "stdout_sha256": "", "stdout_bytes": 0}
        for seq, status in (([ok, bad, ok], "failed"), ([bad, ok, ok], "failed"), ([ok, {"timeout": True, "seconds": 1}, ok], "timeout"),
                            ([ok, {**ok, "stdout_sha256": "b"}, ok], "failed"), ([ok, {**ok, "exit": 2}, ok], "failed")):
            with mock.patch("harness.measure._one", side_effect=list(seq)):
                self.assertEqual(measure(["x"], repeat=3, warmup=0)["status"], status)

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


class BaselineServerTests(unittest.TestCase):
    def test_port_conflict_gives_actionable_error(self):
        import socket
        from harness.web_probe import serve_baseline
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            s.listen()
            with self.assertRaises(ValueError) as cm:
                serve_baseline("127.0.0.1", s.getsockname()[1])
            self.assertIn("different --port", str(cm.exception))


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
