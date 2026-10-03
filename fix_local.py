#!/usr/bin/env python3
"""Download Netlify JS/CSS used by the clone and patch HTML for local preview."""

from __future__ import annotations

import re
import ssl
import urllib.request
from pathlib import Path

NETLIFY = "https://united-carriers.netlify.app"
ROOT = Path(__file__).resolve().parent
JS_ROOT = ROOT / "js"
GTAG = "https://www.googletagmanager.com/gtag/js?id=G-V8J933FGY0"

CTX = ssl.create_default_context()
IMPORT_RE = re.compile(
    r"""(?:from|import)\s*["'](\./[^"']+)["']|import\(["'](\./[^"']+)["']\)"""
)
URL_RE = re.compile(r"""["'](\./(?:chunks|assets)/[^"']+)["']""")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 UnitedCarriersClone"},
    )
    with urllib.request.urlopen(req, context=CTX, timeout=45) as resp:
        return resp.read()


def collect_imports(text: str) -> set[str]:
    found: set[str] = set()
    for a, b in IMPORT_RE.findall(text):
        found.add(a or b)
    for match in URL_RE.findall(text):
        found.add(match)
    return found


def download_tree() -> None:
    JS_ROOT.mkdir(parents=True, exist_ok=True)
    queue = ["./main.js"]
    seen: set[str] = set()
    while queue:
        rel = queue.pop(0)
        rel = rel.split("?")[0]
        if rel in seen:
            continue
        seen.add(rel)
        url = NETLIFY + "/" + rel.lstrip("./")
        dest = JS_ROOT / rel.lstrip("./")
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = fetch(url)
            dest.write_bytes(data)
            print(f"OK  {rel}", flush=True)
            if dest.suffix in {".js", ".mjs", ".css"}:
                text = data.decode("utf-8", errors="replace")
                for child in collect_imports(text):
                    if child.startswith("./"):
                        queue.append(child)
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {rel} {exc}", flush=True)

    main = JS_ROOT / "main.js"
    if main.exists():
        text = main.read_text(encoding="utf-8")
        old = '["united-carriers.webflow.io","united-carriers-bp.webflow.io","united-carriers.netlify.app","unitedcarriers.com"]'
        new = '["united-carriers.webflow.io","united-carriers-bp.webflow.io","united-carriers.netlify.app","unitedcarriers.com","localhost","127.0.0.1","vercel.app"]'
        if old in text:
            main.write_text(text.replace(old, new), encoding="utf-8")
            print("Patched localhost allowlist in main.js", flush=True)
        else:
            print("WARN allowlist string not found", flush=True)


def patch_html() -> None:
    count = 0
    for html_path in ROOT.rglob("index.html"):
        html = html_path.read_text(encoding="utf-8")
        original = html
        html = html.replace(
            'src="https://united-carriers.netlify.app/main.js"',
            'src="/js/main.js"',
        )
        html = re.sub(
            r'<script async="" src="/9i1h7htkfq16NmE0NGVlYzFlZDFhZjJjNGM0MDNkZjZi/mhF8l1Ws1LN3_BS5Ibk2DnX-sDQ"></script>',
            f'<script async="" src="{GTAG}"></script>',
            html,
        )
        html = re.sub(
            r'<script id="cookieyes"[^>]*></script>\s*',
            "",
            html,
        )
        html = html.replace('mainScript.src = "https://localhost:3000/src/main.js";', 'mainScript.src = "/js/main.js";')
        html = html.replace('viteClient.src = "https://localhost:3000/@vite/client";', "viteClient.src = '/js/main.js';")
        if html != original:
            html_path.write_text(html, encoding="utf-8")
            count += 1
    print(f"Patched {count} HTML files", flush=True)


if __name__ == "__main__":
    download_tree()
    patch_html()
