---
name: api-backend-development
description: "Build an HTTP API, service, or persistence boundary; use for endpoint contracts, validation, transactions, and backend behavior."
---
# Api Backend Development

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Routes/data contracts, framework, storage schema, access requirements, local runtime.

For validation, mutations, authentication, or upstream dependencies, read [references/service-checks.md](references/service-checks.md).

## Procedure

1. Inspect routing, schema/migrations, errors, and tests; define minimal request/response contracts before changing consumers.
2. Validate boundary inputs; use explicit status codes and stable error shapes. Enforce existing access controls server-side.
3. Implement mutations with appropriate transactions and parameterized queries; keep configuration separate and secrets out of output.
4. Invoke the local service with success, invalid, and relevant authorization/conflict cases; verify persisted effects.

**Output contract:** Service changes, compatible migrations where needed, request/response examples, run steps, endpoint evidence.

**Tools:** Existing framework, HTTP client, database client, migrations, project tests.

**Verification:** Responses and side effects match contracts; invalid input cannot partially mutate data; required access/restart behavior works.

**Failure handling:** Fail clearly with bounded timeouts when dependencies are absent. Never silently replace required persistence with volatile storage.

**Related skills:** [architecture-planning](../architecture-planning/SKILL.md), [web-application-development](../web-application-development/SKILL.md), [systematic-debugging](../systematic-debugging/SKILL.md), [completion-verification](../completion-verification/SKILL.md).
