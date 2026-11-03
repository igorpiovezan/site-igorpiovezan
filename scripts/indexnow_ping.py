#!/usr/bin/env python3
"""Submit the production sitemap URLs to IndexNow.

Run this only after the production deploy is public. The key file must already
answer at https://igorpiovezan.com/<key>.txt.

    python3 scripts/indexnow_ping.py --sitemap /tmp/igor-prod/sitemap.xml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.indexnow.org/indexnow"
HOST = "igorpiovezan.com"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def indexnow_key() -> str:
    site = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    key = site.get("indexNow") or ""
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise SystemExit("content/site.json indexNow must be 32 lowercase hex characters")
    return key


def sitemap_urls(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    urls = []
    for node in root.findall("sm:url/sm:loc", SITEMAP_NS):
        if node.text and node.text.strip():
            urls.append(node.text.strip())
    if not urls:
        raise SystemExit(f"no URLs in {path}")
    for url in urls:
        if not url.startswith(f"https://{HOST}/"):
            raise SystemExit(f"sitemap URL is not on {HOST}: {url}")
    return urls


def payload(key: str, urls: list[str]) -> dict:
    return {
        "host": HOST,
        "key": key,
        "keyLocation": f"https://{HOST}/{key}.txt",
        "urlList": urls,
    }


def post(body: dict) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit sitemap URLs to IndexNow")
    parser.add_argument("--sitemap", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Print the payload and do not POST")
    args = parser.parse_args()
    body = payload(indexnow_key(), sitemap_urls(args.sitemap))
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    status, detail = post(body)
    print(f"IndexNow {status}: {len(body['urlList'])} URLs")
    if detail.strip():
        print(detail.strip())
    if status not in {200, 202}:
        raise SystemExit(f"IndexNow rejected the submission ({status})")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as exc:
        raise SystemExit(f"IndexNow request failed: {exc.reason}") from exc
    except KeyboardInterrupt:
        sys.exit(130)
