from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from omniconvert.core.detection import detect_file
from omniconvert.core.errors import ValidationError
from omniconvert.core.formats import FormatId
from omniconvert.core.registry import ConversionRegistry


def _make_pdf(path: Path, pages: int = 1) -> Path:
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path))
    for i in range(pages):
        c.drawString(72, 720, f"Page {i + 1}")
        c.showPage()
    c.save()
    return path


def test_detect_html(tmp_path: Path) -> None:
    p = tmp_path / "page.html"
    p.write_text("<!DOCTYPE html><html><body><p>Hi</p></body></html>", encoding="utf-8")
    assert detect_file(p).format_id is FormatId.HTML


def _sample_html(path: Path) -> Path:
    path.write_text(
        "<html><head><style>x{}</style><script>alert(1)</script></head>"
        "<body><h1>Title</h1><p>Hello <b>world</b> "
        '<a href="https://example.com">link</a></p>'
        "<ul><li>One</li><li>Two</li></ul></body></html>",
        encoding="utf-8",
    )
    return path


def test_html_to_txt(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _sample_html(tmp_path / "a.html")
    out = tmp_path / "a.txt"
    registry.convert(
        operation_id="text.html_to_txt",
        source=src,
        destination=out,
        settings={},
    )
    text = out.read_text(encoding="utf-8")
    assert "Title" in text
    assert "Hello" in text
    assert "world" in text
    assert "alert" not in text
    assert "<" not in text


def test_html_to_md(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _sample_html(tmp_path / "a.html")
    out = tmp_path / "a.md"
    registry.convert(
        operation_id="text.html_to_md",
        source=src,
        destination=out,
        settings={},
    )
    text = out.read_text(encoding="utf-8")
    assert "# Title" in text
    assert "**world**" in text
    assert "[link](https://example.com)" in text
    assert "- One" in text
    assert "alert" not in text


def test_html_to_pdf(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _sample_html(tmp_path / "a.html")
    out = tmp_path / "a.pdf"
    registry.convert(
        operation_id="text.html_to_pdf",
        source=src,
        destination=out,
        settings={},
    )
    assert out.read_bytes()[:4] == b"%PDF"


def test_html_to_docx(registry: ConversionRegistry, tmp_path: Path) -> None:
    from docx import Document

    src = _sample_html(tmp_path / "a.html")
    out = tmp_path / "a.docx"
    registry.convert(
        operation_id="text.html_to_docx",
        source=src,
        destination=out,
        settings={},
    )
    doc = Document(str(out))
    joined = "\n".join(p.text for p in doc.paragraphs)
    assert "Title" in joined
    assert "Hello" in joined


def test_pdf_rotate_90(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "in.pdf")
    out = tmp_path / "rot.pdf"
    registry.convert(
        operation_id="pdf.rotate",
        source=src,
        destination=out,
        settings={"angle": "90"},
    )
    page = PdfReader(str(out)).pages[0]
    assert int(page.rotation) % 360 == 90


def test_pdf_rotate_rejects_bad_angle(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "in.pdf")
    with pytest.raises(ValidationError):
        registry.convert(
            operation_id="pdf.rotate",
            source=src,
            destination=tmp_path / "o.pdf",
            settings={"angle": "45"},
        )


def test_pdf_compress(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "in.pdf", pages=2)
    out = tmp_path / "c.pdf"
    registry.convert(
        operation_id="pdf.compress",
        source=src,
        destination=out,
        settings={},
    )
    assert out.read_bytes()[:4] == b"%PDF"
    assert PdfReader(str(out)).pages  # readable


def test_image_crop(registry: ConversionRegistry, tmp_path: Path) -> None:
    src = tmp_path / "img.png"
    Image.new("RGB", (100, 80), (10, 20, 30)).save(src)
    out = tmp_path / "crop.png"
    registry.convert(
        operation_id="image.crop",
        source=src,
        destination=out,
        settings={"left_pct": 10, "right_pct": 10, "top_pct": 10, "bottom_pct": 10},
    )
    with Image.open(out) as img:
        assert img.size == (80, 64)


def test_image_crop_rejects_zero_margins(
    registry: ConversionRegistry, tmp_path: Path
) -> None:
    src = tmp_path / "img.png"
    Image.new("RGB", (50, 50), (1, 2, 3)).save(src)
    with pytest.raises(ValidationError):
        registry.convert(
            operation_id="image.crop",
            source=src,
            destination=tmp_path / "o.png",
            settings={"left_pct": 0, "right_pct": 0, "top_pct": 0, "bottom_pct": 0},
        )


def test_detect_svg(tmp_path: Path) -> None:
    p = tmp_path / "icon.svg"
    p.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
        '<rect width="10" height="10" fill="red"/></svg>',
        encoding="utf-8",
    )
    assert detect_file(p).format_id is FormatId.SVG
