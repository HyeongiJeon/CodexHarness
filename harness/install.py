"""Install project skills without overwriting the assignment's existing files."""
from pathlib import Path
import re
import shutil
from .roles import ROOT


def install_skills(project: Path, names: list[str] | None = None) -> dict:
    project = project.resolve(strict=True)
    if not project.is_dir():
        raise ValueError("project must be an existing directory")
    source = ROOT / ".agents/skills"
    available = {p.name: p for p in source.iterdir() if (p / "SKILL.md").is_file()}
    selected = list(dict.fromkeys(names or sorted(available)))
    unknown = set(selected) - available.keys()
    if unknown:
        raise ValueError(f"unknown skills: {sorted(unknown)}")
    requested = set(selected)
    # Follow bundled Markdown links transitively, including cycles, before copying.
    # Existing project skills remain untouched; their bundled dependencies can
    # still be repaired when an older selective installation is run again.
    source = source.resolve()
    scheduled = set(selected)
    for name in selected:
        for path in sorted(available[name].rglob("*.md")):
            for ref in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                if "://" in ref or ref.startswith("#"):
                    continue
                linked = (path.parent / ref.split("#", 1)[0]).resolve()
                if not linked.is_relative_to(source):
                    continue
                relative = linked.relative_to(source)
                dependency = relative.parts[0] if relative.parts else None
                if dependency in available and dependency not in scheduled:
                    scheduled.add(dependency)
                    selected.append(dependency)
    target = project / ".agents/skills"
    if not target.resolve().is_relative_to(project):
        raise ValueError("project skill path resolves outside the project; preserve existing setup")
    target.mkdir(parents=True, exist_ok=True)
    result = {"installed": [], "preserved_existing": [],
              "dependencies": [name for name in selected if name not in requested]}
    for name in selected:
        destination = target / name
        if destination.exists() or destination.is_symlink():
            result["preserved_existing"].append(name)
        else:
            shutil.copytree(available[name], destination)
            result["installed"].append(name)
    return result
