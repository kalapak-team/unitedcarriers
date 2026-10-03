#!/usr/bin/env python3
"""Clone the published United Carriers Webflow site into this folder."""

from __future__ import annotations

import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://unitedcarriers.com"
ROOT = Path(__file__).resolve().parent
OUT = ROOT
SITEMAP = ROOT / "_sitemap.xml"

EXTRA = [
    "/",
    "/about",
    "/services",
    "/industries",
    "/insights",
    "/careers",
    "/contact",
    "/community",
    "/404",
    "/401",
    "/carbon-calculator",
    "/live-tracking",
    "/tracking",
    "/cookie-settings",
]

CTX = ssl.create_default_context()
HREF_RE = re.compile(r"""(?:href|action)=["']([^"'#?]+)""", re.I)
LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
SKIP_PREFIXES = ("/cdn-cgi/", "/api/")
SKIP_EXT = {".css", ".js", ".json", ".xml", ".txt", ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".mp4", ".webm", ".woff", ".woff2", ".ttf", ".ico"}


def path_from_url(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in {"mailto", "tel", "javascript"}:
        return None
    host = (parsed.netloc or "").lower()
    if host and host not in {"unitedcarriers.com", "www.unitedcarriers.com"}:
        return None
    p = parsed.path or "/"
    if p.startswith("//"):
        return None
    name = Path(p).name
    suffix = Path(name).suffix.lower()
    if suffix and suffix in SKIP_EXT:
        return None
    if any(p.startswith(pref) for pref in SKIP_PREFIXES):
        return None
    if p != "/":
        p = p.rstrip("/")
    return p or "/"


def local_file_for(path: str) -> Path:
    if path == "/":
        return OUT / "index.html"
    return OUT / path.lstrip("/") / "index.html"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, context=CTX, timeout=45) as resp:
        return resp.read()


def clean_html(html: str) -> str:
    html = html.replace('data-wf-domain="unitedcarriers.com"', 'data-wf-domain="localhost"')
    return html


def discover_links(html: str) -> set[str]:
    found: set[str] = set()
    for match in HREF_RE.findall(html):
        if match.startswith("http"):
            path = path_from_url(match)
        elif match.startswith("/"):
            path = path_from_url(BASE + match)
        else:
            continue
        if path:
            found.add(path)
    return found


def sitemap_paths() -> list[str]:
    paths: list[str] = []
    try:
        raw = fetch(BASE + "/sitemap.xml")
        SITEMAP.write_bytes(raw)
        text = raw.decode("utf-8", errors="replace")
        for loc in LOC_RE.findall(text):
            path = path_from_url(loc.strip())
            if path:
                paths.append(path)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN sitemap: {exc}")
    return paths


def main() -> None:
    queue = list(dict.fromkeys(sitemap_paths() + EXTRA))
    seen: set[str] = set()
    ok: list[str] = []
    failed: list[str] = []

    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        url = BASE if path == "/" else BASE + path
        dest = local_file_for(path)
        try:
            raw = fetch(url)
            html = raw.decode("utf-8", errors="replace")
            html = clean_html(html)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(html, encoding="utf-8")
            ok.append(path)
            print(f"OK  {path}", flush=True)
            for link in discover_links(html):
                if link not in seen:
                    queue.append(link)
            time.sleep(0.12)
        except urllib.error.HTTPError as exc:
            failed.append(f"{path} ({exc.code})")
            print(f"ERR {path} HTTP {exc.code}", flush=True)
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{path} ({exc})")
            print(f"ERR {path} {exc}", flush=True)

    print("\nCloned {0} pages".format(len(ok)), flush=True)
    if failed:
        print("Failed:", flush=True)
        for item in failed:
            print("  -", item, flush=True)


if __name__ == "__main__":
    main()
