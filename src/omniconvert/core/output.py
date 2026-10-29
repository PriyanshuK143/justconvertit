"""Safe output path management."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from omniconvert.core.errors import OutputError
from omniconvert.core.formats import FormatId


def default_output_name(source: Path, target: FormatId) -> str:
    stem = source.stem or "converted"
    return f"{stem}_converted{target.extension}"


def unique_path(directory: Path, filename: str) -> Path:
    """Return a non-colliding path; never overwrites existing files."""
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    n = 1
    while True:
        candidate = directory / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1
        if n > 10_000:
            raise OutputError("Could not find a free output filename.")


def ensure_not_overwrite_source(source: Path, destination: Path) -> None:
    try:
        if source.resolve() == destination.resolve():
            raise OutputError("Refusing to overwrite the original file.")
    except OSError as exc:
        raise OutputError("Could not resolve output path.", detail=str(exc)) from exc


class AtomicWriter:
    """Write to a temp file in the destination directory, then replace."""

    def __init__(self, destination: Path) -> None:
        self.destination = destination
        self._tmp: tempfile.NamedTemporaryFile | None = None
        self.tmp_path: Path | None = None

    def __enter__(self) -> Path:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        # Keep the real extension (e.g. .mp3) so tools like FFmpeg can detect format.
        # Prefix marks the file as incomplete; do not append ".partial" after the suffix.
        self._tmp = tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=str(self.destination.parent),
            prefix=f".{self.destination.stem}.partial.",
            suffix=self.destination.suffix,
        )
        self.tmp_path = Path(self._tmp.name)
        self._tmp.close()
        return self.tmp_path

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.tmp_path is None:
            return
        if exc_type is not None:
            try:
                self.tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return
        try:
            os.replace(self.tmp_path, self.destination)
        except OSError as replace_exc:
            try:
                self.tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise OutputError(
                "Could not write the output file.",
                detail=str(replace_exc),
            ) from replace_exc


def verify_output(path: Path, *, min_bytes: int = 1) -> int:
    if not path.is_file():
        raise OutputError("Output file was not created.")
    size = path.stat().st_size
    if size < min_bytes:
        raise OutputError("Output file is empty or incomplete.")
    return size


def verify_output_magic(path: Path, *, expected_suffix: str) -> None:
    """Reject outputs whose leading bytes do not match the expected format."""
    suffix = expected_suffix.lower()
    try:
        with path.open("rb") as fh:
            header = fh.read(8)
    except OSError as exc:
        raise OutputError("Could not verify output file.", detail=str(exc)) from exc
    if suffix == ".pdf":
        if not header.startswith(b"%PDF"):
            raise OutputError("Output is not a valid PDF.")
    elif suffix in {".docx", ".xlsx", ".pptx", ".zip"}:
        if not header.startswith(b"PK"):
            raise OutputError("Output is not a valid Office/ZIP archive.")
    elif suffix in {".png"}:
        if not header.startswith(b"\x89PNG"):
            raise OutputError("Output is not a valid PNG.")
    elif suffix in {".jpg", ".jpeg"}:
        if not header.startswith(b"\xff\xd8"):
            raise OutputError("Output is not a valid JPEG.")


def discard_incomplete_output(path: Path | None) -> None:
    """Best-effort delete of a destination that must not be treated as success."""
    if path is None:
        return
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass
