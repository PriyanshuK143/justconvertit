#!/usr/bin/env bash
# Build a standalone Ubuntu app folder + shareable tar.gz (no Python for end users).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate

VERSION="$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"
ARCH="$(uname -m)"
BUNDLE_NAME="justconvertit-${VERSION}-linux-${ARCH}"

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

APP_DIR="$ROOT/dist/justconvertit"
mkdir -p "$APP_DIR/icons"

# End-user installers live *inside* the shareable folder.
install -m 0755 packaging/linux/install.sh "$APP_DIR/install.sh"
install -m 0755 packaging/linux/uninstall.sh "$APP_DIR/uninstall.sh"
install -m 0644 packaging/linux/justconvertit.desktop "$APP_DIR/justconvertit.desktop"
install -m 0644 src/omniconvert/resources/omniconvert.png "$APP_DIR/icons/justconvertit.png"
cp -f docs/INSTALL.md "$APP_DIR/INSTALL.md"
cp -f docs/PRIVACY.md "$APP_DIR/PRIVACY.md"
cp -f docs/THIRD_PARTY_NOTICES.md "$APP_DIR/THIRD_PARTY_NOTICES.md"
cp -f LICENSE "$APP_DIR/LICENSE"

# Short readme at the top of the archive.
cat > "$APP_DIR/README.txt" <<EOF
justconvertit ${VERSION} (Linux)

Install (recommended):
  1. Keep this folder extracted
  2. Run:  ./install.sh
  3. Open "justconvertit" from your app menu

Default install location: ~/.local/opt/justconvertit
System-wide: sudo ./install.sh --system

Uninstall: ~/.local/opt/justconvertit/uninstall.sh
More help: INSTALL.md
EOF

# Shareable archive next to the folder.
mkdir -p "$ROOT/dist"
ARCHIVE="$ROOT/dist/${BUNDLE_NAME}.tar.gz"
CHECKSUM="$ROOT/dist/${BUNDLE_NAME}.sha256"
rm -f "$ARCHIVE" "$CHECKSUM"
tar -C "$ROOT/dist" -czf "$ARCHIVE" justconvertit
(
  cd "$ROOT/dist"
  sha256sum "$(basename "$ARCHIVE")" > "$(basename "$CHECKSUM")"
)

echo
echo "Built standalone app:  $APP_DIR/justconvertit"
echo "Shareable archive:     $ARCHIVE"
echo "Checksum:              $CHECKSUM"
echo
echo "End users: extract archive → ./install.sh → open from app menu"
