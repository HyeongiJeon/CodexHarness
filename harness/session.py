"""One-command session launcher for the five specialist modes.

Everything here runs BEFORE Codex starts: it resolves paths, links skills, picks
the single required model and builds the launch command. It never edits
user/managed Codex configuration, authentication or permissions, and it never
claims a configuration applies to an already running session.
"""
from __future__ import annotations

import filecmp
import hashlib
import json
import os
import re
import shutil
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from .install import install_skills
from .roles import MODEL, ROOT, launch_overrides

STATE_ROOT = Path(os.environ.get("HARNESS_STATE_ROOT") or ROOT / ".harness" / "sessions")
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
            raise SessionError(f"--project is not a directory: {project}")
    else:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True)
        project = Path(top.stdout.strip()).resolve() if top.returncode == 0 and top.stdout.strip() else cwd
    if project == ROOT or ROOT in project.parents:
        raise SessionError("project resolves to the CodexHarness repository itself; run from your task project "
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


class SessionError(ValueError):
    """Preparation/configuration failure (not a Codex launch failure)."""


def check_model_available(catalog_reader=None) -> dict:
    """Advisory only: the catalog never blocks a launch and never selects another model.

    Sol 6.1 is the only allowed model. Whether it is usable is decided by the real Codex run (explicit -m, no fallback).
    """
    slugs = None
    if catalog_reader is not None:
        slugs = catalog_reader()
    elif shutil.which("codex"):
        try:
            p = subprocess.run(["codex", "debug", "models"], capture_output=True, text=True, timeout=30)
            if p.returncode == 0:
                data = json.loads(p.stdout)
                items = data.get("models", data) if isinstance(data, dict) else data
                slugs = [m["slug"] for m in items if isinstance(m, dict) and m.get("slug")]
        except (OSError, ValueError, subprocess.TimeoutExpired):
            slugs = None
    if slugs is None:
        return {"model": MODEL, "catalog": "unreadable", "status": "unverified",
                "note": "catalog could not be read; the explicit -m flag makes Codex fail loudly if the model is unavailable (no fallback)"}
    if MODEL not in slugs:
        return {"model": MODEL, "catalog": "does not list model", "status": "not_listed",
                "note": f"{MODEL} is not in the local catalog (catalogs can be incomplete); launching anyway - if Codex rejects the model it fails and nothing falls back"}
    return {"model": MODEL, "catalog": "lists model", "status": "listed",
            "note": "catalog listing is not proof that a model call succeeds; only a real run proves it"}


def detect_workdir(project: Path, cwd: Path | None = None) -> Path | None:
    """The registered OPTIMIZE worktree of THIS project if cwd is inside it; any other directory is not a workspace."""
    cwd = (cwd or Path.cwd()).resolve()
    wt = (state_dir(project) / "optimize-worktree").resolve()
    if not wt.is_dir() or (cwd != wt and wt not in cwd.parents):
        return None
    top = _git(wt, "rev-parse", "--show-toplevel")
    branch = _git(wt, "rev-parse", "--abbrev-ref", "HEAD")
    if top is None or Path(top.strip()).resolve() != wt or branch is None or branch.strip() != "harness/optimize":
        return None
    return wt


def _git(project: Path, *args: str) -> str | None:
    p = subprocess.run(["git", *args], cwd=project, capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def _is_harness_skill_copy(project: Path, path: Path) -> bool:
    """True only for a file byte-identical to its bundled counterpart in <project>/.agents/skills.

    Files the user wrote or edited differ from the bundle (or have no counterpart), so they still count.
    """
    if not path.is_relative_to(project / ".agents/skills") or path.is_symlink():
        return False
    bundled = ROOT / ".agents/skills" / path.relative_to(project / ".agents/skills")
    try:
        return bundled.is_file() and filecmp.cmp(path, bundled, shallow=False)
    except OSError:
        return False


def fingerprint(project: Path) -> str:
    """Fingerprint project content, excluding generated state and unmodified harness skills stored inside it."""
    project = project.resolve()
    state_root = STATE_ROOT.resolve()
    # An OPTIMIZE worktree may itself live below STATE_ROOT. Its source files
    # must still count: exclude state only when its root is inside this project.
    exclude_state = state_root != project and state_root.is_relative_to(project)

    def is_state(path: Path) -> bool:
        return exclude_state and path.resolve().is_relative_to(state_root)

    def is_generated(path: Path) -> bool:
        return is_state(path) or _is_harness_skill_copy(project, path)

    h = hashlib.sha256()
    head = _git(project, "rev-parse", "HEAD")
    if head is not None:
        h.update(head.encode())
        h.update((_git(project, "diff", "HEAD") or "").encode())
        # -z: without it git quotes non-ASCII paths, which then fail to stat and silently drop out
        for rel in sorted(filter(None, (_git(project, "ls-files", "-z", "-o", "--exclude-standard") or "").split("\0"))):
            if is_generated(project / rel):
                continue
            try:
                st = (project / rel).stat()
                h.update(f"{rel}:{st.st_size}:{st.st_mtime_ns}".encode())
            except OSError:
                pass
        return "git:" + h.hexdigest()[:16]
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__"}
    count = 0
    for directory, directories, files in os.walk(project):
        parent = Path(directory)
        directories[:] = sorted(name for name in directories
                                if name not in skip and not is_state(parent / name))
        for name in sorted(files):
            path = parent / name
            if name in skip or is_generated(path) or not path.is_file():
                continue
            count += 1
            if count > 20000:
                h.update(b"truncated")
                break
            st = path.stat()
            h.update(f"{path.relative_to(project)}:{st.st_size}:{st.st_mtime_ns}".encode())
        if count > 20000:
            break
    return "fs:" + h.hexdigest()[:16]


def state_dir(project: Path) -> Path:
    digest = hashlib.sha256(str(project).encode()).hexdigest()[:8]
    return STATE_ROOT / f"{project.name}-{digest}"


VERIFY_KINDS = {"qa-result", "defect", "perf", "preview"}
KINDS = {"command", "decision", "change", "qa-result", "defect", "perf", "preview", "open-item", "note"}


def _workspace(project: Path, workdir: Path | None) -> dict:
    """Where the work lives: the live project or an isolated worktree, with branch and commit."""
    where = (workdir or project).resolve()
    info = {"kind": "worktree" if workdir and workdir.resolve() != project.resolve() else "project", "path": str(where)}
    branch = _git(where, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _git(where, "rev-parse", "HEAD")
    if branch is not None:
        info["branch"] = branch.strip()
    if commit is not None:
        info["commit"] = commit.strip()
    # harness-installed skills (.agents) do not count as the user's uncommitted work
    info["dirty"] = any(line and not line.startswith("?? .agents/") for line in (_git(where, "status", "--porcelain") or "").splitlines())
    return info


def state_add(project: Path, session: str, kind: str, text: str, workdir: Path | None = None) -> dict:
    if kind not in KINDS:
        raise SessionError(f"kind must be one of {sorted(KINDS)}")
    if session not in MODES:
        raise SessionError(f"session must be one of {sorted(MODES)}")
    if not text.strip() or len(text) > 4000:
        raise SessionError("text must be 1..4000 characters (concise facts, not transcripts)")
    workspace = _workspace(project, workdir)
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session": session, "kind": kind,
              "text": text.strip(), "workspace": workspace, "fingerprint": fingerprint(Path(workspace["path"]))}
    directory = state_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "state.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _integrated(project: Path, commit: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=project, capture_output=True).returncode == 0


def state_show(project: Path, kind: str | None = None, limit: int = 50) -> dict:
    """stale = the record's OWN workspace changed since it was written.
    not_integrated = the record lives in a separate worktree whose commit is not in the project's HEAD (or has uncommitted work)."""
    path = state_dir(project) / "state.jsonl"
    cache: dict[str, str | None] = {}

    def current(where: str) -> str | None:
        if where not in cache:
            cache[where] = fingerprint(Path(where)) if Path(where).is_dir() else None
        return cache[where]

    records = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict) or (kind and rec.get("kind") != kind):
                continue
            ws = rec.get("workspace")
            if not isinstance(ws, dict) or not ws.get("path"):
                ws = {"kind": "project", "path": str(project)}
            if rec.get("kind") in VERIFY_KINDS:
                now = current(ws["path"])
                if now is None:
                    rec["stale"] = "unknown"
                    rec["stale_reason"] = "workspace no longer exists"
                elif rec.get("fingerprint") != now:
                    rec["stale"] = True
            if ws.get("kind") == "worktree":
                done = bool(ws.get("commit")) and not ws.get("dirty") and _integrated(project, ws["commit"])
                if not done:
                    rec["not_integrated"] = True
                    rec["integration_note"] = ("result reflects uncommitted work or commits in the isolated worktree that are NOT in the project HEAD; "
                                               "it is not part of the project until committed and merged")
            records.append(rec)
    return {"project": str(project), "project_fingerprint": fingerprint(project), "records": records[-limit:],
            "note": "stale: the record's own workspace changed after it was written (gitignored files and unmodified harness-installed skill copies are not fingerprinted). not_integrated: separate worktree result not yet merged into the project HEAD. decision/change/note records are never marked stale"}


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
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        (path.parent / "project.txt").write_text(str(project))
    if path.exists():
        current = _git(path, "rev-parse", "--abbrev-ref", "HEAD")
        if current is None or current.strip() != branch:
            raise SessionError(f"{path} exists but is not a valid worktree on {branch}; remove it (git worktree remove --force) and retry")
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
        raise SessionError(f"git worktree add failed: {p.stderr.strip()[:300]}")
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
            f"Skill의 Related skills 링크 대상이 프로젝트에 없으면 필요할 때 {ROOT / '.agents/skills'}/<이름>/SKILL.md 를 직접 읽어라. "
            "프로젝트 AGENTS.md와 과제 지침, 시험 제한이 항상 우선한다. 사용자 승인 없이 구현을 시작하지 말라.")


def prepare(mode: str, project_arg: Path | None = None, *, dry_run: bool = False, exam: bool = False, in_place: bool = False,
            skip_skills: bool = False, catalog_reader=None) -> dict:
    """Pure preparation: never launches Codex and does not require it to be installed."""
    from .validate import validate
    if mode not in MODES:
        raise SessionError(f"unknown mode {mode}")
    spec = MODES[mode]
    project = find_project(project_arg)
    errors = validate()
    if errors:
        raise SessionError(f"harness validation failed: {errors[:3]}")
    report: dict = {"mode": mode, "purpose": spec["purpose"], "project": str(project), "harness": str(ROOT),
                    "dry_run": dry_run, "codex": shutil.which("codex"), "notes": []}
    report["model"] = check_model_available(catalog_reader)
    report["model_policy"] = f"{MODEL} only for main session and all subagents; no routing, no fallback"
    bundle = ROOT / ".codex"

    workdir = project
    if spec.get("isolate"):
        iso = ensure_worktree(project, dry_run)
        report["isolation"] = iso
        if iso["isolated"]:
            workdir = Path(iso["path"]) if not iso.get("would_create") else project
        elif not in_place:
            raise SessionError(f"cannot isolate OPTIMIZE: {iso['reason']}. Re-run with --in-place only after backing up / committing your work")
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

    cmd = ["codex", "-C", str(workdir), "-m", MODEL, *launch_overrides(bundle)]
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
    report["not_verified"] = ["real model calls (only a live run proves that gpt-6.1-sol is usable)",
                              "Cofa-specific behaviour (this launcher only prepares before Codex starts)"]
    for key in ("warning", "limitations"):
        if report.get("isolation", {}).get(key):
            report["notes"].append(f"{mode}: {report['isolation'][key]}")
    if not dry_run and mode != "explain":
        state_add(project, mode, "note", f"session prepared: model={MODEL} skills={names}")
    return report
