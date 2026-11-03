#!/usr/bin/env python3
"""Raster brand images. Run when the artwork changes; the build only hashes the results."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
INK = (16, 33, 30)
CREAM = (246, 241, 231)
BRASS = (226, 181, 106)


def font(path, size):
    return ImageFont.truetype(path, size)


def nameplate(width, height, domain=True):
    image = Image.new("RGB", (width, height), INK)
    draw = ImageDraw.Draw(image)
    draw.rectangle((48, 48, width - 48, height - 48), outline=BRASS, width=3)
    draw.text((width / 2, height * 0.30), "IGOR AGENOR", font=font(SANS, int(width * 0.028)), fill=BRASS, anchor="mm")
    draw.text((width / 2, height * 0.48), "PIOVEZAN", font=font(SERIF, int(width * 0.078)), fill=CREAM, anchor="mm")
    draw.text((width / 2, height * 0.66), "CTO  ·  SEGWARE", font=font(SANS, int(width * 0.028)), fill=CREAM, anchor="mm")
    if domain:
        draw.text((width / 2, height * 0.80), "igorpiovezan.com", font=font(SANS, int(width * 0.024)), fill=BRASS, anchor="mm")
    return image


def icon(size):
    image = Image.new("RGB", (size, size), INK)
    draw = ImageDraw.Draw(image)
    margin = int(size * 0.08)
    draw.rounded_rectangle((margin, margin, size - margin, size - margin), radius=int(size * 0.12), outline=BRASS, width=max(2, size // 32))
    draw.text((size / 2, size * 0.56), "IP", font=font(SERIF, int(size * 0.38)), fill=CREAM, anchor="mm")
    return image


def main():
    ASSETS.mkdir(exist_ok=True)
    hero = nameplate(1200, 675)
    hero.save(ASSETS / "hero.webp", "WEBP", quality=68, method=6)
    og = nameplate(1200, 630)
    og.save(ASSETS / "og.png", "PNG", optimize=True)
    touch = icon(180)
    touch.save(ASSETS / "apple-touch-icon.png", "PNG", optimize=True)
    icon(32).save(ASSETS / "favicon-32.png", "PNG", optimize=True)
    icon(192).save(ASSETS / "icon-192.png", "PNG", optimize=True)
    icon(512).save(ASSETS / "icon-512.png", "PNG", optimize=True)
    icon(64).save(
        ASSETS / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )
    meta = {
        "hero": {"file": "hero.webp", "width": 1200, "height": 675},
        "og": {"file": "og.png", "width": 1200, "height": 630},
    }
    (ASSETS / "media.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("assets ready", hero.size, og.size)


if __name__ == "__main__":
    main()
