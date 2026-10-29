---
name: architecture-planning
description: "Plan component boundaries, interfaces, and implementation order; use when a change spans several files or independent work."
---
# Architecture Planning

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Acceptance criteria, existing architecture/dependencies, runtime constraints, deadline.

## Procedure

1. Identify extension points, data ownership, execution paths, and actual build/test commands; prefer the existing stack.
2. Choose the smallest design meeting the task. Compare alternatives only where they affect delivery or correctness.
3. Define interface names, data shapes, failure semantics, persistence, and shared-file ownership before splitting work.
4. Order a runnable vertical slice first, required features next, and verification last. Give risky dependencies an early feasibility check and fallback.

**Output contract:** A short component/file plan, interface contracts, dependency order, risk checks, and first runnable slice.

**Tools:** Repository reads, dependency/runtime discovery, and diagrams only for meaningful boundaries.

**Verification:** All acceptance criteria have an implementation path; existing launch and data contracts are preserved.

**Failure handling:** If a dependency is unavailable, select a compatible local fallback and state behavioral limits; replan before building a replacement.

**Related skills:** [requirement-discovery](../requirement-discovery/SKILL.md), [parallel-implementation](../parallel-implementation/SKILL.md), [rapid-mvp-development](../rapid-mvp-development/SKILL.md).
