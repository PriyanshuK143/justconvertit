"""Guards against zip bombs when inspecting untrusted Office archives."""

from __future__ import annotations

import zipfile
from pathlib import Path

from omniconvert.core.errors import ResourceLimitError, ValidationError
from omniconvert.core.limits import (
    MAX_ZIP_COMPRESSION_RATIO,
    MAX_ZIP_MEMBERS,
    MAX_ZIP_UNCOMPRESSED_BYTES,
)


def open_zip_safely(path: Path) -> zipfile.ZipFile:
    """Open a ZIP and reject archives with unsafe declared sizes/ratios."""
    try:
        zf = zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as exc:
        raise ValidationError(
            "File looks like a ZIP archive but is corrupt.",
            detail=str(exc),
        ) from exc

    try:
        infos = zf.infolist()
        if len(infos) > MAX_ZIP_MEMBERS:
            zf.close()
            raise ResourceLimitError(
                f"Archive has too many entries (max {MAX_ZIP_MEMBERS}).",
            )
        total_uncomp = 0
        for info in infos:
            # Skip directories.
            if info.is_dir():
                continue
            # Path traversal / absolute paths in member names.
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or name.startswith("../") or "/../" in f"/{name}/":
                zf.close()
                raise ValidationError("Archive contains an unsafe file path.")
            comp = max(info.compress_size, 1)
            uncomp = max(info.file_size, 0)
            if uncomp > MAX_ZIP_UNCOMPRESSED_BYTES:
                zf.close()
                raise ResourceLimitError(
                    "Archive entry is too large to open safely.",
                )
            ratio = uncomp / comp
            if ratio > MAX_ZIP_COMPRESSION_RATIO and uncomp > 10 * 1024 * 1024:
                zf.close()
                raise ResourceLimitError(
                    "Archive compression ratio looks unsafe (possible zip bomb).",
                )
            total_uncomp += uncomp
            if total_uncomp > MAX_ZIP_UNCOMPRESSED_BYTES:
                zf.close()
                raise ResourceLimitError(
                    "Archive uncompressed size exceeds the safe limit.",
                )
    except (ResourceLimitError, ValidationError):
        raise
    except Exception:
        zf.close()
        raise

    return zf
