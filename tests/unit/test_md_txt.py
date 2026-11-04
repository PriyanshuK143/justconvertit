from __future__ import annotations

from pathlib import Path

import pytest

from omniconvert.core.detection import detect_file
from omniconvert.core.errors import ValidationError
from omniconvert.core.formats import FormatId
from omniconvert.core.registry import ConversionRegistry


def test_detect_markdown(tmp_path: Path) -> None:
    p = tmp_path / "notes.md"
    p.write_text("# Hello\n\nSome **bold** text.\n", encoding="utf-8")
    assert detect_file(p).format_id is FormatId.MD


def test_md_to_txt_strips_markup(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = tmp_path / "doc.md"
    src.write_text(
        "# Title\n\nHello **world** and a [link](https://example.com).\n",
        encoding="utf-8",
    )
    out = tmp_path / "doc.txt"
    registry.convert(
        operation_id="text.md_to_txt",
        source=src,
        destination=out,
        settings={},
    )
    text = out.read_text(encoding="utf-8")
    assert "Title" in text
    assert "Hello world" in text
    assert "link" in text
    assert "**" not in text
    assert "[" not in text
    assert "https://example.com" not in text


def test_txt_to_md_preserves_text(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = tmp_path / "plain.txt"
    src.write_text("Line one\nLine two\n", encoding="utf-8")
    out = tmp_path / "plain.md"
    registry.convert(
        operation_id="text.txt_to_md",
        source=src,
        destination=out,
        settings={},
    )
    assert out.read_text(encoding="utf-8") == "Line one\nLine two\n"
    assert detect_file(out).format_id is FormatId.MD


def test_txt_to_md_normalizes_windows_crlf(
    registry: ConversionRegistry, tmp_path: Path
) -> None:
    """Windows text files often store CRLF; output must not become blank-line doubled."""
    src = tmp_path / "crlf.txt"
    src.write_bytes(b"Line one\r\nLine two\r\n")
    out = tmp_path / "crlf.md"
    registry.convert(
        operation_id="text.txt_to_md",
        source=src,
        destination=out,
        settings={},
    )
    assert out.read_bytes() == b"Line one\nLine two\n"


def test_md_ops_registered(registry: ConversionRegistry) -> None:
    ids = {op.operation_id for op in registry.available_operations_for(FormatId.MD)}
    assert "text.md_to_txt" in ids
    txt_ids = {op.operation_id for op in registry.available_operations_for(FormatId.TXT)}
    assert "text.txt_to_md" in txt_ids


def test_md_rejects_oversized(
    registry: ConversionRegistry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import omniconvert.converters.text_ops as text_ops

    monkeypatch.setattr(text_ops, "MAX_TEXT_BYTES", 64)
    src = tmp_path / "big.md"
    src.write_bytes(b"# " + b"x" * 80)
    with pytest.raises(ValidationError):
        registry.convert(
            operation_id="text.md_to_txt",
            source=src,
            destination=tmp_path / "out.txt",
            settings={},
        )
