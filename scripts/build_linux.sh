#!/usr/bin/env bash
# Build standalone Ubuntu app folder, then the end-user .deb installer.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Local dev uses .venv; GitHub Actions uses the runner Python already on PATH.
if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

VERSION="$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"

if [[ -f requirements-release.txt ]]; then
  pip install -r requirements-release.txt >/dev/null
fi
pip install -e . >/dev/null

# Avoid --collect-all PySide6 (pulls WebEngine and balloons the bundle).
pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name justconvertit \
  --paths src \
  --add-data "docs/THIRD_PARTY_NOTICES.md:docs" \
  --add-data "docs/PRIVACY.md:docs" \
  --add-data "LICENSE:." \
  --add-data "src/omniconvert/resources/omniconvert.png:omniconvert/resources" \
  --hidden-import omniconvert.converters.image_pillow \
  --hidden-import omniconvert.converters.tabular \
  --hidden-import omniconvert.converters.text_ops \
  --hidden-import omniconvert.converters.pdf_ops \
  --hidden-import omniconvert.converters.office_pure \
  --hidden-import omniconvert.converters.office_libreoffice \
  --hidden-import omniconvert.converters.media_ffmpeg \
  --hidden-import omniconvert.converters.svg_inkscape \
  --exclude-module PySide6.QtWebEngine \
  --exclude-module PySide6.QtWebEngineCore \
  --exclude-module PySide6.QtWebEngineWidgets \
  --exclude-module pytest \
  --exclude-module pygments \
  --exclude-module py \
  src/omniconvert/main.py

APP_DIR="$ROOT/dist/justconvertit"
cp -f docs/INSTALL.md "$APP_DIR/INSTALL.md"
cp -f docs/PRIVACY.md "$APP_DIR/PRIVACY.md"
cp -f docs/THIRD_PARTY_NOTICES.md "$APP_DIR/THIRD_PARTY_NOTICES.md"
cp -f LICENSE "$APP_DIR/LICENSE"

echo
echo "Built standalone app folder: $APP_DIR/justconvertit"
echo "Packaging .deb for end users…"
bash "$ROOT/scripts/build_deb.sh"
