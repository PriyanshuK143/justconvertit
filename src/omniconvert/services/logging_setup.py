"""Local diagnostic logging (no file contents)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from omniconvert.platform.paths import user_log_dir


def setup_logging(level: int = logging.INFO) -> Path | None:
    root = logging.getLogger("omniconvert")
    if root.handlers:
        return None

    root.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    sh.setLevel(logging.WARNING)
    root.addHandler(sh)

    log_path: Path | None = None
    try:
        log_dir = user_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "omniconvert.log"
        fh = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(formatter)
        root.addHandler(fh)
    except OSError:
        # Still run if the preferred log directory is not writable.
        root.warning("Could not create log file; continuing with console logging only.")

    return log_path
