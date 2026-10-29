---
name: rapid-mvp-development
description: "Build a runnable minimum product under a short deadline; use when an end-to-end required flow takes priority over optional breadth."
---
# Rapid Mvp Development

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Required user journey, acceptance criteria, repository, deadline, verification reserve.

## Procedure

1. Inspect and run the original application before changing its scaffold; reuse working components and installed dependencies.
2. Implement a real vertical slice from input through processing/persistence to visible output. Use supplied data or clearly labeled task-allowed fixtures.
3. Add remaining required behavior in priority order and recheck the runnable path after meaningful slices.
4. At feature cutoff, fix defects, verify launch instructions, and prepare deliverables. Defer optional polish before mandatory behavior.

**Output contract:** Runnable application, exact launch steps, requirement coverage, and clearly identified simulated or incomplete behavior.

**Tools:** Existing framework/package CLIs, local HTTP requests, project checks; add dependencies only when worth setup risk.

**Verification:** A user can complete the required journey; empty, invalid, and failure states behave sensibly.

**Failure handling:** When time shrinks, stabilize the working slice and remove optional breadth. Report every unmet requirement explicitly.

**Related skills:** [task-prioritization](../task-prioritization/SKILL.md), [time-budget-management](../time-budget-management/SKILL.md), [web-application-development](../web-application-development/SKILL.md), [completion-verification](../completion-verification/SKILL.md).
