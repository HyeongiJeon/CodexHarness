import argparse
import json
from pathlib import Path
import subprocess
import sys

from .roles import ROOT, ROLES, launch_overrides, render_config, role_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Codex team harness (no uploads or authority changes)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="read-only CLI and model metadata discovery")
    sub.add_parser("validate", help="validate roles, skills and required artifacts")
    role = sub.add_parser("role", help="print a role prompt for IDE/compatibility use")
    role.add_argument("name", choices=ROLES)
    config = sub.add_parser("configure", help="generate a bundle in a NEW directory; never edits user config")
    config.add_argument("destination", type=Path)
    config.add_argument("--mode", choices=("routed", "inherited"), default="inherited")
    install = sub.add_parser("install-skills", help="copy project skills, preserving every existing skill and AGENTS.md")
    install.add_argument("--project", type=Path, required=True)
    install.add_argument("--skill", action="append", help="copy only this skill; repeat as needed (default all)")
    launch = sub.add_parser("launch", help="start supplied CLI with explicit role config paths")
    launch.add_argument("--project", type=Path, default=Path.cwd())
    launch.add_argument("--mode", choices=("routed", "inherited"), default="inherited")
    launch.add_argument("--model", help="explicit verified main model; omitted means inherit installed default")
    launch.add_argument("--bundle", type=Path, help="explicit generated bundle directory instead of checked-in mode")
    launch.add_argument("--dry-run", action="store_true")
    task = sub.add_parser("plan-check", help="check dependency and file ownership contracts")
    task.add_argument("plan", type=Path)
    data = sub.add_parser("data", help="clean a local sales-schema CSV and print exact aggregates/issues")
    data.add_argument("input", type=Path)
    demo = sub.add_parser("demo", help="synthetic local web/data practice application")
    demo.add_argument("--port", type=int, default=8765)
    demo.add_argument("--host", default="127.0.0.1")
    bench = sub.add_parser("benchmark", help="run actual Codex coding exercise; private evidence stays local")
    bench.add_argument("--mode", choices=("single", "multi", "smoke"), default="smoke")
    bench.add_argument("--routing", choices=("routed", "inherited"), default="inherited")
    bench.add_argument("--model", default="gpt-6.1-sol")
    bench.add_argument("--timeout", type=int, default=600)
    recheck = sub.add_parser("benchmark-check", help="offline acceptance check of a generated synthetic benchmark project")
    recheck.add_argument("project", type=Path)
    args = parser.parse_args()
    if args.command == "doctor":
        from .doctor import inspect
        print(json.dumps(inspect(), indent=2, ensure_ascii=False))
    elif args.command == "validate":
        from .validate import validate
        errors = validate()
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
        return bool(errors)
    elif args.command == "role":
        print(role_text(args.name))
    elif args.command == "configure":
        print(render_config(args.destination, args.mode))
    elif args.command == "install-skills":
        from .install import install_skills
        print(json.dumps(install_skills(args.project, args.skill), indent=2))
    elif args.command == "launch":
        if args.model and "astra" in args.model.lower():
            parser.error("Astra is prohibited")
        bundle = args.bundle or ROOT / (".codex" if args.mode == "routed" else "configs/inherited")
        cmd = ["codex", "-C", str(args.project.resolve()), *launch_overrides(bundle)]
        if args.model:
            cmd += ["-m", args.model]
        if args.dry_run:
            print(json.dumps(cmd, indent=2))
        else:
            return subprocess.call(cmd)
    elif args.command == "plan-check":
        from .tasks import validate_plan
        errors = validate_plan(json.loads(args.plan.read_text()))
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
        return bool(errors)
    elif args.command == "demo":
        from .demo import serve
        serve(args.host, args.port)
    elif args.command == "data":
        from dataclasses import asdict
        from .data import clean_sales_csv, aggregate_by_region
        result = clean_sales_csv(args.input.read_text(encoding="utf-8-sig"))
        print(json.dumps({"accepted": len(result.rows), "issues": [asdict(x) for x in result.issues], "regions": aggregate_by_region(result.rows)}, indent=2, ensure_ascii=False))
    elif args.command == "benchmark":
        from .benchmark import run
        return run(args.mode, args.routing, args.model, args.timeout)
    elif args.command == "benchmark-check":
        from .benchmark import evaluate
        checks, passed, log = evaluate(args.project)
        print(json.dumps(checks, indent=2))
        if not passed:
            print(log, file=sys.stderr)
        return 0 if passed else 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
