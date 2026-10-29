---
name: parallel-implementation
description: "Coordinate explicitly authorized parallel coding with ownership and integration checks; use for independent components with stable interfaces."
---
# Parallel Implementation

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Delegation authorization, component plan, available agents, workspace state, time budget.

Before assigning shared-repository work, read [references/coordination.md](references/coordination.md).

## Procedure

1. Check authorization and agent availability; otherwise execute the same dependency order sequentially.
2. Partition by independent file ownership and stable contracts. Assign shared entrypoints, lockfiles, and integration to one owner.
3. Give workers acceptance criteria, allowed paths, interfaces, checks, deadline, and return format. Resolve design uncertainty before delegating it.
4. Integrate early, inspect actual diffs, and run the combined application. Resolve contract conflicts centrally.

**Output contract:** Ownership map, integrated changes, worker evidence, combined validation, and unresolved integration risks.

**Tools:** Available collaboration tools only with authorization; git status/diff and existing checks.

**Verification:** Required outputs are integrated and combined behavior works beyond isolated worker tests.

**Failure handling:** On collisions or late workers, stop that assignment, preserve useful work, and finish the required path centrally. Never reset another worker’s changes.

**Related skills:** [architecture-planning](../architecture-planning/SKILL.md), [time-budget-management](../time-budget-management/SKILL.md), [completion-verification](../completion-verification/SKILL.md).
