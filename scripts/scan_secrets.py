#!/usr/bin/env python3
"""Reject phones, emails, and common credentials in tracked files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS = (
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("phone", re.compile(r"(?:\+\d{11,15}|\(\d{2}\)\s*\d{4,5}[\s.-]?\d{4})")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b|\bghp_[A-Za-z0-9]{20,}\b")),
)


def tracked_files() -> list[Path]:
    skip = {".git", "dist", "__pycache__"}
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip for part in path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return files


def main() -> None:
    failures = []
    for path in tracked_files():
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".webp", ".ico"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in PATTERNS:
            match = pattern.search(text)
            if match:
                failures.append(f"{path.relative_to(ROOT)}: {label}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(f"{len(failures)} secret or contact hit(s)")
    print("secret scan passed")


if __name__ == "__main__":
    main()
