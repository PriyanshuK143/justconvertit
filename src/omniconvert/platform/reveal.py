"""Open files / reveal folders in the system file manager."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_path(path: Path) -> None:
    path = Path(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def reveal_in_file_manager(path: Path) -> None:
    path = Path(path)
    if sys.platform.startswith("win"):
        subprocess.run(["explorer", "/select,", str(path)], check=False)
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)], check=False)
    else:
        # Prefer revealing parent folder on Linux (xdg-open on file opens it).
        target = path if path.is_dir() else path.parent
        subprocess.run(["xdg-open", str(target)], check=False)


def which(cmd: str) -> str | None:
    """Resolve a local executable on PATH. Never downloads or contacts a server."""
    from shutil import which as _which

    return _which(cmd)
