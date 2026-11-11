#!/usr/bin/env python3
"""Build the static site into a dist folder.

Usage:
  python3 scripts/build.py
  python3 scripts/build.py --env test --out /tmp/igor-preview
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
SRC = ROOT / "src"
ASSETS = ROOT / "assets"

MEASUREMENT_ID_RE = re.compile(r"^G-[A-Z0-9]+$")

BOTS = (
    "*",
    "Googlebot",
    "Googlebot-Image",
    "Bingbot",
    "DuckDuckBot",
    "Applebot",
    "YandexBot",
    "GPTBot",
    "ChatGPT-User",
    "OAI-SearchBot",
    "ClaudeBot",
    "Claude-User",
    "Claude-SearchBot",
    "anthropic-ai",
    "Google-Extended",
    "Applebot-Extended",
    "PerplexityBot",
    "Perplexity-User",
    "meta-externalagent",
    "Meta-ExternalFetcher",
    "Amazonbot",
    "CCBot",
    "cohere-ai",
    "MistralAI-User",
    "DeepSeekBot",
    "Bytespider",
    "YouBot",
    "GrokBot",
    "xAI-SearchBot",
    "GrokAgent",
)

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "pt-BR": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
}

PAGES = (
    {"id": "home", "lang": "en", "file": "index.html"},
    {"id": "home", "lang": "pt-BR", "file": "pt-br/index.html"},
    {"id": "notes", "lang": "en", "file": "notes/index.html"},
    {"id": "notes", "lang": "pt-BR", "file": "pt-br/notas/index.html"},
    {"id": "privacy", "lang": "en", "file": "privacy/index.html"},
    {"id": "privacy", "lang": "pt-BR", "file": "pt-br/privacidade/index.html"},
)


def load_json(name: str) -> dict:
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


def text(value, lang: str) -> str:
    if isinstance(value, dict):
        return value.get(lang) or value.get("en") or ""
    if value is None:
        return ""
    return str(value)


def e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt_month(ym: str | None, lang: str) -> str:
    if not ym:
        return ""
    year, month = ym.split("-")[:2]
    return f"{MONTHS[lang][int(month) - 1]} {year}"


def fmt_day(iso: str | None, lang: str) -> str:
    if not iso:
        return ""
    parts = iso.split("-")
    if len(parts) == 2:
        return fmt_month(iso, lang)
    year, month, day = parts
    return f"{int(day)} {MONTHS[lang][int(month) - 1]} {year}"


def fmt_range(start: str | None, end: str | None, lang: str, present: str) -> str:
    right = present if not end else fmt_month(end, lang)
    return f"{fmt_month(start, lang)} – {right}"


def sha_name(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
    return f"{path.stem}-{digest}{path.suffix}"


def write_hashed(src: Path, dest_dir: Path) -> str:
    name = sha_name(src)
    target = dest_dir / name
    target.write_bytes(src.read_bytes())
    return f"/assets/{name}"


def absolute(host: str, path: str) -> str:
    if path == "/":
        return host + "/"
    return host + path


def ui(bundle, lang: str, key: str) -> str:
    return text(bundle["ui"][key], lang)


def ga_script(measurement_id: str) -> str:
    if not MEASUREMENT_ID_RE.match(measurement_id):
        raise SystemExit(f"invalid GA4 measurement id: {measurement_id!r}")
    return f"""<script>
(function () {{
  var host = "";
  try {{
    host = String(location.hostname || "").toLowerCase().replace(/^www\\./, "");
  }} catch (err) {{
    return;
  }}
  if (host !== "igorpiovezan.com" && host !== "igorpiovezan.com.br") return;
  window.dataLayer = window.dataLayer || [];
  function gtag() {{ window.dataLayer.push(arguments); }}
  window.gtag = gtag;
  gtag("consent", "default", {{
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: "denied",
    wait_for_update: 500
  }});
  try {{
    if (localStorage.getItem("igor_consent") === "granted") {{
      gtag("consent", "update", {{
        ad_storage: "granted",
        ad_user_data: "granted",
        ad_personalization: "granted",
        analytics_storage: "granted"
      }});
    }}
  }} catch (err) {{ /* private mode */ }}
  gtag("js", new Date());
  gtag("config", "{measurement_id}", {{ anonymize_ip: true }});
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id={measurement_id}";
  document.head.appendChild(s);
}})();
</script>"""


def json_ld(bundle, lang: str, page_url: str, title: str, description: str, og_url: str) -> str:
    host = bundle["site"]["canonicalHost"]
    profile = bundle["profile"]
    creds = bundle["credentials"]
    person_id = host + "/#person"
    website_id = host + "/#website"
    alumni = []
    for school in creds["education"]:
        alumni.append({
            "@type": "CollegeOrUniversity" if "MIT" in school["school"] or "IFSC" in school["school"] or "Universit" in school["school"] else "EducationalOrganization",
            "name": school["school"],
            "url": school["url"],
        })
    credentials = []
    for cert in creds["certifications"]:
        item = {
            "@type": "EducationalOccupationalCredential",
            "name": text(cert["name"], lang),
            "recognizedBy": {"@type": "Organization", "name": cert["issuer"]},
        }
        if cert.get("url"):
            item["url"] = cert["url"]
        if cert.get("issued"):
            item["dateCreated"] = cert["issued"]
        if cert.get("expires"):
            item["expires"] = cert["expires"]
        credentials.append(item)
    person = {
        "@type": "Person",
        "@id": person_id,
        "name": profile["name"],
        "givenName": profile["givenName"],
        "additionalName": profile["additionalName"],
        "familyName": profile["familyName"],
        "jobTitle": job_titles(profile, lang),
        "description": text(profile["headline"], lang),
        "url": host + "/",
        "image": og_url,
        "sameAs": bundle["site"]["sameAs"],
        "worksFor": {
            "@type": "Organization",
            "name": profile["worksFor"]["name"],
            "url": profile["worksFor"]["url"],
            "sameAs": profile["worksFor"]["sameAs"],
            "description": text(
                next(company["summary"] for company in bundle["experience"]["companies"] if company["id"] == "segware"),
                lang,
            ),
        },
        "address": {
            "@type": "PostalAddress",
            "addressLocality": profile["location"]["locality"],
            "addressRegion": profile["location"]["region"],
            "addressCountry": profile["location"]["country"],
        },
        "alumniOf": alumni,
        "hasCredential": credentials,
        "knowsAbout": knows_about(profile, lang),
        "knowsLanguage": [text(item["name"], "en") for item in profile["languages"]],
    }
    awards = (bundle.get("footprint") or {}).get("awards") or {}
    award_list = awards.get(lang) or awards.get("en") or []
    if award_list:
        person["award"] = award_list
    profile_page = page_url.rstrip("/") in {host, f"{host}/pt-br"}
    webpage = {
        "@type": ["WebPage", "ProfilePage"] if profile_page else "WebPage",
        "@id": page_url + "#webpage",
        "url": page_url,
        "name": title,
        "description": description,
        "isPartOf": {"@id": website_id},
        "about": {"@id": person_id},
        "inLanguage": "pt-BR" if lang == "pt-BR" else "en",
        "primaryImageOfPage": og_url,
    }
    if profile_page:
        webpage["mainEntity"] = {"@id": person_id}
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            person,
            {
                "@type": "WebSite",
                "@id": website_id,
                "url": host + "/",
                "name": profile["name"],
                "inLanguage": ["en", "pt-BR"],
                "publisher": {"@id": person_id},
            },
            webpage,
        ],
    }
    payload = json.dumps(graph, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{payload}</script>'


def head(bundle, *, lang, title, description, path, robots, css, ga, assets) -> str:
    site = bundle["site"]
    host = site["canonicalHost"]
    page_url = absolute(host, path)
    locale = site["locales"][lang]
    other = "pt-BR" if lang == "en" else "en"
    other_locale = site["locales"][other]
    # path is this page; alternates come from the caller via bundle["_alts"]
    alts = bundle["_alts"]
    links = [
        f'<link rel="canonical" href="{e(page_url)}">',
        f'<link rel="alternate" hreflang="en" href="{e(absolute(host, alts["en"]))}">',
        f'<link rel="alternate" hreflang="pt-BR" href="{e(absolute(host, alts["pt-BR"]))}">',
        f'<link rel="alternate" hreflang="x-default" href="{e(absolute(host, alts["en"]))}">',
    ]
    og_image = absolute(host, assets["og"])
    icons = [
        '<link rel="icon" href="/favicon.ico" sizes="any">',
        f'<link rel="icon" href="{e(assets["svg"])}" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<link rel="manifest" href="/site.webmanifest">',
    ]
    metas = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(title)}</title>",
        f'<meta name="description" content="{e(description)}">',
        f'<meta name="author" content="{e(bundle["profile"]["name"])}">',
        f'<meta name="robots" content="{robots}">',
        '<meta name="theme-color" content="#10211e">',
        '<meta name="color-scheme" content="light dark">',
        '<meta name="referrer" content="strict-origin-when-cross-origin">',
        '<meta property="og:site_name" content="Igor Agenor Piovezan">',
        f'<meta property="og:type" content="{"profile" if path in ("/", "/pt-br/") else "website"}">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(description)}">',
        f'<meta property="og:url" content="{e(page_url)}">',
        f'<meta property="og:image" content="{e(og_image)}">',
        f'<meta property="og:image:width" content="{assets["og_w"]}">',
        f'<meta property="og:image:height" content="{assets["og_h"]}">',
        f'<meta property="og:image:alt" content="{e(title)}">',
        f'<meta property="og:locale" content="{e(locale["og"])}">',
        f'<meta property="og:locale:alternate" content="{e(other_locale["og"])}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{e(title)}">',
        f'<meta name="twitter:description" content="{e(description)}">',
        f'<meta name="twitter:image" content="{e(og_image)}">',
    ]
    if path in ("/", "/pt-br/"):
        metas.append('<meta property="profile:first_name" content="Igor">')
        metas.append('<meta property="profile:last_name" content="Piovezan">')
    structured = json_ld(bundle, lang, page_url, title, description, og_image)
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{e(locale["html"])}">\n<head>\n'
        + "\n".join(metas)
        + "\n"
        + "\n".join(links)
        + "\n"
        + "\n".join(icons)
        + "\n"
        + structured
        + "\n"
        + ga
        + "\n<style>\n"
        + css
        + "\n</style>\n</head>\n"
    )


def header(bundle, lang, page_id) -> str:
    home = bundle["site"]["locales"][lang]["home"]
    other = "pt-BR" if lang == "en" else "en"
    other_path = bundle["_alts"][other]
    sections = (
        ("about", "navAbout"),
        ("technologies", "navTechnologies"),
        ("world", "navWorld"),
        ("experience", "navExperience"),
        ("work", "navWork"),
        ("speaking", "navSpeaking"),
        ("footprint", "navFootprint"),
        ("background", "navBackground"),
    )
    nav = []
    for anchor, key in sections:
        href = f"#{anchor}" if page_id == "home" else f"{home}#{anchor}"
        nav.append(f'<a href="{e(href)}">{e(ui(bundle, lang, key))}</a>')
    notes_href = bundle["site"]["locales"][lang]["notes"]
    current = ' aria-current="page"' if page_id == "notes" else ""
    nav.append(f'<a href="{e(notes_href)}"{current}>{e(ui(bundle, lang, "navNotes"))}</a>')
    if page_id == "home":
        lang_current = f'<span aria-current="page" lang="{e(bundle["site"]["locales"][lang]["html"])}">{e(ui(bundle, lang, "langName"))}</span>'
    else:
        lang_current = f'<a href="{e(bundle["_alts"][lang])}" aria-current="page" lang="{e(bundle["site"]["locales"][lang]["html"])}">{e(ui(bundle, lang, "langName"))}</a>'
    other_html = bundle["site"]["locales"][other]["html"]
    switch = (
        f'<a href="{e(other_path)}" hreflang="{e(other_html)}" lang="{e(other_html)}">'
        f'{e(ui(bundle, lang, "switchTo"))}</a>'
    )
    return (
        f'<a class="skip" href="#content">{e(ui(bundle, lang, "skip"))}</a>'
        '<header class="site-header"><div class="wrap">'
        f'<a class="brand" href="{e(home)}">{e(bundle["profile"]["name"])}</a>'
        f'<nav class="nav" aria-label="{"Sections" if lang == "en" else "Seções"}">' + "".join(nav) + "</nav>"
        f'<div class="lang">{lang_current}{switch}</div>'
        "</div></header>"
    )


def footer(bundle, lang) -> str:
    site = bundle["site"]
    privacy = site["locales"][lang]["privacy"]
    notes = site["locales"][lang]["notes"]
    return (
        '<footer class="site-footer"><div class="wrap">'
        f'<p>{e(ui(bundle, lang, "footerNote"))}</p>'
        f'<p>{e(ui(bundle, lang, "connect"))}</p>'
        '<p class="profile-links">'
        f'<a href="{e(privacy)}">{e(ui(bundle, lang, "privacy"))}</a>'
        f'<a href="{e(notes)}">{e(ui(bundle, lang, "navNotes"))}</a>'
        f'<a href="{e(site["linkedin"])}">LinkedIn</a>'
        f'<a href="{e(site["github"])}">GitHub</a>'
        "</p></div></footer>"
    )


def consent(bundle, lang) -> str:
    privacy = bundle["site"]["locales"][lang]["privacy"]
    return (
        '<div id="igor-consent" class="consent" hidden>'
        f'<p id="igor-consent-title"><strong>{e(ui(bundle, lang, "consentTitle"))}</strong></p>'
        f'<p>{e(ui(bundle, lang, "consentBody"))} '
        f'<a href="{e(privacy)}">{e(ui(bundle, lang, "privacy"))}</a>.</p>'
        '<div class="consent-actions">'
        f'<button type="button" data-consent="granted">{e(ui(bundle, lang, "consentAccept"))}</button>'
        f'<button type="button" data-consent="denied">{e(ui(bundle, lang, "consentDecline"))}</button>'
        "</div></div>"
    )


def paras(items, lang) -> str:
    return "".join(f"<p>{e(text(item, lang))}</p>" for item in items)


def chips(items) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{e(item)}</li>" for item in items)
    return f'<ul class="chips">{lis}</ul>'


def job_titles(profile, lang: str):
    titles = [text(profile["jobTitle"], lang)]
    tagline_items = (profile.get("tagline") or {}).get(lang) or []
    if tagline_items and tagline_items[0] not in titles:
        titles.append(tagline_items[0])
    return titles


def knows_about(profile, lang: str) -> list:
    topics = profile.get("knowsAbout")
    if isinstance(topics, dict):
        localized = topics.get(lang) or topics.get("en") or []
        if localized:
            return localized
    return list(profile["featuredSkills"])


def tagline_list(bundle, lang: str) -> str:
    items = (bundle["profile"].get("tagline") or {}).get(lang) or []
    if not items:
        return ""
    label = ui(bundle, lang, "taglineLabel")
    lis = "".join(f"<li>{e(item)}</li>" for item in items)
    return f'<ul class="tagline" aria-label="{e(label)}">{lis}</ul>'


def stack_block(bundle, lang, items) -> str:
    if not items:
        return ""
    label = ui(bundle, lang, "technologies")
    body = chips(items)
    if len(items) > 14:
        return (
            f'<details class="stack"><summary>{e(ui(bundle, lang, "showStack"))} ({len(items)})</summary>'
            f"{body}</details>"
        )
    return f'<p class="eyebrow">{e(label)}</p>{body}'


CHAPTER = {
    "about": "01",
    "igor": "02",
    "technologies": "03",
    "world": "04",
    "experience": "05",
    "work": "06",
    "speaking": "07",
    "footprint": "08",
    "background": "09",
    "notes": "10",
}

GLYPHS = {
    "aws": """<svg viewBox="0 0 400 280" fill="none" aria-hidden="true"><path d="M48 86h304M48 140h304M48 194h304" stroke="currentColor" stroke-width="1.25"/><rect x="168" y="58" width="64" height="164" stroke="currentColor" stroke-width="1.25"/><circle cx="200" cy="140" r="5" fill="currentColor"/></svg>""",
    "ai": """<svg viewBox="0 0 400 280" fill="none" aria-hidden="true"><path d="M250 64l78 42-18 86-96 22 8-74z" stroke="currentColor" stroke-width="1.25"/><path d="M250 64l48 96M328 106L232 214" stroke="currentColor" stroke-width="1.25"/><circle cx="250" cy="64" r="4" fill="currentColor"/><circle cx="328" cy="106" r="3.5" fill="currentColor"/><circle cx="310" cy="192" r="3.5" fill="currentColor"/><circle cx="232" cy="214" r="3" fill="currentColor"/><circle cx="286" cy="132" r="2.5" fill="currentColor"/></svg>""",
    "cloud": """<svg viewBox="0 0 400 280" fill="none" aria-hidden="true"><rect x="150" y="48" width="196" height="46" rx="8" stroke="currentColor" stroke-width="1.25"/><rect x="118" y="112" width="220" height="46" rx="8" stroke="currentColor" stroke-width="1.25"/><rect x="176" y="176" width="168" height="46" rx="8" stroke="currentColor" stroke-width="1.25"/></svg>""",
    "iot": """<svg viewBox="0 0 400 280" fill="none" aria-hidden="true"><circle cx="250" cy="140" r="78" stroke="currentColor" stroke-width="1.25"/><circle cx="250" cy="140" r="44" stroke="currentColor" stroke-width="1.25"/><circle cx="250" cy="140" r="4" fill="currentColor"/><circle cx="250" cy="62" r="3.5" fill="currentColor"/><circle cx="318" cy="176" r="3.5" fill="currentColor"/><circle cx="186" cy="186" r="3.5" fill="currentColor"/><circle cx="196" cy="86" r="3" fill="currentColor"/></svg>""",
    "data": """<svg viewBox="0 0 400 280" fill="none" aria-hidden="true"><path d="M70 214h270" stroke="currentColor" stroke-width="1.25"/><path d="M96 214V156M132 214V124M168 214V88M204 214V132M240 214V64M276 214V108M312 214V148" stroke="currentColor" stroke-width="1.5"/></svg>""",
}


def h2(number: str, label: str) -> str:
    return f'<h2 class="reveal"><span class="chap-no" aria-hidden="true">{e(number)}</span>{e(label)}</h2>'


def youtube_id(url: str) -> str:
    if not url:
        return ""
    match = re.search(r"(?:v=|youtu\.be/)([\w-]{6,})", url)
    return match.group(1) if match else ""


def still_by_url(assets, url: str):
    return (assets.get("stills") or {}).get(youtube_id(url))


def still_img(still, lazy: bool = True) -> str:
    loading = ' loading="lazy"' if lazy else ""
    return (
        f'<img src="{e(still["src"])}" width="{still["w"]}" height="{still["h"]}" alt=""'
        f'{loading} decoding="async">'
    )


def seal_label(title: str, issuer: str) -> str:
    blob = f"{title} {issuer}".lower()
    if "aws" in blob or "amazon" in blob:
        return "AWS"
    if "mongo" in blob:
        return "MDB"
    if "mit" in blob:
        return "MIT"
    letters = "".join(ch for ch in issuer if ch.isalnum())
    return (letters[:3] or "REC").upper()


def require_locale(value, where: str) -> None:
    if not isinstance(value, dict) or not value.get("en") or not value.get("pt-BR"):
        raise SystemExit(f"missing en/pt-BR copy in {where}")


def resolve_stage(bundle, stage, lang: str) -> dict:
    source = stage.get("source")
    if source == "company":
        company = next(item for item in bundle["experience"]["companies"] if item["id"] == stage["id"])
        return {"name": company["name"], "url": company["url"], "line": text(company["summary"], lang)}
    if source == "education":
        school = next(item for item in bundle["credentials"]["education"] if item["school"] == stage["school"])
        return {"name": school["school"], "url": school["url"], "line": text(school["degree"], lang)}
    if source == "custom":
        require_locale(stage.get("line"), stage.get("id") or "stage")
        return {"name": stage["name"], "url": stage["url"], "line": text(stage["line"], lang)}
    raise SystemExit(f"unknown stage source: {source}")


def validate_chapters(chapters: dict) -> None:
    techs = chapters.get("technologies") or []
    if [item.get("id") for item in techs] != ["aws", "ai", "cloud", "iot", "data"]:
        raise SystemExit("technology chapters must stay AWS, AI, cloud, IoT, data")
    for item in techs:
        if item["id"] not in GLYPHS:
            raise SystemExit(f"missing glyph for {item['id']}")
        require_locale(item.get("name"), item["id"])
        require_locale(item.get("line"), item["id"])
    for stage in chapters.get("stages") or []:
        if stage.get("tier") not in ("primary", "secondary"):
            raise SystemExit("stage tier must be primary or secondary")
        if stage.get("source") == "custom":
            require_locale(stage.get("line"), stage.get("id") or "stage")


def logo_chip(assets, logo_id: str) -> str:
    logo = (assets.get("logos") or {}).get(logo_id or "")
    if not logo:
        return ""
    tone = " on-dark" if logo.get("chip") == "dark" else ""
    return (
        f'<span class="logo-chip{tone}">'
        f'<img class="logo" src="{e(logo["src"])}" width="{logo["w"]}" height="{logo["h"]}" alt="" loading="lazy" decoding="async">'
        "</span>"
    )


def badge_for(assets, url: str):
    for badge in assets.get("badges") or []:
        if badge.get("match") and badge["match"] in (url or ""):
            return badge
    return None


def fmt_cert_date(value: str | None, lang: str) -> str:
    if not value:
        return ""
    if len(value.split("-")) >= 3:
        return fmt_day(value, lang)
    return fmt_month(value, lang)


def render_hero(bundle, lang, assets) -> str:
    profile = bundle["profile"]
    ready = bool(assets.get("portrait"))
    if ready:
        src = assets["portrait"]
        width = assets["portrait_w"]
        height = assets["portrait_h"]
        alt = text(assets.get("portrait_alt") or profile["name"], lang)
        caption = ui(bundle, lang, "portraitReadyCaption")
        frame = "portrait is-photo"
        kicker = ""
    else:
        src = assets["hero"]
        width = assets["hero_w"]
        height = assets["hero_h"]
        alt = (
            "Nameplate reading Igor Agenor Piovezan, CTO at Segware"
            if lang == "en"
            else "Cartão com o nome Igor Agenor Piovezan, CTO na Segware"
        )
        caption = ui(bundle, lang, "portraitCaption")
        frame = "portrait is-slot"
        kicker = f'<span class="slot-kicker">{e(ui(bundle, lang, "portraitReserved"))}</span>'
    stats = "".join(
        f'<li><strong>{e(item["value"])}</strong><span>{e(text(item["label"], lang))}</span></li>'
        for item in profile["impact"]
    )
    return (
        '<section class="hero"><div class="wrap hero-layout">'
        '<div class="hero-copy">'
        f'<p class="kicker">{e(text(profile["jobTitle"], lang))}, {e(profile["worksFor"]["name"])}</p>'
        '<h1><span class="name-line">Igor Agenor</span><span class="name-line">Piovezan</span></h1>'
        f'<p class="headline">{e(text(profile["headline"], lang))}</p>'
        f'<p class="lede">{e(text(profile["location"]["label"], lang))}</p>'
        '<p class="hero-actions">'
        f'<a href="{e(bundle["site"]["linkedin"])}">LinkedIn</a>'
        f'<a href="{e(bundle["site"]["github"])}">GitHub</a>'
        f'<a href="#igor">{e(ui(bundle, lang, "publicStills"))}</a>'
        "</p></div>"
        f'<figure class="{frame}">'
        '<div class="portrait-frame">'
        f'<img class="portrait-img" src="{e(src)}" width="{width}" height="{height}" alt="{e(alt)}" fetchpriority="high">'
        "</div>"
        f"<figcaption>{kicker}{e(caption)}</figcaption>"
        "</figure>"
        f'<ul class="proof" aria-label="{e(ui(bundle, lang, "impactTitle"))}">{stats}</ul>'
        "</div></section>"
    )


def render_igor(bundle, lang, assets) -> str:
    cards = []
    for item in bundle["footprint"]["talks"]:
        still = still_by_url(assets, item["url"])
        if not still:
            continue
        when = footprint_when(item.get("date") or "", lang)
        cards.append(
            f'<a class="still reveal" href="{e(item["url"])}" rel="noopener noreferrer">'
            '<span class="still-media">'
            f'{still_img(still)}'
            '<span class="play" aria-hidden="true"></span>'
            "</span><span class=\"still-copy\">"
            f"<strong>{e(text(item['title'], lang))}</strong>"
            f'<span class="muted">{e(ui(bundle, lang, "watchYouTube"))}'
            f'{(" · " + e(when)) if when else ""}</span>'
            "</span></a>"
        )
    return (
        f'<section id="igor"><div class="wrap">{h2(CHAPTER["igor"], ui(bundle, lang, "igorTitle"))}'
        f'<p class="lede reveal">{e(ui(bundle, lang, "igorLead"))}</p>'
        f'<div class="film">{"".join(cards)}</div>'
        f'<h3>{e(ui(bundle, lang, "photoTitle"))}</h3>'
        f'<p class="lede reveal">{e(ui(bundle, lang, "photoLead"))}</p>'
        f'<div class="photo-grid">{"".join(render_photo(photo, lang) for photo in assets.get("photos") or [])}</div>'
        "</div></section>"
    )


def render_photo(photo, lang: str) -> str:
    focus = f' style="object-position: {e(photo["focus"])}"' if photo.get("focus") else ""
    source = photo.get("source") or ""
    linked = source.startswith("http://") or source.startswith("https://")
    alt = "" if linked else text(photo.get("alt") or {}, lang)
    image = (
        f'<img src="{e(photo["src"])}" width="{photo["w"]}" height="{photo["h"]}" alt="{e(alt)}" '
        f'loading="lazy" decoding="async"{focus}>'
    )
    frame = f'<span class="photo-frame">{image}</span>'
    caption = e(text(photo["caption"], lang))
    if linked:
        return (
            f'<a class="photo reveal" href="{e(source)}" rel="noopener noreferrer">'
            f"{frame}<span class=\"photo-caption\">{caption}</span></a>"
        )
    return (
        f'<figure class="photo reveal">{frame}'
        f'<figcaption class="photo-caption">{caption}</figcaption></figure>'
    )


def render_technologies(bundle, lang, assets) -> str:
    cards = []
    for index, item in enumerate(bundle["chapters"]["technologies"], start=1):
        wide = " tech-card-wide" if index == 1 else ""
        mark = logo_chip(assets, item.get("logo") or "")
        art = f'<div class="tech-art tech-mark">{mark}</div>' if mark else f'<div class="tech-art">{GLYPHS[item["id"]]}</div>'
        cards.append(
            f'<article class="tech-card reveal{wide}">'
            f"{art}"
            f'<p class="index">{index:02d}</p>'
            f'<h3>{e(text(item["name"], lang))}</h3>'
            f'<p>{e(text(item["line"], lang))}</p>'
            "</article>"
        )
    return (
        f'<section class="band" id="technologies"><div class="wrap">'
        f'{h2(CHAPTER["technologies"], ui(bundle, lang, "technologiesTitle"))}'
        f'<p class="lede reveal">{e(ui(bundle, lang, "technologiesLead"))}</p>'
        f'<div class="tech-grid">{"".join(cards)}</div>'
        "</div></section>"
    )


def render_world(bundle, lang, assets) -> str:
    primary = []
    secondary = []
    number = 0
    for stage in bundle["chapters"]["stages"]:
        number += 1
        item = resolve_stage(bundle, stage, lang)
        plate = (
            '<article class="plate reveal">'
            f'{logo_chip(assets, stage.get("logo") or "")}'
            f'<p class="plate-index" aria-hidden="true">{number:02d}</p>'
            f'<h3><a href="{e(item["url"])}" rel="noopener noreferrer">{e(item["name"])}</a></h3>'
            f'<p>{e(item["line"])}</p>'
            "</article>"
        )
        if stage["tier"] == "primary":
            primary.append(plate)
        else:
            secondary.append(plate)
    return (
        f'<section id="world"><div class="wrap">{h2(CHAPTER["world"], ui(bundle, lang, "worldTitle"))}'
        f'<p class="lede reveal">{e(ui(bundle, lang, "worldLead"))}</p>'
        f'<div class="plate-grid">{"".join(primary)}</div>'
        f'<h3>{e(ui(bundle, lang, "alsoOnRecord"))}</h3>'
        f'<div class="plate-grid plate-grid-secondary">{"".join(secondary)}</div>'
        "</div></section>"
    )


def render_home(bundle, lang, assets) -> str:
    profile = bundle["profile"]
    experience = bundle["experience"]
    creds = bundle["credentials"]
    posts = [p for p in bundle["posts"]["posts"] if p["kind"] == "own" and not p.get("imageOnly")]
    featured = [p for p in posts if p.get("featured")][:3] or posts[:3]
    grouped = []
    for company in experience["companies"]:
        company_roles = [r for r in experience["roles"] if r["companyId"] == company["id"]]
        role_bits = []
        for role in company_roles:
            highlight_items = role["highlights"].get(lang) or []
            highlight_html = ""
            if highlight_items:
                highlight_html = "<ul>" + "".join(f"<li>{e(item)}</li>" for item in highlight_items) + "</ul>"
            role_bits.append(
                '<article class="role">'
                f'<p class="when">{e(fmt_range(role["start"], role["end"], lang, ui(bundle, lang, "present")))}'
                f'<br>{e(text(role["location"], lang))} · {e(text(role["arrangement"], lang))}</p>'
                "<div>"
                f'<h4>{e(text(role["title"], lang))}</h4>'
                f'<p>{e(text(role["summary"], lang))}'
                + "".join(
                    f' <a href="{e(link["url"])}" rel="noopener noreferrer">{e(text(link["label"], lang))}</a>'
                    for link in (role.get("links") or [])
                )
                + "</p>"
                f"{highlight_html}"
                f'{stack_block(bundle, lang, role.get("technologies") or [])}'
                "</div></article>"
            )
        grouped.append(
            '<article class="company"><div class="company-head">'
            f'<h3><a href="{e(company["url"])}">{e(company["name"])}</a></h3>'
            f'<p>{e(text(company["span"], lang))}</p>'
            f'<p class="muted">{e(text(company["summary"], lang))}</p>'
            "</div>"
            + "".join(role_bits)
            + "</article>"
        )
    hero = render_hero(bundle, lang, assets)
    about = (
        f'<section id="about"><div class="wrap">{h2(CHAPTER["about"], ui(bundle, lang, "aboutTitle"))}'
        + paras(profile["about"][lang], lang)
        + tagline_list(bundle, lang)
        + "</div></section>"
    )
    project = creds["projects"][0]
    project_items = project["items"][lang]
    work_cards = []
    for item in project_items:
        head, _, tail = item.partition(": ")
        body = f"<p>{e(tail)}</p>" if tail else ""
        work_cards.append(
            '<article class="work-card reveal">'
            f"<h3>{e(head)}</h3>{body}"
            "</article>"
        )
    work = (
        f'<section class="band" id="work"><div class="wrap">{h2(CHAPTER["work"], ui(bundle, lang, "workTitle"))}'
        f'<h3>{e(text(project["name"], lang))}</h3>'
        f'<p class="muted">{e(fmt_range(project["start"], project["end"], lang, ui(bundle, lang, "present")))} · {e(project["associated"])}</p>'
        f'<p class="lede reveal">{e(text(project["summary"], lang))}</p>'
        f'<div class="work-grid">{"".join(work_cards)}</div>'
        "</div></section>"
    )
    honors = []
    for honor in creds["honors"]:
        when = fmt_month(honor.get("date"), lang)
        link = ""
        if honor.get("url"):
            label = ui(bundle, lang, "watch") if "youtube.com" in honor["url"] or "youtu.be" in honor["url"] else ui(bundle, lang, "read")
            link = f' <a href="{e(honor["url"])}">{e(label)}</a>'
        still = still_by_url(assets, honor.get("url") or "")
        thumb = f'{still_img(still, lazy=True)}'.replace("<img ", '<img class="thumb" ', 1) if still else ""
        row = " media-row" if still else ""
        honors.append(
            f'<article class="honor{row}">'
            f"{thumb}<div>"
            f'<h4>{e(text(honor["title"], lang))}</h4>'
            f'<p class="muted">{e(honor["issuer"])}{(" · " + e(when)) if when else ""}</p>'
            f'<p>{e(text(honor["summary"], lang))}{link}</p>'
            "</div></article>"
        )
    pubs = []
    for pub in creds["publications"]:
        when = fmt_day(pub.get("date"), lang)
        quote = f'<blockquote><p>{e(pub["quote"])}</p></blockquote>' if pub.get("quote") else ""
        summary = f'<p>{e(text(pub.get("summary"), lang))}</p>' if pub.get("summary") else ""
        pubs.append(
            '<article class="cover reveal">'
            f'<p class="mast">{e(pub["publisher"])}</p>'
            f'<h4><a href="{e(pub["url"])}">{e(text(pub["title"], lang))}</a></h4>'
            f'{f"<p class=\"muted\">{e(when)}</p>" if when else ""}'
            f"{quote}{summary}"
            "</article>"
        )
    speaking = (
        f'<section id="speaking"><div class="wrap">{h2(CHAPTER["speaking"], ui(bundle, lang, "speakingTitle"))}'
        f'<h3>{e(ui(bundle, lang, "honorsTitle"))}</h3>'
        + "".join(honors)
        + f'<h3>{e(ui(bundle, lang, "publicationsTitle"))}</h3>'
        + f'<div class="card-grid">{"".join(pubs)}</div>'
        + "</div></section>"
    )
    schools = []
    for school in creds["education"]:
        extra = ""
        if school.get("credentialUrl"):
            extra += f' <a href="{e(school["credentialUrl"])}">{e(ui(bundle, lang, "showCredential"))}</a>'
        for item in school.get("links") or []:
            extra += f' <a href="{e(item["url"])}">{e(item["label"])}</a>'
        schools.append(
            '<article class="school">'
            f'<h4>{e(school["school"])}</h4>'
            f'<p>{e(text(school["degree"], lang))}</p>'
            f'<p class="muted">{e(fmt_range(school["start"], school["end"], lang, ui(bundle, lang, "present")))}</p>'
            f'<p>{e(text(school["summary"], lang))}{extra}</p>'
            "</article>"
        )
    certs = []
    updated = bundle["site"]["updated"]
    for cert in creds["certifications"]:
        bits = [f'{e(ui(bundle, lang, "issued"))} {e(fmt_cert_date(cert.get("issued"), lang))}']
        if cert.get("expires"):
            key = "expired" if cert["expires"] < updated else "expires"
            bits.append(f'{e(ui(bundle, lang, key))} {e(fmt_cert_date(cert["expires"], lang))}')
        link = ""
        if cert.get("url"):
            link = f' <a href="{e(cert["url"])}">{e(ui(bundle, lang, "showCredential"))}</a>'
        summary = f'<p>{e(text(cert.get("summary"), lang))}</p>' if cert.get("summary") else ""
        certs.append(
            '<article class="cert">'
            f'<h4>{e(text(cert["name"], lang))}</h4>'
            f'<p class="muted">{e(cert["issuer"])} · {" · ".join(bits)}{link}</p>'
            f"{summary}"
            "</article>"
        )
    courses = "<ul>" + "".join(
        f'<li>{e(item["name"])} <span class="muted">({e(ui(bundle, lang, "associated"))} {e(item["associated"])})</span></li>'
        for item in creds["courses"]
    ) + "</ul>"
    featured_skills = chips(profile["featuredSkills"])
    all_skills = chips(profile["skills"])
    languages = "<ul>" + "".join(
        f'<li>{e(text(item["name"], lang))} — {e(text(item["level"], lang))}</li>'
        for item in profile["languages"]
    ) + "</ul>"
    rec = profile["recommendations"][0]
    recommendation = (
        f'<h3>{e(ui(bundle, lang, "recommendationsTitle"))}</h3>'
        '<figure class="quote">'
        f'<blockquote><p>{e(text(rec["quote"], lang))}</p></blockquote>'
        "<figcaption>"
        f'{e(ui(bundle, lang, "quoteBy"))} <a href="{e(rec["url"])}">{e(rec["name"])}</a>, {e(rec["title"])}. '
        f'<span class="muted">{e(text(rec["relationship"], lang))} · {e(fmt_day(rec["date"], lang))}</span>'
        "</figcaption></figure>"
    )
    background = (
        f'<section id="background"><div class="wrap">{h2(CHAPTER["background"], ui(bundle, lang, "navBackground"))}'
        f'<h3>{e(ui(bundle, lang, "educationTitle"))}</h3>'
        + "".join(schools)
        + f'<h3>{e(ui(bundle, lang, "certificationsTitle"))}</h3>'
        + "".join(certs)
        + f'<h3>{e(ui(bundle, lang, "coursesTitle"))}</h3>'
        + courses
        + f'<h3>{e(ui(bundle, lang, "skillsTitle"))}</h3>'
        f'<p class="eyebrow">{e(ui(bundle, lang, "featuredSkills"))}</p>'
        + featured_skills
        + f'<details><summary>{e(ui(bundle, lang, "allSkills"))}</summary>{all_skills}</details>'
        + f'<h3>{e(ui(bundle, lang, "languagesTitle"))}</h3>'
        + languages
        + recommendation
        + "</div></section>"
    )
    note_bits = []
    for post in featured:
        note_bits.append(
            '<article class="note">'
            f'<h3>{e(post["title"])}</h3>'
            f'<p class="muted"><time datetime="{e(post["date"])}">{e(fmt_day(post["date"], lang))}</time></p>'
            f'<p>{e(post["excerpt"])}</p>'
            f'<p><a href="{e(post["url"])}">{e(ui(bundle, lang, "onLinkedin"))}</a></p>'
            "</article>"
        )
    notes = (
        f'<section id="notes"><div class="wrap">{h2(CHAPTER["notes"], ui(bundle, lang, "featuredNotes"))}'
        + "".join(note_bits)
        + f'<p><a href="{e(bundle["site"]["locales"][lang]["notes"])}">{e(ui(bundle, lang, "allNotes"))}</a></p>'
        + "</div></section>"
    )
    experience_html = (
        f'<section id="experience"><div class="wrap">{h2(CHAPTER["experience"], ui(bundle, lang, "experienceTitle"))}'
        + "".join(grouped)
        + "</div></section>"
    )
    return (
        hero
        + about
        + render_igor(bundle, lang, assets)
        + render_technologies(bundle, lang, assets)
        + render_world(bundle, lang, assets)
        + experience_html
        + work
        + speaking
        + render_footprint(bundle, lang, assets)
        + background
        + notes
    )


def footprint_when(value, lang: str) -> str:
    if not value or value == "null":
        return ""
    if len(value) == 4:
        return value
    if len(value) == 7:
        return fmt_month(value, lang)
    return fmt_day(value, lang)


def outbound(url: str, label: str) -> str:
    return f'<a href="{e(url)}" rel="noopener noreferrer">{e(label)}</a>'


def render_footprint(bundle, lang: str, assets) -> str:
    data = bundle["footprint"]

    def links(items) -> str:
        if not items:
            return ""
        return "<p>" + " · ".join(
            outbound(item["url"], text(item["label"], lang)) for item in items
        ) + "</p>"

    press = []
    for item in data["press"]:
        when = footprint_when(item.get("date") or "", lang)
        press.append(
            '<article class="press-card reveal">'
            f'<p class="mast">{e(item["outlet"])}</p>'
            f'<h4>{outbound(item["url"], text(item["title"], lang))}</h4>'
            f'{f"<p class=\"muted\">{e(when)}</p>" if when else ""}'
            f'<p>{e(text(item["summary"], lang))}</p>'
            "</article>"
        )
    talks = []
    for item in data["talks"]:
        when = footprint_when(item.get("date") or "", lang)
        still = still_by_url(assets, item["url"])
        if still:
            media = (
                '<span class="still-media">'
                f'{still_img(still)}'
                '<span class="play" aria-hidden="true"></span>'
                "</span>"
            )
            facade = "video-facade has-still"
        else:
            media = '<span class="play" aria-hidden="true"></span>'
            facade = "video-facade"
        talks.append(
            '<article class="talk">'
            f'<a class="{facade}" href="{e(item["url"])}" rel="noopener noreferrer">'
            f"{media}<span>"
            f'<strong>{e(text(item["title"], lang))}</strong>'
            f'<span class="muted">{e(ui(bundle, lang, "watchYouTube"))}'
            f'{(" · " + e(when)) if when else ""}</span>'
            "</span></a>"
            f'<p>{e(text(item["summary"], lang))}</p>'
            f'{links(item.get("links") or [])}'
            "</article>"
        )
    credentials = []
    for item in data["credentials"]:
        badge = badge_for(assets, item["url"])
        if badge:
            mark = (
                f'<img class="badge-art" src="{e(badge["src"])}" width="{badge["w"]}" height="{badge["h"]}" '
                'alt="" loading="lazy" decoding="async">'
            )
        else:
            label = seal_label(text(item["title"], lang), item["issuer"])
            mark = f'<p class="seal-mark" aria-hidden="true">{e(label)}</p>'
        credentials.append(
            '<article class="seal">'
            f"{mark}"
            f'<h4>{outbound(item["url"], text(item["title"], lang))}</h4>'
            f'<p class="muted">{e(item["issuer"])}</p>'
            f'<p>{e(text(item["summary"], lang))}</p>'
            "</article>"
        )
    milestones = []
    for item in data["milestones"]:
        milestones.append(
            "<li>"
            f'<p class="when">{e(text(item["when"], lang))}</p>'
            "<h4>"
            f'{e(text(item["title"], lang))}'
            f'<span class="age">{e(text(item.get("age"), lang))}</span>'
            "</h4>"
            f'<p>{e(text(item["summary"], lang))}</p>'
            f'{links(item.get("links") or [])}'
            "</li>"
        )
    elsewhere = []
    for item in data["elsewhere"]:
        elsewhere.append(
            "<li>"
            f'{outbound(item["url"], text(item["title"], lang))}. '
            f'{e(text(item["summary"], lang))}'
            "</li>"
        )
    return (
        f'<section id="footprint"><div class="wrap">{h2(CHAPTER["footprint"], ui(bundle, lang, "navFootprint"))}'
        f'<p class="lede reveal">{e(ui(bundle, lang, "footprintLead"))}</p>'
        f'<h3 id="press">{e(ui(bundle, lang, "pressTitle"))}</h3>'
        + f'<div class="card-grid">{"".join(press)}</div>'
        + f'<h3 id="talks">{e(ui(bundle, lang, "talksTitle"))}</h3>'
        + "".join(talks)
        + f'<h3 id="credentials">{e(ui(bundle, lang, "credentialLinksTitle"))}</h3>'
        + f'<div class="seal-row">{"".join(credentials)}</div>'
        + f'<h3 id="milestones">{e(ui(bundle, lang, "milestonesTitle"))}</h3>'
        + f'<ol class="timeline">{"".join(milestones)}</ol>'
        + f'<h3>{e(ui(bundle, lang, "elsewhereTitle"))}</h3>'
        + f'<ul class="plain-list">{"".join(elsewhere)}</ul>'
        + "</div></section>"
    )


def render_notes(bundle, lang) -> str:
    def block(post) -> str:
        title = ui(bundle, lang, "imagePost") if post.get("imageOnly") else post["title"]
        excerpt = f'<p>{e(post["excerpt"])}</p>' if post.get("excerpt") else ""
        who = ""
        if post["kind"] == "repost":
            who = f'<p class="muted">{e(ui(bundle, lang, "repostOf"))} {e(post["author"])}'
            if post.get("authorTitle"):
                who += f', {e(post["authorTitle"])}'
            who += "</p>"
        return (
            '<article class="note">'
            f'<h3>{e(title)}</h3>'
            f'<p class="muted"><time datetime="{e(post["date"])}">{e(fmt_day(post["date"], lang))}</time></p>'
            f"{who}{excerpt}"
            f'<p><a href="{e(post["url"])}">{e(ui(bundle, lang, "onLinkedin"))}</a></p>'
            "</article>"
        )

    posts = bundle["posts"]["posts"]
    own = "".join(block(p) for p in posts if p["kind"] == "own")
    reposts = "".join(block(p) for p in posts if p["kind"] == "repost")
    return (
        '<div class="wrap" style="padding-top:2rem">'
        f'<h1>{e(ui(bundle, lang, "notesPageTitle"))}</h1>'
        f'<p class="lede">{e(ui(bundle, lang, "notesLead"))}</p>'
        f'<h2>{e(ui(bundle, lang, "ownPosts"))}</h2>{own}'
        f'<h2>{e(ui(bundle, lang, "reposts"))}</h2>{reposts}'
        "</div>"
    )


def render_privacy(bundle, lang) -> str:
    paragraphs = bundle["privacy"]["paragraphs"][lang]
    return (
        '<div class="wrap" style="padding-top:2rem">'
        f'<h1>{e(ui(bundle, lang, "privacyTitle"))}</h1>'
        f'<p class="lede">{e(ui(bundle, lang, "privacyLead"))}</p>'
        + "".join(f"<p>{e(p)}</p>" for p in paragraphs)
        + "</div>"
    )


def render_404(bundle, css, ga) -> str:
    host = bundle["site"]["canonicalHost"]
    page_url = host + "/404.html"
    title = "Page not found — Igor Agenor Piovezan"
    description = "That address is not on this site."
    bundle["_alts"] = {"en": "/404.html", "pt-BR": "/404.html"}
    assets = bundle["_assets"]
    document = head(
        bundle,
        lang="en",
        title=title,
        description=description,
        path="/404.html",
        robots="noindex, nofollow",
        css=css,
        ga=ga,
        assets=assets,
    )
    body = (
        '<body><div class="progress" aria-hidden="true"></div>'
        + header(bundle, "en", "404")
        + '<main id="content"><div class="wrap" style="padding-top:2rem">'
        + f'<h1>{e(ui(bundle, "en", "notFoundTitle"))}</h1>'
        + f'<p>{e(ui(bundle, "en", "notFoundBody"))}</p>'
        + '<p><a href="/">Home</a></p>'
        + f'<h2 lang="pt-BR">{e(ui(bundle, "pt-BR", "notFoundTitle"))}</h2>'
        + f'<p lang="pt-BR">{e(ui(bundle, "pt-BR", "notFoundBody"))}</p>'
        + '<p><a href="/pt-br/" hreflang="pt-BR" lang="pt-BR">Início</a></p>'
        + "</div></main>"
        + footer(bundle, "en")
        + consent(bundle, "en")
        + f'<script src="{e(assets["motion"])}"></script>'
        + f'<script src="{e(assets["analytics"])}" defer></script>'
        + "</body></html>\n"
    )
    return document + body


def page_title(bundle, page_id, lang) -> str:
    name = bundle["profile"]["name"]
    if page_id == "home":
        role = "CTO at Segware" if lang == "en" else "CTO na Segware"
        return f"{name} — {role}"
    if page_id == "notes":
        return f"{ui(bundle, lang, 'notesPageTitle')} — {name}"
    return f"{ui(bundle, lang, 'privacyTitle')} — {name}"


def page_description(bundle, page_id, lang) -> str:
    if page_id == "home":
        return text(bundle["profile"]["metaDescription"], lang)
    if page_id == "notes":
        return ui(bundle, lang, "notesLead")
    return ui(bundle, lang, "privacyLead")


def page_path(bundle, page_id, lang) -> str:
    locale = bundle["site"]["locales"][lang]
    return {"home": locale["home"], "notes": locale["notes"], "privacy": locale["privacy"]}[page_id]


def robots_txt(host: str, env: str) -> str:
    directive = "Allow" if env == "prod" else "Disallow"
    lines = [
        f"# {'Production' if env == 'prod' else 'Preview'} — canonical host {host}/",
        "# Search and AI crawlers.",
        "",
    ]
    for bot in BOTS:
        lines.append(f"User-agent: {bot}")
        lines.append(f"{directive}: /")
        lines.append("")
    if env == "prod":
        lines.append(f"Sitemap: {host}/sitemap.xml")
    return "\n".join(lines).rstrip() + "\n"


def sitemap(bundle, assets) -> str:
    host = bundle["site"]["canonicalHost"]
    updated = bundle["site"]["updated"]
    hero = absolute(host, assets["hero"])
    og = absolute(host, assets["og"])
    rows = []
    specs = (
        ("home", "monthly", "1.0", True),
        ("notes", "monthly", "0.6", False),
        ("privacy", "yearly", "0.3", False),
    )
    for page_id, freq, priority, images in specs:
        for lang in ("en", "pt-BR"):
            path = page_path(bundle, page_id, lang)
            loc = absolute(host, path)
            alternates = (
                '    <xhtml:link rel="alternate" hreflang="en" href="' + e(absolute(host, page_path(bundle, page_id, "en"))) + '"/>\n'
                '    <xhtml:link rel="alternate" hreflang="pt-BR" href="' + e(absolute(host, page_path(bundle, page_id, "pt-BR"))) + '"/>\n'
                '    <xhtml:link rel="alternate" hreflang="x-default" href="' + e(absolute(host, page_path(bundle, page_id, "en"))) + '"/>'
            )
            image_xml = ""
            if images:
                image_xml = (
                    "\n    <image:image>\n"
                    f"      <image:loc>{e(hero)}</image:loc>\n"
                    "      <image:title>Igor Agenor Piovezan</image:title>\n"
                    "    </image:image>\n"
                    "    <image:image>\n"
                    f"      <image:loc>{e(og)}</image:loc>\n"
                    "      <image:title>Igor Agenor Piovezan</image:title>\n"
                    "    </image:image>"
                )
            rows.append(
                "  <url>\n"
                f"    <loc>{e(loc)}</loc>\n"
                f"    <lastmod>{e(updated)}</lastmod>\n"
                f"    <changefreq>{freq}</changefreq>\n"
                f"    <priority>{priority}</priority>\n"
                f"{alternates}{image_xml}\n"
                "  </url>"
            )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )


def llms_txt(bundle) -> str:
    host = bundle["site"]["canonicalHost"]
    profile = bundle["profile"]
    return "\n".join([
        f"# {profile['name']}",
        "",
        f"> {text(profile['headline'], 'en')}",
        "",
        f"> {text(profile['headline'], 'pt-BR')}",
        "",
        f"Canonical site: {host}/",
        "Languages: English (primary), Portuguese (Brazil) at /pt-br/",
        "Location: São Paulo, Brazil",
        f"Role: {text(profile['jobTitle'], 'en')} at {profile['worksFor']['name']} ({profile['worksFor']['url']})",
        f"LinkedIn: {bundle['site']['linkedin']}",
        f"GitHub: {bundle['site']['github']}",
        "",
        "This site publishes his public career only. It has no phone number, no personal email, and no contact form.",
        "",
        "## Footprint",
        "",
        text(profile["headline"], "en"),
        "",
        f"Press, talks, credentials, and milestones: {host}/#footprint",
        f"Portuguese: {host}/pt-br/#footprint",
        "",
        *[
            f"- {item['outlet']}: {text(item['title'], 'en')} {item['url']}"
            for item in bundle["footprint"]["press"]
        ],
        "",
        "## Pages",
        "",
        f"- [Home]({host}/)",
        f"- [Home in Portuguese]({host}/pt-br/)",
        f"- [Notes]({host}/notes/)",
        f"- [Notas]({host}/pt-br/notas/)",
        f"- [Privacy]({host}/privacy/)",
        f"- [Privacidade]({host}/pt-br/privacidade/)",
        f"- [Full career summary]({host}/llms-full.txt)",
        "",
    ])


def llms_full(bundle) -> str:
    profile = bundle["profile"]
    lines = [
        f"# {profile['name']}",
        "",
        text(profile["headline"], "en"),
        "",
        "## About",
        "",
        *profile["about"]["en"],
        "",
        "## Experience",
        "",
    ]
    companies = {c["id"]: c for c in bundle["experience"]["companies"]}
    for role in bundle["experience"]["roles"]:
        company = companies[role["companyId"]]
        end = role["end"] or "present"
        lines.append(f"### {text(role['title'], 'en')} — {company['name']} ({role['start']} – {end})")
        lines.append("")
        lines.append(text(role["summary"], "en"))
        lines.append("")
        for item in role["highlights"].get("en") or []:
            lines.append(f"- {item}")
        if role.get("technologies"):
            lines.append("")
            lines.append("Technologies: " + "; ".join(role["technologies"]) + ".")
        lines.append("")
    lines.append("## Public footprint")
    lines.append("")
    lines.append("Milestones")
    lines.append("")
    for item in bundle["footprint"]["milestones"]:
        age = text(item.get("age"), "en")
        prefix = f"{text(item['when'], 'en')}, {age}" if age else text(item["when"], "en")
        lines.append(f"- {prefix}: {text(item['summary'], 'en')}")
        for link in item.get("links") or []:
            lines.append(f"  {text(link['label'], 'en')}: {link['url']}")
    lines.append("")
    lines.append("Press")
    lines.append("")
    for item in bundle["footprint"]["press"]:
        lines.append(f"- {item['outlet']}: {text(item['title'], 'en')} {item['url']}")
    lines.append("")
    lines.append("Talks and videos")
    lines.append("")
    for item in bundle["footprint"]["talks"]:
        lines.append(f"- {text(item['title'], 'en')} {item['url']}")
    lines.append("")
    lines.append("Credential links")
    lines.append("")
    for item in bundle["footprint"]["credentials"]:
        lines.append(f"- {text(item['title'], 'en')} — {item['issuer']}. {item['url']}")
    lines.append("")
    lines.append("## Education")
    lines.append("")
    for school in bundle["credentials"]["education"]:
        lines.append(f"- {school['school']}: {text(school['degree'], 'en')} ({school['start']} – {school['end']})")
    lines.append("")
    lines.append("## Certifications")
    lines.append("")
    for cert in bundle["credentials"]["certifications"]:
        url = f" {cert['url']}" if cert.get("url") else ""
        lines.append(f"- {text(cert['name'], 'en')} — {cert['issuer']}.{url}")
    lines.append("")
    lines.append("## Publications and talks")
    lines.append("")
    for honor in bundle["credentials"]["honors"]:
        url = f" {honor['url']}" if honor.get("url") else ""
        lines.append(f"- {text(honor['title'], 'en')} ({honor['issuer']}).{url}")
    for pub in bundle["credentials"]["publications"]:
        lines.append(f"- {text(pub['title'], 'en')} — {pub['publisher']}. {pub['url']}")
    lines.append("")
    lines.append("## Public LinkedIn posts")
    lines.append("")
    for post in bundle["posts"]["posts"]:
        kind = "Post" if post["kind"] == "own" else f"Repost of {post['author']}"
        lines.append(f"- {post['date']} — {kind}: {post['title']} {post['url']}")
    lines.append("")
    return "\n".join(lines)


def manifest(assets) -> str:
    data = {
        "name": "Igor Agenor Piovezan",
        "short_name": "Piovezan",
        "lang": "en",
        "start_url": "/",
        "display": "browser",
        "background_color": "#10211e",
        "theme_color": "#10211e",
        "icons": [
            {"src": assets["icon192"], "sizes": "192x192", "type": "image/png"},
            {"src": assets["icon512"], "sizes": "512x512", "type": "image/png"},
        ],
    }
    return json.dumps(data, indent=2) + "\n"


def build(env: str, out: Path) -> None:
    if env not in ("prod", "test"):
        raise SystemExit("env must be prod or test")
    bundle = {
        "site": load_json("site.json"),
        "profile": load_json("profile.json"),
        "experience": load_json("experience.json"),
        "credentials": load_json("credentials.json"),
        "footprint": load_json("footprint.json"),
        "ui": load_json("ui.json"),
        "posts": load_json("posts.json"),
        "privacy": load_json("privacy.json"),
        "chapters": load_json("chapters.json"),
    }
    validate_chapters(bundle["chapters"])
    measurement_id = bundle["site"]["ga4MeasurementId"]
    if out.exists():
        shutil.rmtree(out)
    assets_dir = out / "assets"
    assets_dir.mkdir(parents=True)
    media = json.loads((ASSETS / "media.json").read_text(encoding="utf-8"))
    assets = {
        "hero": write_hashed(ASSETS / media["hero"]["file"], assets_dir),
        "hero_w": media["hero"]["width"],
        "hero_h": media["hero"]["height"],
        "og": write_hashed(ASSETS / media["og"]["file"], assets_dir),
        "og_w": media["og"]["width"],
        "og_h": media["og"]["height"],
        "svg": write_hashed(ASSETS / "favicon.svg", assets_dir),
        "icon192": write_hashed(ASSETS / "icon-192.png", assets_dir),
        "icon512": write_hashed(ASSETS / "icon-512.png", assets_dir),
        "analytics": write_hashed(SRC / "analytics.js", assets_dir),
        "motion": write_hashed(SRC / "motion.js", assets_dir),
        "stills": {},
        "portrait": "",
        "photos": [],
        "logos": {},
        "badges": [],
    }
    for still in media.get("stills") or []:
        assets["stills"][still["id"]] = {
            "src": write_hashed(ASSETS / still["file"], assets_dir),
            "w": still["width"],
            "h": still["height"],
        }
    portrait = media.get("portrait") or None
    if isinstance(portrait, dict) and portrait.get("file"):
        assets["portrait"] = write_hashed(ASSETS / portrait["file"], assets_dir)
        assets["portrait_w"] = portrait["width"]
        assets["portrait_h"] = portrait["height"]
        assets["portrait_alt"] = portrait.get("alt") or {}
    for photo in media.get("photos") or []:
        assets["photos"].append({
            "src": write_hashed(ASSETS / photo["file"], assets_dir),
            "w": photo["width"],
            "h": photo["height"],
            "source": photo["source"],
            "caption": photo["caption"],
            "alt": photo.get("alt") or {},
            "focus": photo.get("focus") or "",
        })
    for logo in media.get("logos") or []:
        assets["logos"][logo["id"]] = {
            "src": write_hashed(ASSETS / logo["file"], assets_dir),
            "w": logo["width"],
            "h": logo["height"],
            "chip": logo.get("chip") or "light",
        }
    for badge in media.get("badges") or []:
        assets["badges"].append({
            "src": write_hashed(ASSETS / badge["file"], assets_dir),
            "w": badge["width"],
            "h": badge["height"],
            "match": badge.get("match") or "",
        })
    shutil.copyfile(ASSETS / "favicon.ico", out / "favicon.ico")
    shutil.copyfile(ASSETS / "apple-touch-icon.png", out / "apple-touch-icon.png")
    bundle["_assets"] = assets
    css = (SRC / "site.css").read_text(encoding="utf-8")
    ga = ga_script(measurement_id)
    robots = "index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"
    if env == "test":
        robots = "noindex, nofollow"
    for page in PAGES:
        bundle["_alts"] = {
            "en": page_path(bundle, page["id"], "en"),
            "pt-BR": page_path(bundle, page["id"], "pt-BR"),
        }
        lang = page["lang"]
        title = page_title(bundle, page["id"], lang)
        description = page_description(bundle, page["id"], lang)
        path = page_path(bundle, page["id"], lang)
        if page["id"] == "home":
            main = render_home(bundle, lang, assets)
        elif page["id"] == "notes":
            main = render_notes(bundle, lang)
        else:
            main = render_privacy(bundle, lang)
        document = head(
            bundle,
            lang=lang,
            title=title,
            description=description,
            path=path,
            robots=robots,
            css=css,
            ga=ga,
            assets=assets,
        )
        html_doc = (
            document
            + '<body>\n<div class="progress" aria-hidden="true"></div>\n'
            + header(bundle, lang, page["id"])
            + f'<main id="content">{main}</main>'
            + footer(bundle, lang)
            + consent(bundle, lang)
            + f'<script src="{e(assets["motion"])}"></script>'
            + f'<script src="{e(assets["analytics"])}" defer></script>'
            + "</body></html>\n"
        )
        target = out / page["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html_doc, encoding="utf-8")
    (out / "404.html").write_text(render_404(bundle, css, ga), encoding="utf-8")
    host = bundle["site"]["canonicalHost"]
    (out / "robots.txt").write_text(robots_txt(host, env), encoding="utf-8")
    (out / "sitemap.xml").write_text(sitemap(bundle, assets), encoding="utf-8")
    (out / "llms.txt").write_text(llms_txt(bundle), encoding="utf-8")
    (out / "llms-full.txt").write_text(llms_full(bundle), encoding="utf-8")
    (out / "site.webmanifest").write_text(manifest(assets), encoding="utf-8")
    key = indexnow_key(bundle["site"])
    (out / f"{key}.txt").write_text(key, encoding="utf-8")
    print(f"built {env} -> {out}")


def indexnow_key(site: dict) -> str:
    key = site.get("indexNow") or ""
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise SystemExit("content/site.json indexNow must be 32 lowercase hex characters")
    return key


def main() -> None:
    parser = argparse.ArgumentParser(description="Build igorpiovezan.com into a static folder")
    parser.add_argument("--env", choices=("prod", "test"), default="prod")
    parser.add_argument("--out", default=str(ROOT / "dist"))
    args = parser.parse_args()
    build(args.env, Path(args.out))


if __name__ == "__main__":
    main()
