#!/usr/bin/env bash
# Remove a justconvertit install created by install.sh.
set -euo pipefail

APP_NAME="justconvertit"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

META=""
for candidate in \
  "$SCRIPT_DIR/.justconvertit-install.env" \
  "${HOME}/.local/opt/${APP_NAME}/.justconvertit-install.env" \
  "/opt/${APP_NAME}/.justconvertit-install.env"
do
  if [[ -f "$candidate" ]]; then
    META="$candidate"
    break
  fi
done

PREFIX=""
BIN_LINK=""
DESKTOP=""
ICON=""
MODE="user"

if [[ -n "$META" ]]; then
  # shellcheck disable=SC1090
  source "$META"
fi

if [[ -z "$PREFIX" ]]; then
  PREFIX="$(dirname "${META:-$SCRIPT_DIR/.x}")"
fi

if [[ -n "${BIN_LINK:-}" && -L "$BIN_LINK" ]]; then
  rm -f "$BIN_LINK"
fi
if [[ -n "${DESKTOP:-}" && -f "$DESKTOP" ]]; then
  rm -f "$DESKTOP"
fi
if [[ -n "${ICON:-}" && -f "$ICON" ]]; then
  rm -f "$ICON"
fi

rm -f "${HOME}/.local/share/applications/${APP_NAME}.desktop" \
      "/usr/share/applications/${APP_NAME}.desktop" 2>/dev/null || true
rm -f "${HOME}/.local/share/icons/hicolor/256x256/apps/${APP_NAME}.png" \
      "/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png" 2>/dev/null || true
rm -f "${HOME}/.local/bin/${APP_NAME}" "/usr/local/bin/${APP_NAME}" 2>/dev/null || true

if [[ -n "$PREFIX" && -d "$PREFIX" ]]; then
  case "$PREFIX" in
    "${HOME}/.local/opt/${APP_NAME}"|"/opt/${APP_NAME}")
      rm -rf "$PREFIX"
      ;;
    *)
      echo "Refusing to delete unexpected prefix: $PREFIX" >&2
      echo "Remove it manually after checking contents." >&2
      exit 1
      ;;
  esac
else
  echo "No install folder found to remove." >&2
  exit 1
fi

echo "justconvertit removed."
echo "Optional engines (LibreOffice / FFmpeg) were left installed."
