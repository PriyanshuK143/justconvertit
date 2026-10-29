"""Security / resource-limit regressions for untrusted inputs."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from omniconvert.core.detection import detect_file
from omniconvert.core.errors import OutputError, ResourceLimitError, ValidationError
from omniconvert.core.output import discard_incomplete_output, verify_output_magic
from omniconvert.core.registry import ConversionRegistry
from omniconvert.core.safe_zip import open_zip_safely


def test_zip_bomb_ratio_rejected(tmp_path: Path) -> None:
    zeros = tmp_path / "zeros.xlsx"
    with zipfile.ZipFile(zeros, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        payload = b"\x00" * (12 * 1024 * 1024)
        zf.writestr("xl/sheet1.xml", payload)
        zf.writestr("[Content_Types].xml", b"<Types/>")
    with pytest.raises(ResourceLimitError):
        open_zip_safely(zeros)


def test_zip_path_traversal_rejected(tmp_path: Path) -> None:
    path = tmp_path / "evil.xlsx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("../evil.txt", b"x")
        zf.writestr("[Content_Types].xml", b"<Types/>")
    with pytest.raises(ValidationError):
        open_zip_safely(path)


def test_detect_rejects_zip_bomb_office(tmp_path: Path) -> None:
    zeros = tmp_path / "fake.docx"
    with zipfile.ZipFile(zeros, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", b"\x00" * (12 * 1024 * 1024))
        zf.writestr("[Content_Types].xml", b"<Types/>")
    with pytest.raises(ResourceLimitError):
        detect_file(zeros)


def test_verify_output_magic_pdf(tmp_path: Path) -> None:
    good = tmp_path / "a.pdf"
    good.write_bytes(b"%PDF-1.4\n")
    verify_output_magic(good, expected_suffix=".pdf")
    bad = tmp_path / "b.pdf"
    bad.write_bytes(b"not-a-pdf")
    with pytest.raises(OutputError):
        verify_output_magic(bad, expected_suffix=".pdf")


def test_discard_incomplete_output(tmp_path: Path) -> None:
    f = tmp_path / "partial.pdf"
    f.write_bytes(b"%PDF")
    discard_incomplete_output(f)
    assert not f.exists()
    discard_incomplete_output(None)


def test_nested_json_rejected(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = tmp_path / "nested.json"
    src.write_text('[{"a": 1, "b": {"c": 2}}]\n', encoding="utf-8")
    with pytest.raises(ValidationError):
        registry.convert(
            operation_id="data.json_to_csv",
            source=src,
            destination=tmp_path / "out.csv",
            settings={},
        )


def test_pages_zip_respects_page_cap(
    registry: ConversionRegistry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "omniconvert.converters.pdf_ops.MAX_PDF_RENDER_PAGES",
        2,
    )
    pdf = tmp_path / "many.pdf"
    c = canvas.Canvas(str(pdf))
    for i in range(3):
        c.drawString(72, 720, f"Page {i}")
        c.showPage()
    c.save()
    with pytest.raises(ResourceLimitError):
        registry.convert(
            operation_id="pdf.pages_to_zip",
            source=pdf,
            destination=tmp_path / "pages.zip",
            settings={},
        )


def test_oversized_input_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("omniconvert.core.detection.MAX_INPUT_BYTES", 100)
    huge = tmp_path / "big.png"
    huge.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 200)
    with pytest.raises(ResourceLimitError):
        detect_file(huge)
