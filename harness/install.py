"""Install project skills without overwriting the assignment's existing files."""
from pathlib import Path
import shutil
from .roles import ROOT


def install_skills(project: Path, names: list[str] | None = None) -> dict:
    project = project.resolve(strict=True)
    if not project.is_dir():
        raise ValueError("project must be an existing directory")
    source = ROOT / ".agents/skills"
    available = {p.name: p for p in source.iterdir() if (p / "SKILL.md").is_file()}
    selected = names or sorted(available)
    unknown = set(selected) - available.keys()
    if unknown:
        raise ValueError(f"unknown skills: {sorted(unknown)}")
    target = project / ".agents/skills"
    if not target.resolve().is_relative_to(project):
        raise ValueError("project skill path resolves outside the project; preserve existing setup")
    target.mkdir(parents=True, exist_ok=True)
    result = {"installed": [], "preserved_existing": []}
    for name in selected:
        destination = target / name
        if destination.exists() or destination.is_symlink():
            result["preserved_existing"].append(name)
        else:
            shutil.copytree(available[name], destination)
            result["installed"].append(name)
    return result
