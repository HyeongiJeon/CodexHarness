"""Local-only synthetic task board, served with Python's standard library."""

from __future__ import annotations

import json
import re
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import RLock
from urllib.parse import parse_qs, urlparse


STATUSES = ("todo", "in_progress", "done")
_ID_RE = re.compile(r"^/api/tasks/(\d+)$")

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Synthetic Task Board</title>
  <style>
    :root { color-scheme: light; font: 16px/1.5 system-ui, sans-serif; color: #17212b; background: #f3f6f8; }
    * { box-sizing: border-box; }
    body { margin: 0; }
    header { padding: 1.4rem max(1rem, calc((100% - 68rem) / 2)); background: #17324d; color: white; }
    main { max-width: 70rem; margin: 1.5rem auto; padding: 0 1rem 3rem; }
    h1 { margin: 0; font-size: 1.4rem; }
    h2 { font-size: 1.1rem; margin-top: 0; }
    .layout { display: grid; grid-template-columns: minmax(17rem, 1fr) minmax(0, 1.5fr); gap: 1rem; align-items: start; }
    section { background: white; border: 1px solid #dbe2e8; border-radius: .6rem; padding: 1rem; }
    label { display: block; font-weight: 650; margin: .7rem 0 .2rem; }
    input, select, textarea, button { width: 100%; font: inherit; padding: .55rem; border: 1px solid #9cabb8; border-radius: .35rem; }
    textarea { min-height: 5rem; resize: vertical; }
    button { margin-top: .9rem; border: 0; color: white; background: #165d92; font-weight: 700; cursor: pointer; }
    button:hover { background: #104a75; }
    .toolbar { display: flex; align-items: center; gap: .75rem; margin: 0 0 .8rem; }
    .toolbar label { margin: 0; }
    .toolbar select { width: auto; min-width: 10rem; }
    #notice { min-height: 1.5rem; color: #8a2c20; }
    #tasks { list-style: none; padding: 0; margin: 0; }
    .task { border-top: 1px solid #e3e9ee; padding: .8rem 0; }
    .task h3 { margin: 0; font-size: 1rem; }
    .task p { margin: .2rem 0; color: #475867; white-space: pre-wrap; overflow-wrap: anywhere; }
    .task-meta { font-size: .88rem; color: #475867; }
    .task select { width: auto; min-width: 9rem; margin-top: .4rem; }
    @media (max-width: 700px) { .layout { grid-template-columns: 1fr; } header { padding: 1rem; } main { margin-top: 1rem; } }
  </style>
</head>
<body>
  <header><h1>Synthetic Task Board</h1></header>
  <main>
    <p>Practice board for local development tasks. Changes live in this process and disappear when the server stops.</p>
    <p id="notice" role="status" aria-live="polite"></p>
    <div class="layout">
      <section aria-labelledby="new-task-heading">
        <h2 id="new-task-heading">Add a task</h2>
        <form id="task-form">
          <label for="title">Title</label><input id="title" name="title" required maxlength="120">
          <label for="owner">Owner</label><input id="owner" name="owner" maxlength="80">
          <label for="due-date">Due date</label><input id="due-date" name="due_date" type="date">
          <label for="description">Description</label><textarea id="description" name="description" maxlength="500"></textarea>
          <button type="submit">Add task</button>
        </form>
      </section>
      <section aria-labelledby="task-list-heading">
        <h2 id="task-list-heading">Tasks</h2>
        <div class="toolbar"><label for="status-filter">Filter status</label>
          <select id="status-filter"><option value="all">All</option><option value="todo">To do</option><option value="in_progress">In progress</option><option value="done">Done</option></select>
        </div>
        <ul id="tasks" aria-live="polite"></ul>
      </section>
    </div>
  </main>
  <script>
    const list = document.querySelector('#tasks');
    const notice = document.querySelector('#notice');
    const filter = document.querySelector('#status-filter');
    const statusLabel = {todo: 'To do', in_progress: 'In progress', done: 'Done'};

    async function api(path, options) {
      const response = await fetch(path, options);
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Request failed');
      return result;
    }
    function render(tasks) {
      list.replaceChildren();
      for (const task of tasks) {
        const item = document.createElement('li');
        item.className = 'task';
        const title = document.createElement('h3'); title.textContent = task.title;
        const description = document.createElement('p'); description.textContent = task.description || 'No description';
        const meta = document.createElement('p'); meta.className = 'task-meta';
        meta.textContent = `Owner: ${task.owner || 'Unassigned'} · Due: ${task.due_date || 'None'} · ID: ${task.id}`;
        const status = document.createElement('select'); status.setAttribute('aria-label', `Status for ${task.title}`);
        for (const value of ['todo', 'in_progress', 'done']) {
          const option = document.createElement('option'); option.value = value; option.textContent = statusLabel[value]; status.append(option);
        }
        status.value = task.status;
        status.addEventListener('change', async () => {
          try { await api(`/api/tasks/${task.id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({status: status.value})}); notice.textContent = 'Task updated.'; await load(); }
          catch (error) { notice.textContent = error.message; await load(); }
        });
        item.append(title, description, meta, status); list.append(item);
      }
      if (!tasks.length) { const empty = document.createElement('li'); empty.textContent = 'No tasks match this filter.'; list.append(empty); }
    }
    async function load() {
      const query = filter.value === 'all' ? '' : `?status=${encodeURIComponent(filter.value)}`;
      render(await api(`/api/tasks${query}`));
    }
    document.querySelector('#task-form').addEventListener('submit', async event => {
      event.preventDefault(); notice.textContent = '';
      const fields = new FormData(event.currentTarget);
      const task = Object.fromEntries(fields.entries());
      try { await api('/api/tasks', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(task)}); event.currentTarget.reset(); notice.textContent = 'Task added.'; filter.value = 'all'; await load(); }
      catch (error) { notice.textContent = error.message; }
    });
    filter.addEventListener('change', () => load().catch(error => { notice.textContent = error.message; }));
    load().catch(error => { notice.textContent = error.message; });
  </script>
</body>
</html>
"""


class TaskBoard:
    """Process-local task storage with small validation rules."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._tasks = [
            {"id": 1, "title": "Review weekly inventory", "description": "Compare synthetic stock counts with the reorder list.", "owner": "Mina", "status": "todo", "due_date": "2026-11-02"},
            {"id": 2, "title": "Confirm delivery window", "description": "Send the warehouse team the agreed time slot.", "owner": "Joon", "status": "in_progress", "due_date": "2026-11-03"},
            {"id": 3, "title": "Archive closed requests", "description": "Move completed requests to the weekly archive.", "owner": "", "status": "done", "due_date": ""},
        ]
        self._next_id = 4

    def list(self, status: str | None = None) -> list[dict[str, object]]:
        if status and status not in STATUSES:
            raise ValueError("status must be todo, in_progress, or done")
        with self._lock:
            tasks = self._tasks if status is None else [task for task in self._tasks if task["status"] == status]
            return [task.copy() for task in tasks]

    def add(self, payload: object) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        title = self._text(payload, "title", required=True, limit=120)
        owner = self._text(payload, "owner", limit=80)
        description = self._text(payload, "description", limit=500)
        due_date = self._date(payload.get("due_date", ""))
        with self._lock:
            task = {"id": self._next_id, "title": title, "description": description, "owner": owner, "status": "todo", "due_date": due_date}
            self._next_id += 1
            self._tasks.append(task)
            return task.copy()

    def update(self, task_id: int, payload: object) -> dict[str, object] | None:
        if not isinstance(payload, dict) or not payload:
            raise ValueError("request body must be a non-empty JSON object")
        unknown = set(payload) - {"title", "owner", "description", "status", "due_date"}
        if unknown:
            raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
        updates: dict[str, object] = {}
        if "title" in payload:
            updates["title"] = self._text(payload, "title", required=True, limit=120)
        if "owner" in payload:
            updates["owner"] = self._text(payload, "owner", limit=80)
        if "description" in payload:
            updates["description"] = self._text(payload, "description", limit=500)
        if "due_date" in payload:
            updates["due_date"] = self._date(payload["due_date"])
        if "status" in payload:
            status = payload["status"]
            if status not in STATUSES:
                raise ValueError("status must be todo, in_progress, or done")
            updates["status"] = status
        with self._lock:
            task = next((item for item in self._tasks if item["id"] == task_id), None)
            if task is None:
                return None
            task.update(updates)
            return task.copy()

    @staticmethod
    def _text(payload: dict, key: str, *, required: bool = False, limit: int) -> str:
        value = payload.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"{key} must be text")
        value = value.strip()
        if required and not value:
            raise ValueError(f"{key} is required")
        if len(value) > limit:
            raise ValueError(f"{key} must be at most {limit} characters")
        return value

    @staticmethod
    def _date(value: object) -> str:
        if value in (None, ""):
            return ""
        if not isinstance(value, str):
            raise ValueError("due_date must be YYYY-MM-DD")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("due_date must be YYYY-MM-DD")
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("due_date must be YYYY-MM-DD") from exc


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Create a local task-board server; pass port=0 to choose an ephemeral port."""

    board = TaskBoard()

    class Handler(BaseHTTPRequestHandler):
        server_version = "SyntheticTaskBoard/1.0"

        def _json(self, status: int, body: object) -> None:
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def _body(self) -> object:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if length < 0 or length > 64 * 1024:
                raise ValueError("request body must be at most 64 KiB")
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("request body must be valid JSON") from exc

        def do_GET(self) -> None:  # noqa: N802 - stdlib HTTP handler API
            parsed = urlparse(self.path)
            if parsed.path == "/":
                body = INDEX_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            elif parsed.path == "/api/tasks":
                query = parse_qs(parsed.query)
                try:
                    if len(query.get("status", [])) > 1:
                        raise ValueError("provide only one status filter")
                    tasks = board.list(query.get("status", [None])[0])
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
                else:
                    self._json(200, tasks)
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/tasks":
                self._json(404, {"error": "not found"})
                return
            try:
                task = board.add(self._body())
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            else:
                self._json(201, task)

        def do_PATCH(self) -> None:  # noqa: N802
            match = _ID_RE.fullmatch(urlparse(self.path).path)
            if not match:
                self._json(404, {"error": "not found"})
                return
            try:
                task = board.update(int(match.group(1)), self._body())
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            if task is None:
                self._json(404, {"error": "task not found"})
            else:
                self._json(200, task)

        def log_message(self, fmt: str, *args: object) -> None:
            # Keep the demo quiet and avoid writing request content to logs.
            return

    return ThreadingHTTPServer((host, port), Handler)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run the demo until interrupted by the user."""

    server = create_server(host, port)
    try:
        print(f"Synthetic task board: http://{host}:{server.server_address[1]}/")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
