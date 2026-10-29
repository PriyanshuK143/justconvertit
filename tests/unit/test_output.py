from __future__ import annotations

from pathlib import Path

import pytest

from omniconvert.core.errors import OutputError
from omniconvert.core.formats import FormatId
from omniconvert.core.output import (
    AtomicWriter,
    default_output_name,
    ensure_not_overwrite_source,
    unique_path,
    verify_output,
)


def test_unique_path_suffix(tmp_path: Path) -> None:
    (tmp_path / "a_converted.png").write_text("x", encoding="utf-8")
    p = unique_path(tmp_path, "a_converted.png")
    assert p.name == "a_converted (1).png"


def test_default_output_name() -> None:
    assert default_output_name(Path("photo.PNG"), FormatId.JPEG) == "photo_converted.jpg"


def test_refuse_overwrite_source(tmp_path: Path) -> None:
    f = tmp_path / "x.png"
    f.write_bytes(b"abc")
    with pytest.raises(OutputError):
        ensure_not_overwrite_source(f, f)


def test_atomic_writer(tmp_path: Path) -> None:
    dest = tmp_path / "out.bin"
    with AtomicWriter(dest) as tmp:
        Path(tmp).write_bytes(b"hello")
    assert dest.read_bytes() == b"hello"
    assert verify_output(dest) == 5


def test_atomic_writer_keeps_real_extension(tmp_path: Path) -> None:
    dest = tmp_path / "song.mp3"
    with AtomicWriter(dest) as tmp:
        assert Path(tmp).suffix == ".mp3"
        assert ".partial." in Path(tmp).name
        Path(tmp).write_bytes(b"ID3")
    assert dest.read_bytes() == b"ID3"


def test_atomic_writer_cleans_on_error(tmp_path: Path) -> None:
    dest = tmp_path / "out.bin"
    with pytest.raises(RuntimeError):
        with AtomicWriter(dest) as tmp:
            Path(tmp).write_bytes(b"partial")
            raise RuntimeError("boom")
    assert not dest.exists()
    assert list(tmp_path.glob(".*.partial.*")) == []
