# Symptom to layer

| Evidence | Layer | Likely cause and fix |
| --- | --- | --- |
| Port not listening / connection refused | server | Process exited (read log), different port, bound to a unix socket; start in foreground and read the first error |
| Listens only on 127.0.0.1 and preview cannot connect | preview | Rebind to `0.0.0.0` (`--host 0.0.0.0`, `app.run(host="0.0.0.0")`, `listen(PORT, "0.0.0.0")`); still browse via the preview's port field |
| `/` 404 or 500 | server | Route/static dir wrong, template missing, exception in log |
| `/` 200, empty `<div id="root">`, no script tag | frontend | Template without bundle; run the build or use the dev server's index.html |
| Asset 404 | frontend | Vite `base`/`homepage` mismatch, build output not served, static mount path |
| Script returns HTML | frontend/proxy | SPA fallback answering missing assets; fix paths, restrict fallback to routes without a file extension |
| `/api/...` returns HTML | proxy | Missing `server.proxy`/route prefix; backend not running on the proxied port |
| Hard-coded `localhost:3000` in code or HTML | preview | Browser resolves it on the user's machine, not the app host; use relative URLs |
| Vite "Blocked request. Host not allowed" | frontend | Add the host to `server.allowedHosts` or use the supplied preview host setting |
| Deep link 404 but `/` works | SPA routing | Server lacks history fallback to `index.html` |
| Probe clean, preview blank | preview/runtime | Needs the browser console (below) |

## Ask the user to read from the browser

1. The exact address typed and the port used.
2. Console: first red error message with file:line (syntax, `Uncaught`, `Failed to fetch`, CORS, mixed content).
3. Network tab: any request that is red, status 0, 404, or has `text/html` type for a `.js` file.
4. Whether a plain `/` static route or `/api/health`-style JSON path loads in a new tab.
5. Whether the page differs after a hard reload.

Record these as user-observed facts, not automated results.
