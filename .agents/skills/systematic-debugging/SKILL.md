---
name: systematic-debugging
description: "Find and fix defects through reproduction and narrow experiments; use for failing tests, runtime errors, incorrect output, or regressions."
---
# Systematic Debugging

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Expected/actual behavior, reproduction input, environment, logs, recent changes.

When the cause is unclear or a first fix fails, read [references/experiments.md](references/experiments.md).

## Procedure

1. Reproduce with the smallest representative input; record exact command, symptom, and expected output.
2. Trace the failing boundary with logs, values, and call sites. Test one falsifiable hypothesis and causal factor at a time.
3. Fix the earliest incorrect assumption or state transition; update related callers only as the contract requires.
4. Rerun the original reproduction and affected checks. Add a regression test when it guards real behavior without mirroring implementation.

**Output contract:** Root cause, focused fix, before/after evidence, and affected validation results.

**Tools:** Project tests, debugger or trace logs, rg, git diff, local HTTP/database inspection.

**Verification:** The original failure is resolved for the stated reason; neighboring behavior is checked; temporary diagnostics are removed.

**Failure handling:** After two uninformative experiments, shrink the reproduction or revisit assumptions. Preserve evidence and name concrete blockers.

**Related skills:** [decision-and-evidence-recording](../decision-and-evidence-recording/SKILL.md), [independent-code-review](../independent-code-review/SKILL.md), [completion-verification](../completion-verification/SKILL.md).
