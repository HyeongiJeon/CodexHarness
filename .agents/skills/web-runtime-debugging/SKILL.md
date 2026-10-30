---
name: web-runtime-debugging
description: "Diagnose a web app that runs but shows a blank page, errors, or fails in a preview; use to separate server, frontend, and preview-connection faults."
---
# Web Runtime Debugging

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Launch command, intended port, symptom (blank page, error text), framework (Vite/React, Flask, Express, static).

Read [references/layers.md](references/layers.md) for the symptom-to-cause table and the browser-console checklist.

## Procedure

1. Process: confirm the server process is alive and its log shows no crash; note the real port it printed.
2. Port and URL: `0.0.0.0` is a bind address, not a browse URL. Check the port listens, then run (from the CodexHarness directory, e.g. `cd <CodexHarness> && ...`) `python3 -m harness web-probe http://127.0.0.1:PORT/ --path /api/...` (add the app's real API paths). It reports port, page, referenced assets, MIME types, and API-returns-HTML fallback.
3. Classify with the evidence: **server fault** (port closed, non-200, crash), **frontend fault** (assets 404 or HTML-as-JS, wrong Vite `base`, unbuilt bundle, proxy/SPA fallback), or **preview-connection fault** (probe is clean but the preview is blank).
4. Fix only the layer the evidence names; rerun the probe. Dev servers: set `server.host`/`--host 0.0.0.0`, `allowedHosts` if the host is rejected, and relative API URLs or a `server.proxy` instead of hard-coded `localhost:OTHER`. Production: build first and serve `dist` with an SPA fallback that never answers `/api` or `/assets`.
5. If the probe is clean, ask the user to open the preview and report the **browser console** items in the reference (first red error, failed Network rows, the exact URL they entered). Do not guess a Cofa-specific feature or URL; only the supplied preview's documented port field is known.

**Output contract:** Verdict (server / frontend / preview-connection / unverified), the probe output, the fix, and what only the user's browser can confirm.

**Tools:** `web-probe`, `ss -ltnp` or `lsof -i`, `curl`/`urllib` against localhost, server logs, build output; no browser, GUI, or computer-use automation, no external hosts.

**Verification:** Probe verdict is `server_and_assets_ok` after the fix, and the user-operated preview result is recorded or marked unconfirmed.

**Failure handling:** A clean probe plus blank preview is not "fixed". If the preview failure cannot be reproduced, report the diagnosis and the console data needed instead of claiming resolution.

**Related skills:** [systematic-debugging](../systematic-debugging/SKILL.md), [web-flow-verification](../web-flow-verification/SKILL.md), [web-application-development](../web-application-development/SKILL.md).
