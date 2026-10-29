#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
# Disable system-wide pytest plugins (common on ROS/Ubuntu desktops).
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
exec pytest -p pytestqt "$@"
