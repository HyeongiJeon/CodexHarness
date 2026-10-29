---
name: independent-code-review
description: "Review a change for concrete correctness and regression risks using fresh inspection; use before accepting substantial work or when review is requested."
---
# Independent Code Review

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Diff, requirement contract, original behavior, relevant checks.

## Procedure

1. Read requirements and relevant original code before relying on the implementer’s summary. Without authorized agents, perform a fresh separate pass and state that limitation.
2. Trace changed inputs, outputs, edge cases, failures, state transitions, and callers. Prioritize reachable defects over style preferences.
3. Validate suspected defects with a reproduction, failing check, or precise causal explanation; separate confirmed findings from untested concerns.
4. Report findings by impact with file/line references. After fixes, inspect the actual diff and recheck affected behavior.

**Output contract:** Actionable evidence-backed findings, checks performed, coverage limits, or an explicit no-actionable-findings result.

**Tools:** git diff, rg, source reads, project checks, local reproductions; another agent only with explicit authorization.

**Verification:** Each finding names a reachable condition and consequence; review covers requirements and integration.

**Failure handling:** When execution is unavailable, limit claims to inspection evidence. No findings does not prove correctness.

**Related skills:** [systematic-debugging](../systematic-debugging/SKILL.md), [completion-verification](../completion-verification/SKILL.md), [final-delivery-verification](../final-delivery-verification/SKILL.md).
