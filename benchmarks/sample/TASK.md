Synthetic benchmark, not an exam answer. Python stdlib only. Work only here.
No network, external uploads, git push, browser/GUI automation, credentials or CLI updates.
Task A (web/server.py): implement create_server(host='127.0.0.1', port=0) returning
a stdlib HTTP server. GET / serves semantic HTML with a labeled title input,
add button, status filter and JS fetching the task API (no external assets).
GET /api/tasks returns JSON list; POST /api/tasks JSON {title} creates {id,title,status:'todo'},
returns 201. Blank title returns JSON 400. PATCH /api/tasks/ID JSON {status:'done'}
updates status, returns 200; nonexistent ID ->404; invalid status ->400.
Task B (analysis/report.py): summarize(text) accepts CSV id,region,amount. Trim values;
skip rows with empty required fields, duplicates by id (first VALID wins), malformed,
negative or nonfinite amount; return dict region -> amount string exactly two decimals.
Use Decimal and reject more than two fractional digits, output sorted by region.
Task C (repair/tickets.py): fix summarize(tickets) to return counts by status,
with no state retained across calls and unknown statuses counted as 'unknown'.
Supported statuses are 'open','closed'; do not mutate input.
