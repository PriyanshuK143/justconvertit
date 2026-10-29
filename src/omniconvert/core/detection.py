"""Content-based file type detection."""

from __future__ import annotations

import json
import struct
from pathlib import Path

from omniconvert.core.errors import DetectionError, ResourceLimitError, ValidationError
from omniconvert.core.formats import DetectedFile, FormatId
from omniconvert.core.limits import MAX_INPUT_BYTES


def _read_header(path: Path, n: int = 64) -> bytes:
    with path.open("rb") as fh:
        return fh.read(n)


def _is_jpeg(header: bytes) -> bool:
    return len(header) >= 3 and header[0:2] == b"\xff\xd8"


def _is_png(header: bytes) -> bool:
    return header.startswith(b"\x89PNG\r\n\x1a\n")


def _is_webp(header: bytes) -> bool:
    return len(header) >= 12 and header[0:4] == b"RIFF" and header[8:12] == b"WEBP"


def _is_bmp(header: bytes) -> bool:
    return header.startswith(b"BM")


def _is_tiff(header: bytes) -> bool:
    return header.startswith(b"II*\x00") or header.startswith(b"MM\x00*")


def _is_pdf(header: bytes) -> bool:
    return header.startswith(b"%PDF")


def _is_zip_based(header: bytes) -> bool:
    return header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06")


def _sniff_zip_office(path: Path) -> FormatId | None:
    """Distinguish XLSX/DOCX/PPTX via zip member names without full extract."""
    from omniconvert.core.safe_zip import open_zip_safely

    try:
        with open_zip_safely(path) as zf:
            names = {n.replace("\\", "/") for n in zf.namelist()}
    except (ResourceLimitError, ValidationError) as exc:
        # Re-wrap detection-facing errors; keep resource limits as ResourceLimitError.
        if isinstance(exc, ResourceLimitError):
            raise
        raise DetectionError(exc.user_message, detail=exc.detail) from exc

    if "[Content_Types].xml" not in names:
        return None
    if any(n.startswith("xl/") for n in names):
        return FormatId.XLSX
    if any(n.startswith("word/") for n in names):
        return FormatId.DOCX
    if any(n.startswith("ppt/") for n in names):
        return FormatId.PPTX
    return None


def _looks_like_text(sample: bytes) -> bool:
    if not sample:
        return True
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            sample.decode("latin-1")
            return True
        except UnicodeDecodeError:
            return False


def _detect_textish(path: Path, sample: bytes) -> FormatId:
    text = sample.decode("utf-8", errors="replace").lstrip("\ufeff").strip()
    if not text:
        # Empty file — use extension hint if present.
        ext = path.suffix.lower()
        if ext == ".json":
            return FormatId.JSON
        if ext == ".csv":
            return FormatId.CSV
        return FormatId.TXT

    if text[0] in "{[":
        try:
            with path.open("r", encoding="utf-8") as fh:
                json.load(fh)
            return FormatId.JSON
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            # Might still be intended JSON with errors — fall through to ext.
            if path.suffix.lower() == ".json":
                raise DetectionError("File has a .json extension but is not valid JSON.")

    # Lightweight CSV heuristic: multiple comma/tab-separated lines.
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 1:
        first = lines[0]
        if ("," in first or "\t" in first) and path.suffix.lower() in {".csv", ".tsv", ""}:
            return FormatId.CSV
        if path.suffix.lower() == ".csv":
            return FormatId.CSV

    if path.suffix.lower() == ".json":
        raise DetectionError("File has a .json extension but is not valid JSON.")
    if path.suffix.lower() == ".csv":
        return FormatId.CSV
    return FormatId.TXT


_EXT_HINT: dict[str, FormatId] = {
    ".png": FormatId.PNG,
    ".jpg": FormatId.JPEG,
    ".jpeg": FormatId.JPEG,
    ".webp": FormatId.WEBP,
    ".bmp": FormatId.BMP,
    ".tif": FormatId.TIFF,
    ".tiff": FormatId.TIFF,
    ".txt": FormatId.TXT,
    ".json": FormatId.JSON,
    ".csv": FormatId.CSV,
    ".pdf": FormatId.PDF,
    ".xlsx": FormatId.XLSX,
    ".docx": FormatId.DOCX,
    ".pptx": FormatId.PPTX,
    ".mp3": FormatId.MP3,
    ".wav": FormatId.WAV,
    ".mp4": FormatId.MP4,
    ".mkv": FormatId.MKV,
}

_MIME = {
    FormatId.PNG: "image/png",
    FormatId.JPEG: "image/jpeg",
    FormatId.WEBP: "image/webp",
    FormatId.BMP: "image/bmp",
    FormatId.TIFF: "image/tiff",
    FormatId.TXT: "text/plain",
    FormatId.JSON: "application/json",
    FormatId.CSV: "text/csv",
    FormatId.PDF: "application/pdf",
    FormatId.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    FormatId.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    FormatId.PPTX: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    FormatId.MP3: "audio/mpeg",
    FormatId.WAV: "audio/wav",
    FormatId.MP4: "video/mp4",
    FormatId.MKV: "video/x-matroska",
    FormatId.UNKNOWN: "application/octet-stream",
}


def detect_file(path: Path | str) -> DetectedFile:
    """Detect file type from content, using extension only as a hint."""
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"File not found: {p.name}")
    if not p.is_file():
        raise ValidationError("Please choose a regular file.")

    try:
        size = p.stat().st_size
    except OSError as exc:
        raise ValidationError("Could not read file information.", detail=str(exc)) from exc

    if size > MAX_INPUT_BYTES:
        raise ResourceLimitError(
            f"File is too large (max {MAX_INPUT_BYTES // (1024 * 1024)} MiB).",
            detail=f"size={size}",
        )

    header = _read_header(p, 512)
    fmt: FormatId | None = None

    if _is_png(header):
        fmt = FormatId.PNG
    elif _is_jpeg(header):
        fmt = FormatId.JPEG
    elif _is_webp(header):
        fmt = FormatId.WEBP
    elif _is_bmp(header):
        fmt = FormatId.BMP
    elif _is_tiff(header):
        fmt = FormatId.TIFF
    elif _is_pdf(header):
        fmt = FormatId.PDF
    elif _is_zip_based(header):
        fmt = _sniff_zip_office(p)
        if fmt is None:
            raise DetectionError("ZIP archive detected, but it is not a supported Office format.")
    elif header.startswith(b"ID3") or (len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
        # Rough MP3 sniff — only claim if extension agrees; otherwise unknown.
        if p.suffix.lower() == ".mp3":
            fmt = FormatId.MP3
    elif header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WAVE":
        fmt = FormatId.WAV
    elif len(header) >= 8 and header[4:8] == b"ftyp":
        if p.suffix.lower() == ".mp4":
            fmt = FormatId.MP4
    elif header.startswith(b"\x1aE\xdf\xa3") and p.suffix.lower() == ".mkv":
        fmt = FormatId.MKV

    if fmt is None and _looks_like_text(header):
        fmt = _detect_textish(p, header if size <= 512 else _read_header(p, min(size, 8192)))

    if fmt is None:
        hint = _EXT_HINT.get(p.suffix.lower())
        if hint:
            raise DetectionError(
                f"Extension suggests {hint.label}, but file contents do not match.",
            )
        raise DetectionError("Unrecognized or unsupported file type.")

    # Mismatch warning as hard error for images/pdf when extension contradicts content.
    hint = _EXT_HINT.get(p.suffix.lower())
    if hint and hint != fmt and hint in {
        FormatId.PNG, FormatId.JPEG, FormatId.WEBP, FormatId.BMP, FormatId.TIFF, FormatId.PDF
    }:
        raise DetectionError(
            f"File extension suggests {hint.label}, but contents are {fmt.label}.",
        )

    return DetectedFile(
        path=str(p.resolve()),
        format_id=fmt,
        mime=_MIME.get(fmt, "application/octet-stream"),
        size_bytes=size,
        display_name=p.name,
    )


def format_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


# Silence unused import warning for struct if we add more sniffers later.
_ = struct
