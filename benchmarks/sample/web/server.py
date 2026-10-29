"""Small, dependency-free task application with server-local in-memory storage."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit


PAGE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tasks</title>
<style>
body { font: 1rem/1.5 system-ui, sans-serif; margin: 0; color: #172033; background: #f4f6fa; }
main { max-width: 42rem; margin: 3rem auto; padding: 1.5rem; background: white; border-radius: .75rem; }
h1 { margin-top: 0; } form { display: flex; flex-wrap: wrap; gap: .6rem; margin-bottom: 1.5rem; }
form label { flex-basis: 100%; } input { flex: 1; min-width: 8rem; }
input, button, select { font: inherit; padding: .6rem; border: 1px solid #64748b; border-radius: .3rem; }
button { cursor: pointer; background: #184fc4; color: white; } button:disabled { opacity: .6; cursor: wait; }
:focus-visible { outline: 3px solid #e59a13; outline-offset: 3px; }
ul { padding: 0; list-style: none; } li { display: flex; align-items: center; gap: 1rem; padding: 1rem 0; border-bottom: 1px solid #ddd; }
li span { flex: 1; overflow-wrap: anywhere; } .done { text-decoration: line-through; color: #596579; }
#error { color: #a51a23; } #message { color: #596579; }
@media (max-width: 46rem) { main { margin: 0; border-radius: 0; } }
</style>
</head>
<body>
<main>
<h1>Tasks</h1>
<form id="task-form">
<label for="title">Task title</label>
<input id="title" name="title" required autocomplete="off" aria-describedby="error">
<button id="add" type="submit">Add task</button>
</form>
<label for="filter">Status</label>
<select id="filter"><option value="all">All tasks</option><option value="todo">To do</option><option value="done">Done</option></select>
<p id="error" role="alert"></p>
<p id="message" role="status" aria-live="polite">Loading tasks…</p>
<ul id="tasks" aria-label="Tasks" aria-busy="true"></ul>
</main>
<script>
const form = document.querySelector('#task-form');
const title = document.querySelector('#title');
const add = document.querySelector('#add');
const filter = document.querySelector('#filter');
const list = document.querySelector('#tasks');
const message = document.querySelector('#message');
const error = document.querySelector('#error');
let tasks = [];
let loaded = false;
async function request(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The request failed. Please try again.');
  return data;
}
function render() {
  list.replaceChildren();
  const shown = tasks.filter(task => filter.value === 'all' || task.status === filter.value);
  message.textContent = shown.length ? `${shown.length} task${shown.length === 1 ? '' : 's'}` :
    (loaded ? (tasks.length ? 'No tasks match this status.' : 'No tasks yet. Add your first task above.') : 'Tasks could not be loaded. Reload the page to try again.');
  for (const task of shown) {
    const row = document.createElement('li');
    const text = document.createElement('span');
    text.textContent = task.title;
    row.append(text);
    if (task.status === 'done') {
      text.className = 'done';
      const status = document.createElement('small');
      status.textContent = 'Done';
      row.append(status);
    } else {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = 'Mark done';
      button.setAttribute('aria-label', `Mark ${task.title} done`);
      button.addEventListener('click', async () => {
        button.disabled = true;
        button.textContent = 'Saving…';
        error.textContent = '';
        try {
          const updated = await request(`/api/tasks/${task.id}`, {
            method: 'PATCH', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status: 'done'})
          });
          tasks = tasks.map(item => item.id === updated.id ? updated : item);
          render();
          filter.focus();
        } catch (err) {
          error.textContent = err.message;
          button.disabled = false;
          button.textContent = 'Mark done';
        }
      });
      row.append(button);
    }
    list.append(row);
  }
}
filter.addEventListener('change', render);
form.addEventListener('submit', async event => {
  event.preventDefault();
  error.textContent = '';
  const value = title.value.trim();
  if (!value) { error.textContent = 'Enter a task title.'; title.focus(); return; }
  add.disabled = true;
  add.textContent = 'Adding…';
  try {
    const task = await request('/api/tasks', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({title: value})
    });
    tasks.push(task);
    loaded = true;
    title.value = '';
    filter.value = 'all';
    render();
    title.focus();
  } catch (err) { error.textContent = err.message; }
  finally { add.disabled = false; add.textContent = 'Add task'; }
});
(async () => {
  add.disabled = true;
  try { tasks = await request('/api/tasks'); loaded = true; }
  catch (err) { error.textContent = err.message; }
  finally { list.setAttribute('aria-busy', 'false'); add.disabled = false; render(); }
})();
</script>
</body>
</html>'''


def create_server(host='127.0.0.1', port=0):
    """Return an unstarted HTTPServer; callers own serve_forever/server_close."""
    tasks = {}
    next_id = 1

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, data, content_type='application/json; charset=utf-8'):
            body = (json.dumps(data, ensure_ascii=False) if content_type.startswith('application/json') else data).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def read_json(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length <= 0 or length > 65536:
                    raise ValueError
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict):
                    raise ValueError
                return value
            except (ValueError, UnicodeError):
                self.reply(400, {'error': 'Provide a valid JSON object (up to 64 KiB).'})
                return None

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/':
                self.reply(200, PAGE, 'text/html; charset=utf-8')
            elif path == '/api/tasks':
                self.reply(200, list(tasks.values()))
            else:
                self.reply(404, {'error': 'Not found.'})

        def do_POST(self):
            nonlocal next_id
            if urlsplit(self.path).path != '/api/tasks':
                self.reply(404, {'error': 'Not found.'})
                return
            value = self.read_json()
            if value is None:
                return
            title = value.get('title')
            if not isinstance(title, str) or not title.strip():
                self.reply(400, {'error': 'Enter a nonblank task title.'})
                return
            task = {'id': next_id, 'title': title.strip(), 'status': 'todo'}
            tasks[next_id] = task
            next_id += 1
            self.reply(201, task)

        def do_PATCH(self):
            path = urlsplit(self.path).path
            parts = path.split('/')
            if len(parts) != 4 or parts[1:3] != ['api', 'tasks'] or not parts[3].isascii() or not parts[3].isdigit():
                self.reply(404, {'error': 'Task not found.'})
                return
            task_id = int(parts[3])
            if task_id not in tasks:
                self.reply(404, {'error': 'Task not found.'})
                return
            value = self.read_json()
            if value is None:
                return
            if value.get('status') not in ('todo', 'done'):
                self.reply(400, {'error': 'Status must be todo or done.'})
                return
            tasks[task_id]['status'] = value['status']
            self.reply(200, tasks[task_id])

    return HTTPServer((host, port), Handler)
