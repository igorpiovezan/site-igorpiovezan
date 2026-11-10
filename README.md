# igorpiovezan.com

Personal site of Igor Agenor Piovezan. English is the primary language. Portuguese (Brazil) is at `/pt-br/`.

Career copy lives in `content/*.json`. Templates and the generator do not need to change when the biography is updated.

## Build

```bash
python3 scripts/build.py
```

That writes a production static site to `dist/`. Open it with:

```bash
python3 -m http.server -d dist 8000
```

The same build is `scripts/build-release.sh prod dist`.

A preview on any hostname other than `igorpiovezan.com` or `igorpiovezan.com.br` must use the test build. It sets `noindex, nofollow` and a `robots.txt` of `Disallow: /` for search and AI crawlers.

```bash
python3 scripts/build.py --env test --out dist
```

Do not publish the repository root. Publish the `dist/` folder only. `dist/` is gitignored.

## Staging

The long-lived preview branch is `staging/personal-brand`. Publish it to the staging host below. Do not treat that host as production, and do not merge the branch from the deploy step.

Staging host: <https://pure-sketch-dg8y.here.now/>
Slug: `pure-sketch-dg8y`

Publish only a **test** build to that slug. The test build sets `noindex, nofollow` and a `robots.txt` of `Disallow: /`. Do not publish a prod build there. Do not commit an API key, a claim token, or `.herenow/`.

From the private deploy repository, where the here.now key already lives:

```bash
git fetch origin staging/personal-brand
git checkout staging/personal-brand
python3 scripts/build.py --env test --out /tmp/igor-staging
publish.sh /tmp/igor-staging --slug pure-sketch-dg8y --client cursor
```

GA4 does not load on this host. The tag returns before `gtag.js` unless the hostname is `igorpiovezan.com` or `igorpiovezan.com.br`. Do not ping IndexNow for the staging host.

## here.now

Deploy runs from the private deploy repository. The API key stays there, in CI secrets, and is never committed.

From that repository, after this build:

```bash
python3 scripts/build.py --env test --out /tmp/igor-preview
publish.sh /tmp/igor-preview --slug "$HERENOW_TEST_SLUG" --client cursor

python3 scripts/build.py --env prod --out /tmp/igor-prod
publish.sh /tmp/igor-prod --slug "$HERENOW_PROD_SLUG" --client cursor
python3 scripts/indexnow_ping.py --sitemap /tmp/igor-prod/sitemap.xml
```

Run the IndexNow ping only after that production publish. It POSTs every URL in the sitemap to `https://api.indexnow.org/indexnow` for host `igorpiovezan.com`. The key file must already be live at `https://igorpiovezan.com/<key>.txt`. The key is the public `indexNow` field in `content/site.json`; the build writes it to `/<key>.txt`. Do not ping a preview host.

Production canonical host is `https://igorpiovezan.com`. Point the here.now primary domain at that host. `igorpiovezan.com.br` may serve the same files; every canonical, `og:url`, sitemap URL, and JSON-LD `@id` still uses `https://igorpiovezan.com`.

Binary files under `/assets/` are content-hashed because here.now caches that path for an hour.

## Portrait and stills

There is no photograph of Igor in the repository. The hero frame shows the public nameplate and says the frame is reserved. Talk stills are optimized copies of public YouTube thumbnails for videos already linked on the site. They are context for those videos, not a portrait session.

To drop in a photograph Igor supplies, add the file and point `portrait` at it in `assets/media.json`:

```json
"portrait": {
  "file": "portrait.webp",
  "width": 1200,
  "height": 1500,
  "alt": {
    "en": "Photograph of Igor Agenor Piovezan.",
    "pt-BR": "Fotografia de Igor Agenor Piovezan."
  }
}
```

Use a picture you have rights to. Do not generate a face. While `portrait` is null, `scripts/check_site.py` expects the reserved caption. Organization names in the visual chapter are context, not endorsements or partner logos.

`content/chapters.json` is the visual layer. Its lines restate facts already in the career files. Do not add a claim there that the biography does not already make.

## SEO

Production `robots.txt` allows search and AI crawlers, including `GrokBot`, `xAI-SearchBot`, and `GrokAgent`, and lists `https://igorpiovezan.com/sitemap.xml`. The sitemap lists only indexable HTML URLs, each with `en`, `pt-BR`, and `x-default`. `404.html` is `noindex` and is not in the sitemap. `llms.txt` and `llms-full.txt` summarize the public career. `llms.txt` points at `/#footprint` and lists the press links. JSON-LD is `Person` (with `sameAs` and `award`), `WebSite`, and, on the home pages, `["WebPage","ProfilePage"]` with `mainEntity` set to the person. Other pages stay `WebPage`. There is no `FAQPage`.

IndexNow uses a public 32-character hex key. `scripts/build.py` publishes it as `/<key>.txt`. After each production deploy, run `scripts/indexnow_ping.py` as shown above.

## Analytics

The GA4 measurement ID is the single field `ga4MeasurementId` in `content/site.json`.

Consent Mode v2 defaults `analytics_storage`, `ad_storage`, `ad_user_data`, and `ad_personalization` to denied. The choice is stored in `localStorage` under `igor_consent`. The Google tag loads only when the hostname, without `www`, is `igorpiovezan.com` or `igorpiovezan.com.br`.

## Checks

```bash
python3 scripts/scan_secrets.py
python3 scripts/check_site.py
```

CI runs those checks and gitleaks. Do not add a phone number, personal email, home address, or credential to this public repository.
