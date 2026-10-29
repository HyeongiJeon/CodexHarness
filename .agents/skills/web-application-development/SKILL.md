---
name: web-application-development
description: "Implement web features across UI, state, routing, and services; use for functional browser-based workflows."
---
# Web Application Development

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Required user journey, repository, API/data contracts, persistence and runtime constraints.

For forms, persisted state, async requests, or multi-page flows, read [references/application-boundaries.md](references/application-boundaries.md).

## Procedure

1. Discover framework, commands, route/component patterns, and data layer; extend the original application.
2. Connect one complete user journey with explicit validation, loading/failure states, and clear state ownership.
3. Keep secrets server-side, validate untrusted data at boundaries, and use existing authentication/persistence where required.
4. Exercise navigation, submission, reload/persistence, and relevant failures in the running application; run the existing production build.

**Output contract:** Working changes, exact launch commands, configuration names without secret values, and journey evidence.

**Tools:** Project framework/build tools, local HTTP, existing storage clients, and user-operated local preview; no browser, GUI, or computer-use automation.

**Verification:** UI reflects real service results; refresh/navigation work; errors are visible; credentials are not exposed.

**Failure handling:** When a service is unavailable, show failure or use a labeled task-allowed fixture. Never present a disconnected control as functional.

**Related skills:** [frontend-design](../frontend-design/SKILL.md), [api-backend-development](../api-backend-development/SKILL.md), [rapid-mvp-development](../rapid-mvp-development/SKILL.md), [completion-verification](../completion-verification/SKILL.md).
