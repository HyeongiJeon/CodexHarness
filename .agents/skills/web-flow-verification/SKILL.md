---
name: web-flow-verification
description: "Verify a web feature as a real user flow (input, API, save, screen update, reload, errors, final run); use before claiming a web task complete."
---
# Web Flow Verification

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Acceptance criteria, user journey, launch command, API contract, persistence layer.

Read [references/flow-matrix.md](references/flow-matrix.md) for the step matrix and the automatic vs user-performed split.

## Procedure

1. Write the journey as steps: screen input, request, processing, storage, response, screen update, reload.
2. Start the app with the real command, then run `python3 -m harness web-probe http://127.0.0.1:PORT/ --path /api/...` to confirm server and assets before the flow.
3. Automatic checks over local HTTP: create/update through the API with valid and invalid payloads, read it back, restart the server if persistence is claimed, and confirm the stored state matches.
4. Mark each remaining step (typing in the form, seeing the list update, refresh, empty and error screens, narrow width) as **user-verify** with exact instructions and expected result.
5. Run the project's tests and production build, then the final launch from a clean start exactly as a grader would.

**Output contract:** Table of step, method (automatic or user-verify), command or instruction, expected, actual, status (passed / failed / unconfirmed).

**Tools:** Local HTTP (`urllib`, `curl`), `web-probe`, project tests/build, user-operated preview; no browser, GUI, or computer-use automation.

**Verification:** A 200 status proves only that a request succeeded. Claim the flow works only when stored data, the response body, and (via the user) the screen agree and survive reload.

**Failure handling:** Failed or unconfirmed steps stay listed as such in the handoff; do not convert an HTTP pass into a UI pass.

**Related skills:** [completion-verification](../completion-verification/SKILL.md), [web-runtime-debugging](../web-runtime-debugging/SKILL.md), [final-delivery-verification](../final-delivery-verification/SKILL.md), [decision-and-evidence-recording](../decision-and-evidence-recording/SKILL.md).
