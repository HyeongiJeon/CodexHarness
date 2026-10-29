"""Validate discoverable skills/config contracts and avoid silent missing artifacts."""
from pathlib import Path
import re
import tomllib
from .roles import ROOT, ROLES


def validate(root: Path = ROOT) -> list[str]:
    errors = []
    for required in ("AGENTS.md", "README.md", "Makefile", "docs/skills.md"):
        if not (root / required).is_file():
            errors.append(f"missing {required}")
    for bundle in (root / ".codex", root / "configs/inherited"):
        try:
            config = tomllib.loads((bundle / "config.toml").read_text())
            for name in ROLES:
                role = config["agents"][name]
                path = (bundle / role["config_file"]).resolve()
                path.relative_to(bundle.resolve())
                data = tomllib.loads(path.read_text())
                for key in ("name", "description", "developer_instructions"):
                    if not data.get(key):
                        errors.append(f"{path}: missing {key}")
                if "astra" in data.get("model", "").lower():
                    errors.append(f"{path}: prohibited model")
                if bundle.name == "inherited" and "model" in data:
                    errors.append(f"{path}: inherited role forces a model")
        except (OSError, ValueError, KeyError) as exc:
            errors.append(f"{bundle}: {exc}")
    skills = list((root / ".agents/skills").glob("*/SKILL.md"))
    if not skills:
        errors.append("no discoverable skills")
    for path in skills:
        body = path.read_text()
        front = re.match(r"\A---\n(.*?)\n---\n", body, re.S)
        if not front:
            errors.append(f"{path}: missing frontmatter")
            continue
        for key in ("name", "description"):
            if not re.search(rf"^{key}:\s*\S", front[1], re.M):
                errors.append(f"{path}: missing {key}")
        for ref in re.findall(r"\]\(([^)]+)\)", body):
            if "://" not in ref and not ref.startswith("#") and not (path.parent / ref.split("#")[0]).exists():
                errors.append(f"{path}: broken reference {ref}")
    return errors
