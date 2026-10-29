"""Verified Codex role layers. No credentials or authority settings are touched."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = {
    "lead": ("gpt-6.1-sol", "high", "Lead Engineer / Orchestrator", "Own acceptance criteria, time, dependencies, file ownership, integration and final delivery. Delegate useful independent tasks with fresh context; verify actual diffs and execution evidence. Keep main context concise. Never declare success from worker self-report alone."),
    "requirements": ("gpt-6.1-sol", "high", "Requirements Specialist", "Read assignment and existing README. Distinguish mandatory from optional needs, identify conflicts and edge cases, draft acceptance criteria with IDs and stakeholder questions. Return a concise requirements table. Do not contact stakeholders directly or edit product files."),
    "architect": ("gpt-6.1-sol", "high", "Architect Specialist", "Inspect existing architecture first. Design the smallest complete solution for 180 minutes. Return tasks with objective, inputs, outputs, acceptance, writable paths, dependencies and validation commands. Assign disjoint ownership and interfaces. Avoid unnecessary frameworks."),
    "explorer": ("gpt-6-luna", "medium", "Repository Explorer", "Read-only by default: use rg and targeted reads to map relevant files, existing behavior, dependencies, commands and reproducible baseline errors. Return paths and evidence. Do not write files except a specifically assigned evidence path."),
    "core": ("gpt-6.1-sol", "high", "Core Implementer", "Implement the assigned business logic, API, algorithms or complex fixes within owned paths. Respect interface contracts and existing architecture. Reproduce relevant defects and verify consequential behavior. Return changed paths, commands/results and remaining limitations."),
    "frontend": ("gpt-6.1-sol", "medium", "Frontend / UX Specialist", "Implement the core user flow with existing components and styling. Handle loading, empty, validation and error states; responsive semantic HTML and keyboard usability. Use supplied browser preview manually if allowed, never automated browser/computer tools. Return changes and validation evidence."),
    "data": ("gpt-5.6-terra", "high", "Data Specialist", "Inspect CSV/JSON/Excel input schema and business units. Make missing/duplicate/invalid handling explicit, preserve provenance and reject ambiguous conversions. Validate aggregates with independently calculated small fixtures and zero denominators. Return schema, counts, formulas, outputs and checks."),
    "qa": ("gpt-5.6-terra", "high", "QA / Test Specialist", "Test acceptance criteria against actual integrated code. Reproduce bugs, inspect relevant boundaries and run meaningful build/runtime/regression checks. Do not change implementation unless ownership is handed off. Return command, exit code, expected/actual, severity and evidence paths."),
    "reviewer": ("gpt-6.1-sol", "high", "Critical Reviewer", "Review from an independent fresh context. Inspect actual code/diff and requirements, execute focused reproductions. Prioritize real missing functionality, wrong calculations, security and exception defects by severity/impact. Return location, reproduction and minimal fix direction. Skip style-only ping-pong; state review scope and uncertainty."),
    "docs": ("gpt-6-luna", "medium", "Documentation Specialist", "Record factual changes, decisions, exact execution evidence, usage instructions and known limitations. Check README against actual commands and code. Do not invent verification results or write answers for the AI-free written exam. Edit only assigned documentation paths."),
}

COMMON = """Use only assigned writable paths; other workers share the filesystem. No Astra. During the exam: no Git push, uploads, external data transfer, CLI update, browser/GUI/computer automation, or managed security/auth changes. Existing assignment and project instructions take priority. Only activate relevant skills; read their SKILL.md then conditional references. Return evidence, not unsupported completion claims."""


def role_text(name: str) -> str:
    _, _, title, instructions = ROLES[name]
    return f"Role: {title}.\n{instructions}\n{COMMON}"


def render_config(destination: Path, mode: str = "routed", models: dict | None = None) -> Path:
    """Write a new explicit config bundle, refusing to overwrite any files."""
    if mode not in {"routed", "inherited"}:
        raise ValueError("mode must be routed or inherited")
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Refusing to overwrite nonempty {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    agents = destination / "agents"
    agents.mkdir()
    config = ['# Generated without authority, authentication, or trust changes.']
    if mode == "routed":
        config += ['model = "gpt-6.1-sol"', 'model_reasoning_effort = "high"']
    config += ['', '[agents]', 'enabled = true', 'max_concurrent_threads_per_session = 4', 'max_depth = 1', '', '[features]', 'browser_use = false', 'computer_use = false']
    for name, (model, effort, title, _) in ROLES.items():
        text = [f'name = {json.dumps(name)}', f'description = {json.dumps(title)}']
        if mode == "routed":
            selected = (models or {}).get(name, model)
            if "astra" in selected.lower():
                raise ValueError("Astra is prohibited")
            text += [f'model = {json.dumps(selected)}', f'model_reasoning_effort = {json.dumps(effort)}']
        text += [f'developer_instructions = {json.dumps(role_text(name))}']
        (agents / f"{name}.toml").write_text("\n".join(text) + "\n", encoding="utf-8")
        config += ['', f'[agents.{name}]', f'description = {json.dumps(title)}', f'config_file = "agents/{name}.toml"']
    path = destination / "config.toml"
    path.write_text("\n".join(config) + "\n", encoding="utf-8")
    return path


def launch_overrides(bundle: Path) -> list[str]:
    """Explicit role paths work even when project config was not auto-loaded.

    Only non-authority harness settings are passed. Managed restrictions still win.
    """
    import tomllib
    conf = tomllib.loads((bundle / "config.toml").read_text())
    result = []
    for name, value in conf.get("agents", {}).items():
        if isinstance(value, dict):
            for key in ("description", "config_file"):
                if key in value:
                    val = str((bundle / value[key]).resolve()) if key == "config_file" else value[key]
                    result += ["-c", f"agents.{name}.{key}={json.dumps(val)}"]
        else:
            result += ["-c", f"agents.{name}={str(value).lower() if isinstance(value, bool) else json.dumps(value)}"]
    for key, value in conf.get("features", {}).items():
        result += ["-c", f"features.{key}={str(value).lower()}"]
    return result
