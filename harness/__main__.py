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
    data.add_argument("files", nargs="*", type=Path)
    data.add_argument("--config", type=Path)
    data.add_argument("--sample-rows", type=int, default=1000)
    data.add_argument("--encoding")
    data.add_argument("--value")
    data.add_argument("--group-by", action="append")
    data.add_argument("--id-column")
    corpus = sub.add_parser("corpus", help="local inventory, index, retrieval and bounded evidence packs")
    corp = corpus.add_subparsers(dest="corpus_command", required=True)
    inv = corp.add_parser("inventory")
    inv.add_argument("root", type=Path)
    inv.add_argument("--limit", type=int, default=1000)
    idx = corp.add_parser("index")
    idx.add_argument("root", type=Path)
    idx.add_argument("--db", type=Path, required=True)
    idx.add_argument("--metadata", type=Path)
    idx.add_argument("--max-chars", type=int, default=2_000_000)
    for command in ("search", "evidence-pack"):
        p = corp.add_parser(command)
        p.add_argument("--db", type=Path, required=True)
        p.add_argument("--query", required=True, action="append" if command == "evidence-pack" else "store")
        p.add_argument("--mode", choices=("literal", "identifier", "regex", "fts"), default="literal")
        for name in ("status", "date-from", "date-to", "entity"):
            p.add_argument('--' + name)
        p.add_argument("--max-chars", type=int, default=16000 if command == "evidence-pack" else 600)
        if command == "search":
            p.add_argument("--limit", type=int, default=20)
        else:
            p.add_argument("--max-evidence", type=int, default=12)
            p.add_argument("--question", default="")
            p.add_argument("--output", type=Path)
    ev = sub.add_parser("evidence", help="rehash/re-extract originals and reconcile explicit source facts")
    es = ev.add_subparsers(dest="evidence_command", required=True)
    es.add_parser("verify").add_argument("pack", type=Path)
    sy = es.add_parser("synthesize")
    sy.add_argument("pack", type=Path)
    sy.add_argument("--entity", required=True)
    sy.add_argument("--as-of", required=True)
    sy.add_argument("--attribute")
    cp = es.add_parser('compare')
    cp.add_argument('pack',type=Path)
    cp.add_argument('--calculation',type=Path,required=True)
    cp.add_argument('--entity',required=True)
    cp.add_argument('--attribute',required=True)
    cp.add_argument('--as-of',required=True)
    cp.add_argument('--unit',required=True)
    sub.add_parser("resources", help="read-only CPU/memory/disk observations")
    ib = sub.add_parser('intelligence-benchmark', help='local synthetic 100k/1m rows and 120-document benchmark; no AI calls')
    ib.add_argument('--output', type=Path, default=ROOT/'.harness/intelligence')
    ib.add_argument('--rows', default='100000,1000000')
    pe = sub.add_parser('prose-evaluation',help='prepare isolated Korean prose inputs or score frozen real agent outputs; no model call')
    pe.add_argument('action',choices=('prepare','score'))
    pe.add_argument('--work-dir',type=Path,default=ROOT/'.harness/prose-evaluation/run')
    pe.add_argument('--oracle',type=Path)
    pe.add_argument('--answers',type=Path)
    pe.add_argument('--audit',type=Path)
    pe.add_argument('--output',type=Path)
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
        operation = str(args.input)
        if operation == 'profile':
            from .large_data import profile_file
            if len(args.files) != 1:
                parser.error('data profile requires exactly one file')
            report = profile_file(args.files[0], args.sample_rows, args.encoding)
        elif operation == 'aggregate':
            from .large_data import aggregate_files
            config = load_json(args.config) if args.config else {}
            for key in ('value', 'group_by', 'id_column', 'encoding'):
                if getattr(args, key) is not None:
                    config[key] = getattr(args, key)
            if 'value' not in config:
                parser.error('data aggregate requires --value or config.value')
            config.setdefault('group_by', [])
            if config.get('join',{}).get('path'):
                config['join']['path'] = str(Path(config['join']['path']).resolve())
            report = aggregate_files(args.files, **config)
            report['calculation_contract'] = {'paths': [str(p.resolve()) for p in args.files], 'config': config}
        else:
            if args.files:
                parser.error('multiple files require data aggregate; legacy data FILE accepts one file')
            result = clean_sales_csv(args.input.read_text(encoding="utf-8-sig"))
            report = {"accepted": len(result.rows), "issues": [asdict(x) for x in result.issues], "regions": aggregate_by_region(result.rows)}
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif args.command == 'resources':
        from .sources import resources
        print(json.dumps(resources(), indent=2))
    elif args.command == 'intelligence-benchmark':
        from .intelligence_benchmark import run
        counts = [int(n) for n in args.rows.split(',')]
        if not counts or min(counts) < 100 or max(counts) > 10_000_000:
            parser.error('benchmark rows must be 100..10000000')
        report = run(args.output, counts)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['passed'] else 1
    elif args.command == 'prose-evaluation':
        from .prose_evaluation import prepare,score
        if args.action=='prepare':
            report=prepare(args.work_dir)
        else:
            if not args.oracle or not args.answers:
                parser.error('score requires --oracle and --answers from a completed real trial')
            report=score(args.work_dir,load_json(args.oracle),load_json(args.answers),load_json(args.audit) if args.audit else None)
        if args.output:args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps(report,ensure_ascii=False,indent=2))
    elif args.command == 'corpus':
        from .corpus import inventory, index_corpus, search
        if args.corpus_command == 'inventory':
            if args.limit < 1:
                parser.error('inventory limit must be positive')
            count, files = 0, []
            for item in inventory(args.root):
                count += 1
                if len(files) < args.limit:
                    files.append(item)
            report = {'file_count': count, 'files': files, 'truncated': count > len(files)}
        elif args.corpus_command == 'index':
            report = index_corpus(args.root, args.db, load_json(args.metadata) if args.metadata else None, args.max_chars)
        else:
            filters = {k: getattr(args, k) for k in ('status', 'date_from', 'date_to', 'entity')}
            if args.corpus_command == 'search':
                report = search(args.db, args.query, mode=args.mode, limit=args.limit, max_chars=args.max_chars, **filters)
            else:
                from .evidence import evidence_pack, serialized
                report = evidence_pack(args.db, args.query, question=args.question, mode=args.mode, max_evidence=args.max_evidence, max_chars=args.max_chars, **filters)
                if args.output:
                    args.output.write_text(serialized(report), encoding='utf-8')
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif args.command == 'evidence':
        from .evidence import verify, synthesize, compare_calculation
        pack = load_json(args.pack)
        if args.evidence_command == 'verify':
            report = verify(pack)
        elif args.evidence_command == 'compare':
            report = compare_calculation(pack, load_json(args.calculation),entity=args.entity,attribute=args.attribute,as_of=args.as_of,unit=args.unit)
        else:
            report = synthesize(pack, entity=args.entity, as_of=args.as_of, attribute=args.attribute)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report['status'] in {'verified', 'supported'} else 1
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


def load_json(path: Path) -> dict:
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('configuration/evidence JSON exceeds 32 MiB; use streaming data or a smaller evidence pack')
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('configuration/evidence must be a JSON object')
    return value


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
