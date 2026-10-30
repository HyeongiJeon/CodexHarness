# Flow matrix

| Step | Automatic (local HTTP / tests) | User-verify in preview |
| --- | --- | --- |
| Server + assets | `web-probe` verdict, build exit code | Page renders, no console errors |
| Input | Valid and invalid payloads to the API (400/422 with message) | Form shows inline errors, keeps values |
| Request | Status, JSON shape, content type | Network row is not red |
| Processing | Computed fields, totals, filters equal an independently computed value | Displayed numbers match |
| Save | GET after POST returns the record; duplicate/limits behave | New item appears without manual reload |
| Persistence | Restart server and GET again (or inspect file/DB) | Refresh keeps the item |
| Errors | Stop dependency or send bad data, check error JSON | Visible, actionable message; no blank screen |
| Empty/loading | Empty dataset response | Empty state text; loading indicator |
| Final run | Fresh start with the documented command; tests; build | Open the documented URL once |

Evidence goes in `templates/evidence.md` rows: command, exit code, expected vs actual; user-verify rows stay `unconfirmed` until the user reports what they saw.
