#!/usr/bin/env bash
# Install justconvertit for the current user (no Python required).
# Run from the extracted release folder:
#   ./install.sh
# Optional system-wide:
#   sudo ./install.sh --system
set -euo pipefail

APP_NAME="justconvertit"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: ./install.sh [--user|--system] [--prefix DIR]

  --user     Install under ~/.local (default; no sudo)
  --system   Install under /opt (requires root)
  --prefix   Custom install directory (app files go here)
EOF
}

MODE="user"
PREFIX=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --user) MODE="user"; shift ;;
    --system) MODE="system"; shift ;;
    --prefix)
      PREFIX="${2:-}"
      [[ -n "$PREFIX" ]] || { echo "--prefix needs a path" >&2; exit 1; }
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

BIN_SRC="$SCRIPT_DIR/$APP_NAME"
if [[ ! -x "$BIN_SRC" ]]; then
  echo "Missing executable: $BIN_SRC" >&2
  echo "Extract the full release archive and run install.sh from that folder." >&2
  exit 1
fi

if [[ -z "$PREFIX" ]]; then
  if [[ "$MODE" == "system" ]]; then
    PREFIX="/opt/$APP_NAME"
  else
    PREFIX="${HOME}/.local/opt/$APP_NAME"
  fi
fi

if [[ "$MODE" == "system" && "$(id -u)" -ne 0 ]]; then
  echo "System install needs root. Try: sudo ./install.sh --system" >&2
  exit 1
fi

if [[ "$MODE" == "user" ]]; then
  BIN_LINK_DIR="${HOME}/.local/bin"
  APP_DIR="${HOME}/.local/share/applications"
  ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
else
  BIN_LINK_DIR="/usr/local/bin"
  APP_DIR="/usr/share/applications"
  ICON_DIR="/usr/share/icons/hicolor/256x256/apps"
fi

echo "Installing $APP_NAME → $PREFIX"

mkdir -p "$PREFIX" "$BIN_LINK_DIR" "$APP_DIR" "$ICON_DIR"

# Sync app tree (binary + PyInstaller _internal + docs shipped next to it).
# Plain cp — avoids rsync hangs in some sandboxed/restricted environments.
mkdir -p "$PREFIX"
find "$PREFIX" -mindepth 1 -maxdepth 1 \
  ! -name 'uninstall.sh' \
  ! -name '.justconvertit-install.env' \
  ! -name 'icons' \
  -exec rm -rf {} +
shopt -s nullglob
for item in "$SCRIPT_DIR"/* "$SCRIPT_DIR"/.[!.]*; do
  [[ -e "$item" ]] || continue
  base="$(basename "$item")"
  case "$base" in
    .|..|install.sh|uninstall.sh|icons|.justconvertit-install.env) continue ;;
  esac
  case "$base" in
    *.desktop) continue ;;
  esac
  cp -a "$item" "$PREFIX/"
done
shopt -u nullglob

chmod +x "$PREFIX/$APP_NAME"

ICON_SRC=""
for candidate in \
  "$SCRIPT_DIR/icons/${APP_NAME}.png" \
  "$SCRIPT_DIR/${APP_NAME}.png" \
  "$SCRIPT_DIR/omniconvert.png"
do
  if [[ -f "$candidate" ]]; then
    ICON_SRC="$candidate"
    break
  fi
done

ICON_INSTALLED=""
if [[ -n "$ICON_SRC" ]]; then
  install -m 0644 "$ICON_SRC" "$ICON_DIR/${APP_NAME}.png"
  ICON_INSTALLED="$ICON_DIR/${APP_NAME}.png"
  mkdir -p "$PREFIX/icons"
  install -m 0644 "$ICON_SRC" "$PREFIX/icons/${APP_NAME}.png"
fi

DESKTOP_FILE="$APP_DIR/${APP_NAME}.desktop"
{
  echo "[Desktop Entry]"
  echo "Type=Application"
  echo "Name=justconvertit"
  echo "Comment=Offline-first local file converter"
  echo "Exec=${PREFIX}/${APP_NAME}"
  if [[ -n "$ICON_INSTALLED" ]]; then
    echo "Icon=${APP_NAME}"
  else
    echo "Icon=application-x-executable"
  fi
  echo "Terminal=false"
  echo "Categories=Utility;Office;"
  echo "StartupNotify=false"
  echo "StartupWMClass=justconvertit"
} > "$DESKTOP_FILE"
chmod 0644 "$DESKTOP_FILE"

ln -sfn "$PREFIX/$APP_NAME" "$BIN_LINK_DIR/$APP_NAME"

# Remember install layout for uninstall.sh (sourceable env, no Python needed).
cat > "$PREFIX/.justconvertit-install.env" <<EOF
PREFIX='$PREFIX'
MODE='$MODE'
BIN_LINK='$BIN_LINK_DIR/$APP_NAME'
DESKTOP='$DESKTOP_FILE'
ICON='${ICON_INSTALLED}'
EOF

if [[ -f "$SCRIPT_DIR/uninstall.sh" ]]; then
  install -m 0755 "$SCRIPT_DIR/uninstall.sh" "$PREFIX/uninstall.sh"
fi

# Best-effort desktop/icon cache refresh (never block install on these).
if command -v update-desktop-database >/dev/null 2>&1; then
  timeout 5 update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  timeout 5 gtk-update-icon-cache -f -t "$(dirname "$(dirname "$ICON_DIR")")" >/dev/null 2>&1 || true
fi

echo
echo "Installed."
echo "  Launch:  $APP_NAME"
echo "  Or open: justconvertit from your app menu"
echo "  Binary:  $PREFIX/$APP_NAME"
if [[ "$MODE" == "user" ]] && [[ ":$PATH:" != *":$BIN_LINK_DIR:"* ]]; then
  echo
  echo "Note: add $BIN_LINK_DIR to your PATH to run '$APP_NAME' from a terminal."
fi
echo
echo "Uninstall: $PREFIX/uninstall.sh"
