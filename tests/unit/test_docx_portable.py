from __future__ import annotations

import io
import zipfile
from pathlib import Path

from docx import Document
from docx.shared import Inches
from PIL import Image
from pypdf import PdfReader

from omniconvert.core.errors import ValidationError
from omniconvert.core.registry import ConversionRegistry
import pytest


def _sample_docx(path: Path, *, with_image: bool = False) -> Path:
    doc = Document()
    doc.add_heading("Main Title", level=1)
    doc.add_paragraph("Intro paragraph.")
    doc.add_heading("Details", level=2)
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Name"
    table.rows[0].cells[1].text = "Value"
    table.rows[1].cells[0].text = "Alpha"
    table.rows[1].cells[1].text = "1"
    if with_image:
        buf = io.BytesIO()
        Image.new("RGB", (32, 24), (20, 120, 200)).save(buf, format="PNG")
        buf.seek(0)
        doc.add_picture(buf, width=Inches(1.0))
    doc.save(path)
    return path


def test_docx_to_md_has_headings_and_table(
    registry: ConversionRegistry, tmp_path: Path
) -> None:
    src = _sample_docx(tmp_path / "s.docx")
    out = tmp_path / "s.md"
    registry.convert(
        operation_id="office.docx_to_md",
        source=src,
        destination=out,
        settings={},
    )
    text = out.read_text(encoding="utf-8")
    assert "# Main Title" in text
    assert "## Details" in text
    assert "| Name | Value |" in text
    assert "| Alpha | 1 |" in text


def test_docx_to_txt_keeps_order(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _sample_docx(tmp_path / "s.docx")
    out = tmp_path / "s.txt"
    registry.convert(
        operation_id="office.docx_to_txt",
        source=src,
        destination=out,
        settings={},
    )
    text = out.read_text(encoding="utf-8")
    assert text.index("Main Title") < text.index("Intro paragraph")
    assert text.index("Intro paragraph") < text.index("Details")
    assert "Name\tValue" in text
    assert "Alpha\t1" in text


def test_docx_images_zip(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _sample_docx(tmp_path / "pic.docx", with_image=True)
    out = tmp_path / "pics.zip"
    result = registry.convert(
        operation_id="office.docx_images_zip",
        source=src,
        destination=out,
        settings={},
    )
    assert result.bytes_written > 0
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert names
        assert any(n.endswith(".png") for n in names)


def test_docx_images_zip_empty(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _sample_docx(tmp_path / "empty.docx", with_image=False)
    with pytest.raises(ValidationError, match="No images"):
        registry.convert(
            operation_id="office.docx_images_zip",
            source=src,
            destination=tmp_path / "x.zip",
            settings={},
        )


def test_docx_to_pdf_with_image(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _sample_docx(tmp_path / "pic.docx", with_image=True)
    out = tmp_path / "out.pdf"
    registry.convert(
        operation_id="office.docx_to_pdf_text",
        source=src,
        destination=out,
        settings={},
    )
    assert out.read_bytes()[:4] == b"%PDF"
    assert len(PdfReader(str(out)).pages) >= 1


def test_pdf_extract_images(registry: ConversionRegistry, tmp_path: Path) -> None:
    # Build a simple PDF that embeds a PNG via ReportLab
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    png = tmp_path / "dot.png"
    Image.new("RGB", (40, 30), (200, 40, 40)).save(png)
    pdf = tmp_path / "with_img.pdf"
    c = canvas.Canvas(str(pdf), pagesize=letter)
    c.drawImage(str(png), 72, 600, width=80, height=60)
    c.drawString(72, 580, "hello")
    c.save()

    out = tmp_path / "emb.zip"
    result = registry.convert(
        operation_id="pdf.extract_images",
        source=pdf,
        destination=out,
        settings={},
    )
    assert result.bytes_written > 0
    with zipfile.ZipFile(out) as zf:
        assert zf.namelist()
