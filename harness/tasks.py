"""Small task contracts: dependencies, path ownership and evidence, not a scheduler."""
from pathlib import PurePosixPath

REQUIRED = {"id", "role", "objective", "inputs", "outputs", "acceptance", "paths", "depends_on", "verify"}


def normalize(path: str) -> str:
    p = PurePosixPath(path)
    if not path or p.is_absolute() or ".." in p.parts or str(p) == ".":
        raise ValueError(f"invalid owned path: {path!r}")
    return str(p).rstrip("/")


def overlaps(a: str, b: str) -> bool:
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def validate_plan(plan: dict) -> list[str]:
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    errors = []
    tasks = plan.get("tasks", [])
    if not isinstance(tasks, list) or any(not isinstance(t, dict) for t in tasks):
        return ["tasks must be a list of objects"]
    for task in tasks:
        if not isinstance(task.get("id"), str) or not task["id"]:
            errors.append("each task needs a nonempty string id")
        for key in ("paths", "depends_on"):
            value = task.get(key)
            if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
                errors.append(f"{task.get('id')}: {key} must be a list of strings")
    if errors:
        return errors
    ids = [t.get("id") for t in tasks]
    if not tasks:
        return ["plan has no tasks"]
    if len(ids) != len(set(ids)):
        errors.append("duplicate task IDs")
    ancestors = {}
    for task in tasks:
        missing = REQUIRED - task.keys()
        if missing:
            errors.append(f"{task.get('id')}: missing {sorted(missing)}")
        for key in ("objective", "inputs", "outputs", "acceptance", "paths", "verify"):
            if not task.get(key):
                errors.append(f"{task.get('id')}: empty {key}")
        deps = task.get("depends_on", [])
        if any(d not in ids for d in deps):
            errors.append(f"{task.get('id')}: unknown dependency")
        ancestors[task.get("id")] = set(deps)
        for path in task.get("paths", []):
            try:
                normalize(path)
            except ValueError as exc:
                errors.append(str(exc))
    for _ in tasks:
        for key, deps in ancestors.items():
            deps.update(set().union(*(ancestors.get(d, set()) for d in tuple(deps))))
            if key in deps:
                errors.append(f"{key}: dependency cycle")
    for i, left in enumerate(tasks):
        for right in tasks[i + 1:]:
            # Sequential handoff can share paths; simultaneously runnable tasks cannot.
            if left.get("id") in ancestors.get(right.get("id"), set()) or right.get("id") in ancestors.get(left.get("id"), set()):
                continue
            for a in left.get("paths", []):
                for b in right.get("paths", []):
                    try:
                        conflict = overlaps(normalize(a), normalize(b))
                    except ValueError:
                        continue
                    if conflict:
                        errors.append(f"parallel path conflict: {left.get('id')} / {right.get('id')}: {a} <> {b}")
    return sorted(set(errors))
