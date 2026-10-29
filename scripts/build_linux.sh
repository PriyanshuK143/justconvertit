#!/usr/bin/env bash
# Build a standalone Ubuntu folder tree (Python + deps bundled). Offline-ready.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate

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
  --exclude-module PySide6.QtWebEngine \
  --exclude-module PySide6.QtWebEngineCore \
  --exclude-module PySide6.QtWebEngineWidgets \
  --exclude-module pytest \
  --exclude-module pygments \
  --exclude-module py \
  src/omniconvert/main.py

# Ship launcher metadata next to the binary for manual /opt installs.
install -m 0644 packaging/linux/justconvertit.desktop dist/justconvertit/ || true
cp -f docs/INSTALL.md dist/justconvertit/INSTALL.md
cp -f docs/PRIVACY.md dist/justconvertit/PRIVACY.md

echo "Built dist/justconvertit/justconvertit (standalone; no network required at runtime)"
