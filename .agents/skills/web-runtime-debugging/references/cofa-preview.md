# Cofa / restricted preview quick checklist

Full procedure: `<CodexHarness>/docs/preview/cofa-runbook.md` (read it when the preview is blank or fails).

1. Start the server and note the real port from its log. `0.0.0.0` is a bind address, never the URL to open.
2. `ss -ltnp | grep :PORT` (or the `bind_addresses` field of `web-probe`) shows who listens and on which address.
3. `web-probe http://127.0.0.1:PORT/ --path /api/... [--host-header <preview host>]` for server/asset/proxy faults.
4. `python3 -m harness preview-baseline --port PORT` serves a known-good page: baseline visible but app blank = app fault; both blank = preview connection.
5. Anything about Cofa-specific URLs or settings that is not in the runbook's "verified" list is unverified: ask the user to read the preview's own port field and report the browser Console/Network.
