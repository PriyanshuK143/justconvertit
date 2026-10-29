"""Cross-platform user directories and path helpers via pathlib.

Never hardcode machine-specific paths. Safe for spaces, Unicode, and
Windows APPDATA / Linux XDG layouts.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def user_config_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "justconvertit"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "justconvertit"


def user_log_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "justconvertit" / "logs"
    xdg = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "state"
    return base / "justconvertit" / "logs"


def user_cache_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "justconvertit" / "cache"
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "justconvertit"


def user_temp_dir() -> Path:
    """Writable temp directory for conversion scratch files."""
    base = Path(tempfile.gettempdir()) / "justconvertit"
    try:
        base.mkdir(parents=True, exist_ok=True)
        return base
    except OSError:
        return Path(tempfile.gettempdir())


def user_engine_work_dir() -> Path:
    """Scratch dir for external engines (LibreOffice, etc.).

    Snap apps on Linux cannot write under hidden home paths (``~/.cache``).
    Use a visible ``~/justconvertit/work`` folder on Linux; Windows keeps
    LOCALAPPDATA.
    """
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        path = base / "justconvertit" / "work"
    else:
        path = Path.home() / "justconvertit" / "work"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_writable_dir(path: Path) -> bool:
    """Best-effort writability check (OneDrive / removable / restricted dirs)."""
    try:
        ensure_dir(path)
        probe = path / ".justconvertit_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def safe_expand(path_str: str) -> Path:
    """Expand user (~) without assuming a specific drive letter or home layout."""
    return Path(path_str).expanduser()
