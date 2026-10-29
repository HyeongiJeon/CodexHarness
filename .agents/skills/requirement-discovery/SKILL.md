---
name: requirement-discovery
description: "Turn an underspecified build request into testable acceptance criteria; use when missing requirements change scope, behavior, or grading."
---
# Requirement Discovery

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Task statement, repository, exam rules, rubric/examples, time remaining.

## Procedure

1. Inspect original project instructions, entrypoints, tests, and supplied assets before proposing changes.
2. Extract required behavior, input/output contracts, constraints, and acceptance evidence. Label each requirement explicit, inferred, or unresolved.
3. Resolve ordinary implementation choices yourself. Ask only about missing information that materially changes the deliverable; continue independent inspection meanwhile.
4. Map every required outcome to an observable check and choose the smallest coherent scope that satisfies them.

**Output contract:** A requirement-to-check map, labeled assumptions, justified exclusions, and any blocking question.

**Tools:** rg, local file reads, existing tests, CLI help; authorized connected sources only when necessary.

**Verification:** Every explicit requirement has a check; supplied assets and existing behavior are accounted for.

**Failure handling:** Record conflicting requirements; preserve explicit exam/project constraints. Never silently omit mandatory behavior.

**Related skills:** [architecture-planning](../architecture-planning/SKILL.md), [task-prioritization](../task-prioritization/SKILL.md), [decision-and-evidence-recording](../decision-and-evidence-recording/SKILL.md).
