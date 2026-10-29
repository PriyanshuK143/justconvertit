#!/usr/bin/env bash
# Smoke-test the packaged binary without outbound network.
# Usage: bash scripts/verify_offline.sh [path-to-justconvertit-binary]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="${1:-$ROOT/dist/justconvertit/justconvertit}"

if [[ ! -x "$BIN" ]]; then
  echo "Packaged binary not found: $BIN" >&2
  echo "Build first with: bash scripts/build_linux.sh" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# shellcheck disable=SC1091
if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  source "$ROOT/.venv/bin/activate"
fi

python - <<PY
from pathlib import Path
from PIL import Image
Image.new("RGB", (8, 8), (10, 20, 30)).save(Path("$TMP") / "in.png")
PY

OUT="$TMP/out.jpg"
CMD=( "$BIN" --smoke-convert image.png_to_jpeg "$TMP/in.png" "$OUT" )

if command -v unshare >/dev/null 2>&1 && unshare -n true 2>/dev/null; then
  echo "Running packaged smoke under unshare -n (no network)"
  unshare -n -- "${CMD[@]}"
else
  echo "unshare -n unavailable; running packaged smoke without network namespace"
  "${CMD[@]}"
fi

test -s "$OUT"
echo "verify_offline: packaged conversion OK -> $OUT ($(wc -c < "$OUT") bytes)"

# Policy unit tests (source tree) still apply to the same product flags.
cd "$ROOT"
bash scripts/test.sh tests/unit/test_offline_policy.py
echo "verify_offline: passed"
