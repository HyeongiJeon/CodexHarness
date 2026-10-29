---
name: decision-and-evidence-recording
description: "Keep compact records of consequential choices, experiments, and validation; use when assumptions or completion claims need auditability."
---
# Decision And Evidence Recording

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Requirements, changed files, decisions, command results, artifact locations.

## Procedure

1. Record decisions changing scope, architecture, assumptions, or acceptance: reason, material alternatives, and affected requirement.
2. For checks keep exact command/method, relevant environment, observed result, and applicability to final code.
3. Use the task’s existing evidence location or one concise local file; link large artifacts rather than copying them.
4. Refresh evidence after relevant edits and use it for factual handoff. Redact credentials and unnecessary personal data.

**Output contract:** Compact log linking requirement, decision/check, observed result, and artifact; inference is labeled.

**Tools:** Local Markdown/structured records, git status/diff, command outputs, artifact paths; no external publication.

**Verification:** Claims trace to current evidence, assumptions are labeled, and records contain no secret values.

**Failure handling:** Rerun affordable checks if evidence was lost or mark unverified. Never reconstruct successful results from memory.

**Related skills:** [systematic-debugging](../systematic-debugging/SKILL.md), [completion-verification](../completion-verification/SKILL.md), [final-delivery-verification](../final-delivery-verification/SKILL.md).
