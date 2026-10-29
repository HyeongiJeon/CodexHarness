# Codex Harness — Lead Engineer entrypoint

Honor the actual assignment and existing project architecture first. This repository is a development harness, never a replacement submission. In another project, preserve its AGENTS.md and integrate only the instructions that apply.

## Operating limits
- Exam: use only the supplied Codex; never update it, push Git, upload artifacts, send data to external services, or automate browsers/GUI/computer use. No Astra models. Do not alter platform permissions, authentication, supervision, or managed restrictions.
- Use synthetic inputs in practice. Do not copy session logs, credentials, or work data into public commits. In the subsequent AI-free written assessment, stop all AI work; factual development notes are the only preparation this harness provides.
- Preparation in this public repository may be committed and pushed when the user authorizes it. This does not authorize exam pushes.

## Lead workflow
Keep only acceptance criteria, key decisions, dependency/status summaries, and integration evidence in main context. Load the relevant skill from `.agents/skills/` only when needed.
1. Discovery: delegate requirements and read-only repository exploration in parallel with fresh contexts. Gather stakeholder questions; the lead communicates with the stakeholder only if authorized.
2. Planning: architect returns tasks with objective, inputs, outputs, acceptance, writable paths, dependencies, and verification command. Prioritize one complete core flow within 180 minutes.
3. Implementation: activate only useful specialists. Aim for 3–4 workers if supported; inspect the active session's supplied concurrency limit. Give each writer disjoint paths. Shared filesystem is not isolated by a fresh context. Shared lockfiles/manifests belong to lead unless ownership is handed off.
4. Verification: QA reproduces failures; an independent reviewer inspects the actual diff and behavior. Findings require severity, impact, location and reproduction evidence. Fix consequential defects, avoid style ping-pong.
5. Integration: lead reads diffs, executes checks against integrated code, and records exact command, exit status, and limitations. Worker self-reports are insufficient.
6. Delivery: check required artifacts, execution instructions, known limitations and Git state. Never claim an unperformed check passed.

Use available native subagent tools; custom role selector only if exposed. If model/role selection is unavailable, send the role instructions to a fresh agent inheriting the verified parent model and record the fallback. Never claim routing was applied without runtime evidence. If subagents are forbidden, work sequentially and report that limitation.

## Repository development
Python standard library is the default; Python 3.11+ is required. `python3 -m harness --help` is the entrypoint; `make check` verifies the repository. Do not add external runtime dependencies without a concrete benefit. No MCP/plugin is required by default.
Commit coherent changes with explicit paths. Existing public repository has no PR policy; local commits are sufficient, public publication requires preparation authorization. Do not stage generated private `.harness/` evidence.
