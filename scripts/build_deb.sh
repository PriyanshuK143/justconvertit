#!/usr/bin/env bash
# Wrap dist/justconvertit/ (PyInstaller) into an Ubuntu .deb installer.
# Prerequisite: bash scripts/build_linux.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x dist/justconvertit/justconvertit ]]; then
  echo "Missing dist/justconvertit/justconvertit — run: bash scripts/build_linux.sh" >&2
  exit 1
fi

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb not found. Install: sudo apt-get install -y dpkg-dev" >&2
  exit 1
fi

# shellcheck disable=SC1091
if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

VERSION="$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"
ARCH_RAW="$(uname -m)"
case "$ARCH_RAW" in
  x86_64|amd64) DEB_ARCH="amd64" ;;
  aarch64|arm64) DEB_ARCH="arm64" ;;
  *)
    echo "Unsupported architecture for .deb: $ARCH_RAW" >&2
    exit 1
    ;;
esac

PKG_NAME="justconvertit"
DEB_FILE="${PKG_NAME}_${VERSION}_${DEB_ARCH}.deb"
STAGE="$ROOT/build/deb/${PKG_NAME}"
rm -rf "$STAGE"
mkdir -p \
  "$STAGE/DEBIAN" \
  "$STAGE/opt/${PKG_NAME}" \
  "$STAGE/usr/bin" \
  "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/icons/hicolor/256x256/apps" \
  "$STAGE/usr/share/doc/${PKG_NAME}"

# Application payload
cp -a dist/justconvertit/. "$STAGE/opt/${PKG_NAME}/"
# Do not ship maintainer zip-install helpers inside the package tree.
rm -f \
  "$STAGE/opt/${PKG_NAME}/install.sh" \
  "$STAGE/opt/${PKG_NAME}/uninstall.sh" \
  "$STAGE/opt/${PKG_NAME}/justconvertit.desktop" \
  "$STAGE/opt/${PKG_NAME}/README.txt"
rm -rf "$STAGE/opt/${PKG_NAME}/icons"
chmod +x "$STAGE/opt/${PKG_NAME}/${PKG_NAME}"

# Menu entry + icon + PATH symlink
ICON_SRC="src/omniconvert/resources/omniconvert.png"
if [[ -f "$ICON_SRC" ]]; then
  install -m 0644 "$ICON_SRC" "$STAGE/usr/share/icons/hicolor/256x256/apps/${PKG_NAME}.png"
fi

cat > "$STAGE/usr/share/applications/${PKG_NAME}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=justconvertit
Comment=Offline-first local file converter
Exec=/opt/${PKG_NAME}/${PKG_NAME}
Icon=${PKG_NAME}
Terminal=false
Categories=Utility;Office;
StartupNotify=false
StartupWMClass=justconvertit
EOF
chmod 0644 "$STAGE/usr/share/applications/${PKG_NAME}.desktop"

ln -sfn "/opt/${PKG_NAME}/${PKG_NAME}" "$STAGE/usr/bin/${PKG_NAME}"

# Docs required by Debian policy (compressed changelog optional for 0.1)
install -m 0644 LICENSE "$STAGE/usr/share/doc/${PKG_NAME}/copyright"
install -m 0644 docs/PRIVACY.md "$STAGE/usr/share/doc/${PKG_NAME}/PRIVACY.md"
install -m 0644 docs/INSTALL.md "$STAGE/usr/share/doc/${PKG_NAME}/INSTALL.md"
if [[ -f docs/THIRD_PARTY_NOTICES.md ]]; then
  install -m 0644 docs/THIRD_PARTY_NOTICES.md "$STAGE/usr/share/doc/${PKG_NAME}/THIRD_PARTY_NOTICES.md"
fi

# Installed size in KiB
INSTALLED_SIZE="$(du -sk "$STAGE/opt" "$STAGE/usr" | awk '{s+=$1} END {print s}')"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${DEB_ARCH}
Maintainer: justconvertit Contributors <noreply@justconvertit.local>
Installed-Size: ${INSTALLED_SIZE}
Depends: libc6, libxcb-cursor0, libegl1, libxkbcommon0, libgl1, libglib2.0-0, libdbus-1-3, libfontconfig1, libfreetype6, libx11-6, libxcb1
Recommends: libreoffice, ffmpeg
Homepage: https://github.com/
Description: Offline-first local file converter with a radial-wheel UI
 justconvertit converts files on your machine. It does not upload documents,
 require accounts, or phone home. Optional LibreOffice and FFmpeg unlock
 high-fidelity Office↔PDF and audio conversions.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 0755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = remove ] || [ "$1" = purge ]; then
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
  fi
fi
exit 0
EOF
chmod 0755 "$STAGE/DEBIAN/postrm"

mkdir -p "$ROOT/dist"
OUT="$ROOT/dist/$DEB_FILE"
rm -f "$OUT" "$ROOT/dist/${PKG_NAME}_${VERSION}_${DEB_ARCH}.sha256"

if command -v fakeroot >/dev/null 2>&1; then
  fakeroot dpkg-deb --root-owner-group --build "$STAGE" "$OUT"
else
  dpkg-deb --root-owner-group --build "$STAGE" "$OUT"
fi

(
  cd "$ROOT/dist"
  sha256sum "$DEB_FILE" > "${PKG_NAME}_${VERSION}_${DEB_ARCH}.sha256"
)

echo
echo "Debian package: $OUT"
echo "Checksum:       $ROOT/dist/${PKG_NAME}_${VERSION}_${DEB_ARCH}.sha256"
dpkg-deb -I "$OUT" | sed -n '1,20p'
echo
echo "Install: sudo apt install ./dist/${DEB_FILE}"
