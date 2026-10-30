from __future__ import annotations

import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from harness.web_probe import probe

INDEX = b'<html><body><div id="root"></div><script type="module" src="/assets/app.js"></script></body></html>'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def do_GET(self) -> None:
        routes = {
            "/": (200, "text/html", INDEX),
            "/assets/app.js": (200, "text/html", INDEX) if self.server.broken else (200, "text/javascript", b"console.log(1)"),
            "/api/items": (200, "text/html", INDEX) if self.server.broken else (200, "application/json", b"[]"),
        }
        status, ctype, body = routes.get(self.path, (404, "text/plain", b"no"))
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)


class WebProbeTests(unittest.TestCase):
    def serve(self, broken: bool) -> str:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.broken = broken
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(2), server.server_close()))
        return f"http://127.0.0.1:{server.server_address[1]}/"

    def test_healthy_app_passes_with_http_only_limitation(self) -> None:
        report = probe(self.serve(False), ["/api/items"])
        self.assertEqual(report["verdict"], "server_and_assets_ok")
        self.assertIn("console", report["limitation"])

    def test_spa_fallback_for_script_and_api_is_detected(self) -> None:
        report = probe(self.serve(True), ["/api/items"])
        self.assertEqual(report["verdict"], "frontend_assets_broken")
        messages = " ".join(f["message"] for f in report["findings"])
        self.assertIn("instead of JavaScript", messages)
        self.assertIn("SPA fallback", messages)

    def test_closed_port_is_server_down(self) -> None:
        url = self.serve(False)
        server_port = int(url.rsplit(":", 1)[1].rstrip("/"))
        # a port that was just freed by a throwaway socket
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            free = s.getsockname()[1]
        self.assertNotEqual(free, server_port)
        self.assertEqual(probe(f"http://127.0.0.1:{free}/")["verdict"], "server_down")

    def test_external_hosts_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            probe("http://example.com/")

    def test_zero_address_is_probed_as_loopback(self) -> None:
        url = self.serve(False).replace("127.0.0.1", "0.0.0.0")
        report = probe(url)
        self.assertEqual(report["verdict"], "server_and_assets_ok")
        self.assertIn("bind address", report["note"])


if __name__ == "__main__":
    unittest.main()


class WebProbeGuardTests(unittest.TestCase):
    def test_absolute_extra_path_is_rejected(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.broken = False
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(2), server.server_close()))
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        with self.assertRaises(ValueError):
            probe(url, ["http://example.invalid/z"])
        with self.assertRaises(ValueError):
            probe(url, ["//example.invalid/z"])

    def test_non_api_path_returning_html_is_flagged_and_favicon_is_ignored(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.broken = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(2), server.server_close()))
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        report = probe(url, ["/api/items"])
        self.assertTrue(any(f["layer"] == "proxy" for f in report["findings"]))
        self.assertFalse(any("favicon" in f["message"] for f in report["findings"]))
