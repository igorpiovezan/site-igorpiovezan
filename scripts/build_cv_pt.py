#!/usr/bin/env python3
"""Build the Portuguese résumé PDF.

LinkedIn only exports the profile's primary language, so this résumé is
generated here from the same facts. It is not a LinkedIn export. The contact
block is read from assets/cv/igor-piovezan-linkedin-en.pdf and copied into
the Portuguese file. Igor approved that contact block for these two PDFs.

The site HTML must not repeat the phone number or the email address.

    python3 scripts/build_cv_pt.py

Requires PyMuPDF and WeasyPrint (pip install pymupdf weasyprint) and
Liberation Sans, the Arial-compatible face used to match the LinkedIn export.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

import pymupdf
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).with_name("cv_pt.html")
ENGLISH = ROOT / "assets" / "cv" / "igor-piovezan-linkedin-en.pdf"
OUTPUT = ROOT / "assets" / "cv" / "igor-piovezan-linkedin-pt-br.pdf"


def read_contact(pdf: Path) -> dict[str, str]:
    lines = [line.strip() for line in pymupdf.open(pdf)[0].get_text("text").splitlines()]
    try:
        start = lines.index("Contact")
        end = lines.index("Top Skills")
    except ValueError as exc:
        raise SystemExit("the English résumé has no Contact block to copy") from exc
    phone = email = linkedin = site = ""
    for line in lines[start + 1 : end]:
        if not line:
            continue
        if "@" in line and not email:
            email = line
        elif "linkedin.com" in line and not linkedin:
            linkedin = line.split()[0]
        elif "igorpiovezan.com" in line and not site:
            site = line.replace("(Personal)", "").strip()
        elif line.startswith("+") and not phone:
            phone = line.split()[0]
    if not (phone and email and linkedin and site):
        raise SystemExit("the English résumé contact block is incomplete")
    return {"phone": phone, "email": email, "linkedin": linkedin, "site": site}


def render(contact: dict[str, str]) -> str:
    document = TEMPLATE.read_text(encoding="utf-8")
    for key, token in (
        ("phone", "{{PHONE}}"),
        ("email", "{{EMAIL}}"),
        ("linkedin", "{{LINKEDIN}}"),
        ("site", "{{SITE}}"),
    ):
        document = document.replace(token, html.escape(contact[key], quote=True))
    if "{{" in document:
        raise SystemExit("the Portuguese résumé template still has an empty field")
    return document


def main() -> None:
    if not ENGLISH.is_file():
        raise SystemExit(f"missing {ENGLISH}")
    contact = read_contact(ENGLISH)
    HTML(string=render(contact), base_url=str(TEMPLATE.parent)).write_pdf(OUTPUT)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
