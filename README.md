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

## here.now

Deploy runs from the private deploy repository. The API key stays there, in CI secrets, and is never committed.

From that repository, after this build:

```bash
python3 scripts/build.py --env test --out /tmp/igor-preview
publish.sh /tmp/igor-preview --slug "$HERENOW_TEST_SLUG" --client cursor

python3 scripts/build.py --env prod --out /tmp/igor-prod
publish.sh /tmp/igor-prod --slug "$HERENOW_PROD_SLUG" --client cursor
```

Production canonical host is `https://igorpiovezan.com`. Point the here.now primary domain at that host. `igorpiovezan.com.br` may serve the same files; every canonical, `og:url`, sitemap URL, and JSON-LD `@id` still uses `https://igorpiovezan.com`.

Binary files under `/assets/` are content-hashed because here.now caches that path for an hour.

## SEO

Production `robots.txt` allows search and AI crawlers and lists `https://igorpiovezan.com/sitemap.xml`. The sitemap lists only indexable HTML URLs, each with `en`, `pt-BR`, and `x-default`. `404.html` is `noindex` and is not in the sitemap. `llms.txt` and `llms-full.txt` summarize the public career. JSON-LD is `Person` (with `sameAs`), `WebSite`, and `WebPage`. There is no `FAQPage`.

## Analytics

The GA4 measurement ID is the single field `ga4MeasurementId` in `content/site.json`.

Consent Mode v2 defaults `analytics_storage`, `ad_storage`, `ad_user_data`, and `ad_personalization` to denied. The choice is stored in `localStorage` under `igor_consent`. The Google tag loads only when the hostname, without `www`, is `igorpiovezan.com` or `igorpiovezan.com.br`.

## Checks

```bash
python3 scripts/scan_secrets.py
python3 scripts/check_site.py
```

CI runs those checks and gitleaks. Do not add a phone number, personal email, home address, or credential to this public repository.
