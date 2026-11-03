#!/usr/bin/env python3
"""Build prod and preview trees and check the SEO contract."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://igorpiovezan.com"
ID = "G-XNKKPQ0RHB"
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "xhtml": "http://www.w3.org/1999/xhtml",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def build(env: str, out: Path) -> None:
    subprocess.check_call(
        [sys.executable, str(ROOT / "scripts" / "build.py"), "--env", env, "--out", str(out)],
        cwd=ROOT,
    )


def html_files(out: Path) -> list[Path]:
    return sorted(out.rglob("*.html"))


def check_prod(out: Path) -> None:
    if not (out / "favicon.ico").is_file() or not (out / "apple-touch-icon.png").is_file():
        fail("favicon.ico and apple-touch-icon.png must sit at the site root")
    if not (out / "llms.txt").is_file() or not (out / "llms-full.txt").is_file():
        fail("llms.txt and llms-full.txt are required")
    robots = (out / "robots.txt").read_text(encoding="utf-8")
    if "Allow: /" not in robots or "Sitemap: https://igorpiovezan.com/sitemap.xml" not in robots:
        fail("production robots.txt must allow crawlers and list the sitemap")
    for bot in ("Googlebot", "GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot"):
        if f"User-agent: {bot}" not in robots:
            fail(f"production robots.txt missing {bot}")
    if "Disallow: /" in robots:
        fail("production robots.txt must not disallow the site")
    pages = {path.relative_to(out).as_posix(): path.read_text(encoding="utf-8") for path in html_files(out)}
    for name, html in pages.items():
        if "FAQPage" in html:
            fail(f"{name} includes FAQPage without a visible FAQ")
        if HOST not in html:
            fail(f"{name} missing canonical host")
        canonical = re.findall(r'<link rel="canonical" href="([^"]+)"', html)
        og = re.findall(r'<meta property="og:url" content="([^"]+)"', html)
        if canonical != og or not canonical or not canonical[0].startswith(HOST):
            fail(f"{name} canonical and og:url must match on {HOST}")
        if "twitter:card" not in html or "og:image" not in html or "og:title" not in html:
            fail(f"{name} missing Open Graph or Twitter tags")
        for lang in ('hreflang="en"', 'hreflang="pt-BR"', 'hreflang="x-default"'):
            if lang not in html:
                fail(f"{name} missing {lang}")
        ids = re.findall(r'"@id":\s*"(https://igorpiovezan.com[^"]*)"', html)
        if not ids:
            fail(f"{name} missing JSON-LD @id on the canonical host")
        for kind in ("Person", "WebSite", "WebPage"):
            if f'"@type": "{kind}"' not in html and f'"@type":"{kind}"' not in html:
                fail(f"{name} missing JSON-LD {kind}")
        if "linkedin.com/in/igorpiovezan" not in html or "github.com/igorpiovezan" not in html:
            fail(f"{name} Person sameAs links missing")
        if name == "404.html":
            if 'content="noindex, nofollow"' not in html:
                fail("404 must be noindex")
        elif 'content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"' not in html:
            fail(f"{name} must be indexable in the production build")
        if "igor_consent" not in html or ID not in html:
            fail(f"{name} missing consent key or measurement id")
        gate = html.find('if (host !== "igorpiovezan.com" && host !== "igorpiovezan.com.br") return;')
        tag = html.find("https://www.googletagmanager.com/gtag/js?id=" + ID)
        if gate < 0 or tag < 0 or gate > tag:
            fail(f"{name} must return before loading gtag unless the host is igorpiovezan.com or .com.br")
        for signal in ("ad_storage", "ad_user_data", "ad_personalization", "analytics_storage"):
            if f'{signal}: "denied"' not in html:
                fail(f"{name} consent default missing {signal}")
    home = pages["index.html"]
    imgs = re.findall(r"<img\b[^>]*>", home)
    if not imgs:
        fail("home needs an LCP image")
    first = imgs[0]
    if 'fetchpriority="high"' not in first or "width=" not in first or "height=" not in first:
        fail("LCP image needs width, height, and fetchpriority=high")
    if "loading=\"lazy\"" in first:
        fail("LCP image must not be lazy")
    for img in imgs[1:]:
        if 'loading="lazy"' not in img:
            fail("images below the LCP image must be lazy")
    for html in pages.values():
        for match in re.findall(r'(?:src|href)="(/assets/[^"]+)"', html):
            name = match.rsplit("/", 1)[-1]
            if not re.search(r"-[0-9a-f]{10}\.", name):
                fail(f"asset is not content-hashed: {match}")
            if not (out / match.lstrip("/")).is_file():
                fail(f"missing asset {match}")
    tree = ET.parse(out / "sitemap.xml")
    locs = [node.text for node in tree.findall(".//sm:loc", NS)]
    expected = {
        f"{HOST}/",
        f"{HOST}/pt-br/",
        f"{HOST}/notes/",
        f"{HOST}/pt-br/notas/",
        f"{HOST}/privacy/",
        f"{HOST}/pt-br/privacidade/",
    }
    if set(locs) != expected:
        fail(f"sitemap URLs must be exactly the indexable pages, found {locs}")
    if f"{HOST}/404.html" in locs or "llms.txt" in "".join(locs):
        fail("sitemap includes a non-indexable URL")
    for url in tree.findall("sm:url", NS):
        langs = [link.attrib.get("hreflang") for link in url.findall("xhtml:link", NS)]
        if langs != ["en", "pt-BR", "x-default"]:
            fail(f"sitemap hreflang set is wrong: {langs}")
    blob = "\n".join(pages.values()) + (out / "llms.txt").read_text(encoding="utf-8") + (out / "llms-full.txt").read_text(encoding="utf-8")
    forbidden = (
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
        r"\+\d{10,}",
        r"wa\.me",
        r"generate_lead",
        r"whatsapp",
    )
    for pattern in forbidden:
        if re.search(pattern, blob, re.I):
            fail(f"published output matched forbidden pattern {pattern}")


def check_test(out: Path) -> None:
    robots = (out / "robots.txt").read_text(encoding="utf-8")
    if "Allow: /" in robots or "Sitemap:" in robots:
        fail("preview robots.txt must not allow crawling or advertise the sitemap")
    if "Disallow: /" not in robots or "User-agent: GPTBot" not in robots:
        fail("preview robots.txt must disallow every crawler, including AI crawlers")
    for path in html_files(out):
        html = path.read_text(encoding="utf-8")
        if 'content="noindex, nofollow"' not in html:
            fail(f"preview {path.name} must be noindex")


def check_source_id() -> None:
    hits = []
    for path in (ROOT / "content").rglob("*.json"):
        if ID in path.read_text(encoding="utf-8"):
            hits.append(path.relative_to(ROOT).as_posix())
    for path in (ROOT / "src").rglob("*"):
        if path.is_file() and ID in path.read_text(encoding="utf-8"):
            hits.append(path.relative_to(ROOT).as_posix())
    for path in (ROOT / "scripts").rglob("*.py"):
        if path.name == "check_site.py":
            continue
        if ID in path.read_text(encoding="utf-8"):
            hits.append(path.relative_to(ROOT).as_posix())
    if hits != ["content/site.json"]:
        fail(f"measurement id must live only in content/site.json, found {hits}")


def main() -> None:
    check_source_id()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        prod = root / "prod"
        preview = root / "test"
        build("prod", prod)
        build("test", preview)
        check_prod(prod)
        check_test(preview)
    print("site checks passed")


if __name__ == "__main__":
    main()
