#!/usr/bin/env python3
"""Serve the cloned United Carriers site with pretty URLs and local API stubs."""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent

STUB_JSON = {
    "/.wf_graphql/csrf": {"csrfToken": "local-preview"},
    "/.wf_auth": {"ok": True},
}


class CloneHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        parsed = urlparse(self.path)
        if parsed.path in STUB_JSON:
            return self._json(200, STUB_JSON[parsed.path])
        self.send_error(501, "Unsupported method ('POST')")
        return None

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With")
        self.end_headers()

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        url_path = unquote(parsed.path)
        mapped = self._html_path(url_path)
        return super().translate_path(mapped)

    def _html_path(self, url_path: str) -> str:
        if url_path == "/":
            return "/index.html"
        if Path(url_path).suffix:
            return url_path
        candidate = url_path.rstrip("/") + "/index.html"
        if (ROOT / candidate.lstrip("/")).is_file():
            return candidate
        if (ROOT / "404" / "index.html").is_file():
            return "/404/index.html"
        return url_path

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4174)
    args = parser.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), CloneHandler)
    print(f"United Carriers clone: http://{args.host}:{args.port}/", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
