---
name: task-prioritization
description: "Order work by requirement coverage, risk, dependencies, and deadline; use when scope exceeds time or tasks compete."
---
# Task Prioritization

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Acceptance criteria, candidate tasks, dependencies, effort estimates, remaining time.

## Procedure

1. Separate mandatory outcomes, their prerequisites, optional improvements, and unrelated work; preserve explicit task priorities.
2. Prove uncertain prerequisites early, then complete the main journey in dependency order.
3. Select short tasks producing observable requirement coverage; include validation effort in estimates.
4. Reprioritize when evidence changes. Defer optional work explicitly and give mandatory work at risk a concrete fallback.

**Output contract:** Ordered executable queue with checks, rough effort/risk, dependencies, and justified deferrals.

**Tools:** Concise local task list, repository discovery, measured check timings, actual clock.

**Verification:** Every mandatory outcome remains represented; prerequisites precede dependents; work fits the reserve.

**Failure handling:** If mandatory work cannot fit, preserve the most complete runnable flow and report exact gaps. Do not relabel requirements optional.

**Related skills:** [requirement-discovery](../requirement-discovery/SKILL.md), [architecture-planning](../architecture-planning/SKILL.md), [time-budget-management](../time-budget-management/SKILL.md).
