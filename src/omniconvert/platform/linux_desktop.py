"""Install a user-local .desktop entry + icons so Ubuntu/GNOME shows the brand mark.

Wayland shells (Ubuntu dock) ignore Qt window icons. They look up Icon= via a
.desktop file named by QGuiApplication.desktopFileName / StartupWMClass.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from omniconvert.product import APP_NAME

log = logging.getLogger("omniconvert.linux_desktop")

_DESKTOP_ID = "justconvertit"
_ICON_SIZES = (48, 128, 256, 512)


def _resources_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources"


def _exec_line() -> str:
    """Command the dock / app menu should launch."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    # Dev / editable install: keep the same interpreter + module entry.
    return f'"{sys.executable}" -m omniconvert'


def _copy_icons(dest_root: Path) -> bool:
    """Copy hicolor PNGs (or the single app PNG) into ~/.local/share/icons."""
    res = _resources_dir()
    wrote = False
    for size in _ICON_SIZES:
        src = res / "hicolor" / f"{size}x{size}" / "apps" / f"{_DESKTOP_ID}.png"
        if not src.is_file():
            if size == 256:
                src = res / "omniconvert.png"
            else:
                continue
        if not src.is_file():
            continue
        dest = dest_root / "hicolor" / f"{size}x{size}" / "apps" / f"{_DESKTOP_ID}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        wrote = True
    return wrote


def _write_desktop_file(apps_dir: Path) -> Path:
    apps_dir.mkdir(parents=True, exist_ok=True)
    path = apps_dir / f"{_DESKTOP_ID}.desktop"
    body = "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            f"Name={APP_NAME}",
            "Comment=Offline-first local file converter",
            f"Exec={_exec_line()}",
            f"Icon={_DESKTOP_ID}",
            "Terminal=false",
            "Categories=Utility;Office;",
            "StartupNotify=false",
            f"StartupWMClass={_DESKTOP_ID}",
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o644)
    return path


def _refresh_caches(apps_dir: Path, icons_root: Path) -> None:
    try:
        subprocess.run(
            ["update-desktop-database", str(apps_dir)],
            check=False,
            timeout=5,
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(icons_root / "hicolor")],
            check=False,
            timeout=5,
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def ensure_linux_desktop_identity() -> None:
    """Register brand icons + .desktop for the current user (dev and frozen)."""
    if not sys.platform.startswith("linux"):
        return
    # Prefer XDG dirs; fall back to ~/.local/share.
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    apps_dir = data_home / "applications"
    icons_root = data_home / "icons"
    try:
        icons_ok = _copy_icons(icons_root)
        desktop = _write_desktop_file(apps_dir)
        if icons_ok:
            _refresh_caches(apps_dir, icons_root)
        log.info("Linux desktop entry ready: %s", desktop)
    except OSError:
        log.debug("Could not install user desktop entry", exc_info=True)
