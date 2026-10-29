---
name: completion-verification
description: "Verify implemented behavior against acceptance criteria before declaring completion; use after code changes or substantial fixes."
---
# Completion Verification

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Acceptance criteria, final saved code, run commands, relevant fixtures, deadline.

When several requirements or environments need distinct evidence, read [references/evidence-matrix.md](references/evidence-matrix.md).

## Procedure

1. Map requirements to the strongest affordable checks: focused tests, real CLI/API calls, rendered artifacts, or full user journeys.
2. Run checks against final saved code. Cover the main success path and meaningful invalid, empty, and failure cases.
3. Inspect actual outputs, persisted effects, file contents, HTTP behavior, or rendering rather than exit codes alone.
4. Classify requirements passed, failed, or unverified. Fix required failures and rerun affected checks before claiming completion.

**Output contract:** Requirement-to-evidence matrix with exact commands/methods, outcomes, revision context, and unresolved limits.

**Tools:** Project tests/build, shell/API requests, manual local preview, artifact viewers; no browser, GUI, or computer-use automation.

**Verification:** Every completion claim has current evidence; failed and skipped checks remain visible.

**Failure handling:** If a check cannot run, record the blocker and use a narrower check without calling the requirement passed.

**Related skills:** [systematic-debugging](../systematic-debugging/SKILL.md), [independent-code-review](../independent-code-review/SKILL.md), [final-delivery-verification](../final-delivery-verification/SKILL.md).
