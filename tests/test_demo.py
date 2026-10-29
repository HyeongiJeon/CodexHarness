from __future__ import annotations

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from harness.demo import create_server


class TaskBoardHTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = create_server("127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def request(self, path: str, method: str = "GET", payload: object | None = None) -> tuple[int, object, str]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(self.base + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            response = urlopen(request, timeout=2)
        except HTTPError as exc:
            response = exc
        with response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
            parsed = json.loads(body) if "application/json" in content_type else body.decode("utf-8")
            return response.status, parsed, content_type

    def test_dashboard_is_real_semantic_html_over_http(self) -> None:
        status, body, content_type = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn('<html lang="en">', body)
        self.assertIn('aria-labelledby="task-list-heading"', body)
        self.assertIn("@media (max-width: 700px)", body)

    def test_list_filter_create_and_update(self) -> None:
        status, tasks, _ = self.request("/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(len(tasks), 3)

        status, filtered, _ = self.request("/api/tasks?status=in_progress")
        self.assertEqual(status, 200)
        self.assertEqual([task["title"] for task in filtered], ["Confirm delivery window"])

        status, created, _ = self.request("/api/tasks", "POST", {
            "title": "  Count sealed boxes  ", "description": "Synthetic practice task", "owner": "Ari", "due_date": "2026-11-05"
        })
        self.assertEqual(status, 201)
        self.assertEqual((created["id"], created["title"], created["status"]), (4, "Count sealed boxes", "todo"))

        status, updated, _ = self.request(f"/api/tasks/{created['id']}", "PATCH", {"status": "done", "owner": "Sam"})
        self.assertEqual(status, 200)
        self.assertEqual((updated["status"], updated["owner"]), ("done", "Sam"))

        status, done, _ = self.request("/api/tasks?status=done")
        self.assertEqual(status, 200)
        self.assertIn(4, [task["id"] for task in done])

    def test_invalid_inputs_are_reported_as_client_errors(self) -> None:
        status, payload, _ = self.request("/api/tasks?status=blocked")
        self.assertEqual(status, 400)
        self.assertIn("status must be", payload["error"])

        status, payload, _ = self.request("/api/tasks", "POST", {"title": " ", "due_date": "20261031"})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "title is required")

        status, payload, _ = self.request("/api/tasks/999", "PATCH", {"status": "done"})
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "task not found")


if __name__ == "__main__":
    unittest.main()
