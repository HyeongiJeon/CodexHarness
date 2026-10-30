"""Local HTTP diagnosis of a running web app. No browser, no external hosts."""
from __future__ import annotations

from html.parser import HTMLParser
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
SCRIPT_TYPES = ("javascript", "ecmascript")


class _Refs(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[tuple[str, str]] = []
        self.root_ids: list[str] = []
        self.inline_scripts = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = dict(attrs)
        if tag == "script":
            if a.get("src"):
                self.refs.append(("script", a["src"]))
            else:
                self.inline_scripts += 1
        elif tag == "link" and a.get("href") and set((a.get("rel") or "").lower().split()) & {"stylesheet", "modulepreload"}:
            self.refs.append(("link", a["href"]))
        elif tag == "div" and a.get("id") in ("root", "app", "__next"):
            self.root_ids.append(a["id"])


class _LocalRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).hostname not in LOCAL_HOSTS:
            raise URLError(f"redirect to non-local host refused: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = build_opener(_LocalRedirects)


def fetch(url: str, timeout: float = 5.0, limit: int = 2_000_000) -> dict:
    """GET without following redirects' semantics; report status, type and a body prefix."""
    try:
        with _OPENER.open(Request(url, headers={"Accept": "*/*"}), timeout=timeout) as r:
            body = r.read(limit)
            return {"url": url, "final_url": r.geturl(), "status": r.status,
                    "content_type": r.headers.get("Content-Type", ""), "bytes": len(body), "body": body}
    except HTTPError as exc:
        return {"url": url, "status": exc.code, "content_type": exc.headers.get("Content-Type", ""), "bytes": 0, "body": b""}
    except (URLError, OSError, ValueError) as exc:
        return {"url": url, "status": None, "error": str(getattr(exc, "reason", exc)), "bytes": 0, "body": b""}


def listening(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def probe(url: str, extra_paths: list[str] | None = None) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("url must be http(s)://host:port/...")
    if parsed.hostname not in LOCAL_HOSTS:
        raise ValueError("web-probe only checks localhost/127.0.0.1; do not probe external hosts")
    host = "127.0.0.1" if parsed.hostname == "0.0.0.0" else parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    url = url.replace("//0.0.0.0", "//127.0.0.1", 1)
    findings: list[dict] = []

    def flag(severity: str, layer: str, message: str) -> None:
        findings.append({"severity": severity, "layer": layer, "message": message})

    report: dict = {"url": url, "port_listening": listening(host, port), "resources": [], "extra": [], "findings": findings}
    if parsed.hostname == "0.0.0.0":
        report["note"] = "0.0.0.0 is a bind address, not a browse URL; probed 127.0.0.1 instead"
    if not report["port_listening"]:
        flag("error", "server", f"nothing accepts TCP connections on {host}:{port}: process not running, crashed, or other port")
        report["verdict"] = "server_down"
        return report
    page = fetch(url)
    if page.get("final_url") and page["final_url"] != url:
        flag("warn", "server", f"redirected to {page['final_url']}; confirm this is the app and not a login page")
    report["page"] = {k: page.get(k) for k in ("status", "content_type", "bytes", "error")}
    if page["status"] != 200:
        flag("error", "server", f"GET {url} -> {page['status']} {page.get('error', '')}".strip())
        report["verdict"] = "server_error_response"
        return report
    text = page["body"].decode("utf-8", "replace")
    if not page["bytes"]:
        flag("error", "server", "200 with empty body")
    if "html" not in page["content_type"].lower() and text.lstrip()[:1] != "<":
        flag("warn", "server", f"page is {page['content_type']!r}, not HTML (API root? wrong route?)")
    refs = _Refs()
    refs.feed(text)
    if not refs.refs and not refs.inline_scripts and refs.root_ids:
        flag("error", "frontend", "HTML has an empty app root and no script: bundle not referenced (build missing or wrong template)")
    for kind, ref in refs.refs:
        target = urljoin(url, ref)
        origin = urlparse(target)
        if origin.scheme not in ("http", "https"):
            continue
        item = {"ref": ref, "kind": kind}
        if origin.hostname not in LOCAL_HOSTS:
            item["skipped"] = "external host not fetched"
            flag("warn", "frontend", f"{ref} loads from external host; may be blocked in an isolated preview")
            report["resources"].append(item)
            continue
        if (origin.hostname, origin.port or port) != (parsed.hostname, port):
            flag("warn", "preview", f"{ref} points at a different local origin; a preview forwarding one port cannot reach it. Use relative URLs/proxy")
        got = fetch(target)
        item.update(status=got["status"], content_type=got.get("content_type"), bytes=got["bytes"])
        ctype = (got.get("content_type") or "").lower()
        if got["status"] != 200:
            flag("error", "frontend", f"{ref} -> {got['status']}: asset path/base wrong (Vite `base`, build output dir, static mount)")
        elif kind == "script" and "html" in ctype:
            flag("error", "frontend", f"{ref} returned HTML instead of JavaScript: SPA fallback or missing asset swallowed the request")
        elif kind == "script" and not any(t in ctype for t in SCRIPT_TYPES):
            flag("warn", "frontend", f"{ref} content-type {ctype!r}; module scripts need a JavaScript MIME type")
        report["resources"].append(item)
        if ref.endswith("/@vite/client") or "/src/main." in ref:
            report["dev_server_hint"] = "Vite dev server detected; blocked host/HMR websocket issues appear only in the browser console"
    for path in extra_paths or []:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError(f"--path must be an absolute path like /api/items, got {path!r}")
        got = fetch(urljoin(url, path))
        entry = {"path": path, "status": got["status"], "content_type": got.get("content_type"), "bytes": got["bytes"]}
        if got["status"] == 200 and "html" in (got.get("content_type") or "").lower():
            flag("error", "proxy", f"{path} returned HTML: an endpoint you listed is hitting the SPA fallback, not the backend (proxy/route); ignore only if it is meant to be a page")
        elif got["status"] != 200:
            flag("error", "proxy", f"{path} -> {got['status']} {got.get('error', '')}".strip())
        report["extra"].append(entry)
    errors = [f for f in findings if f["severity"] == "error"]
    if not errors:
        report["verdict"] = "server_and_assets_ok"
        report["limitation"] = "HTTP only: JavaScript runtime errors, rendering and the preview connection still need the browser console / manual preview"
    else:
        layers = {f["layer"] for f in errors}
        report["verdict"] = "frontend_assets_broken" if "frontend" in layers else "backend_or_proxy_broken" if "proxy" in layers else "server_error_response"
    return report


def main(url: str, paths: list[str]) -> tuple[str, int]:
    report = probe(url, paths)
    return json.dumps(report, indent=2, ensure_ascii=False), 0 if report["verdict"] == "server_and_assets_ok" else 1
