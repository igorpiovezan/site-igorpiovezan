#!/usr/bin/env bash
# Build a clean static directory. Publish that directory, never the repository root.
# Usage: scripts/build-release.sh prod|test [OUTDIR]
set -euo pipefail

ENV="${1:-prod}"
OUT="${2:-dist}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "$ENV" != "prod" && "$ENV" != "test" ]]; then
  echo "usage: $0 prod|test [OUTDIR]" >&2
  exit 2
fi

python3 "$ROOT/scripts/build.py" --env "$ENV" --out "$OUT"
