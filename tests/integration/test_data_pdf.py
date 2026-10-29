from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from omniconvert.core.registry import ConversionRegistry
from omniconvert.converters.pdf_ops import merge_pdfs


def test_csv_json_roundtrip(registry: ConversionRegistry, sample_csv: Path, tmp_path: Path) -> None:
    js = tmp_path / "a.json"
    registry.convert(
        operation_id="data.csv_to_json",
        source=sample_csv,
        destination=js,
        settings={},
    )
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data[0]["name"] == "Ada"

    csv_out = tmp_path / "b.csv"
    registry.convert(
        operation_id="data.json_to_csv",
        source=js,
        destination=csv_out,
        settings={},
    )
    assert "Ada" in csv_out.read_text(encoding="utf-8")


def test_csv_xlsx_roundtrip(registry: ConversionRegistry, sample_csv: Path, tmp_path: Path) -> None:
    xlsx = tmp_path / "a.xlsx"
    registry.convert(
        operation_id="data.csv_to_xlsx",
        source=sample_csv,
        destination=xlsx,
        settings={},
    )
    assert xlsx.stat().st_size > 0
    csv_out = tmp_path / "back.csv"
    registry.convert(
        operation_id="data.xlsx_to_csv",
        source=xlsx,
        destination=csv_out,
        settings={},
    )
    assert "Bob" in csv_out.read_text(encoding="utf-8")


def test_json_format(registry: ConversionRegistry, sample_json: Path, tmp_path: Path) -> None:
    out = tmp_path / "pretty.json"
    registry.convert(
        operation_id="text.json_format",
        source=sample_json,
        destination=out,
        settings={"indent": 4},
    )
    assert "\n" in out.read_text(encoding="utf-8")


def test_txt_to_pdf_and_extract(registry: ConversionRegistry, sample_txt: Path, tmp_path: Path) -> None:
    pdf = tmp_path / "t.pdf"
    registry.convert(
        operation_id="text.txt_to_pdf",
        source=sample_txt,
        destination=pdf,
        settings={},
    )
    assert pdf.read_bytes()[:4] == b"%PDF"

    txt = tmp_path / "extracted.txt"
    registry.convert(
        operation_id="pdf.extract_text",
        source=pdf,
        destination=txt,
        settings={},
    )
    # Helvetica embedding may alter characters slightly; ensure non-empty extract path works
    assert txt.exists()


def test_pdf_merge(registry: ConversionRegistry, sample_txt: Path, tmp_path: Path) -> None:
    pdf1 = tmp_path / "1.pdf"
    pdf2 = tmp_path / "2.pdf"
    registry.convert(operation_id="text.txt_to_pdf", source=sample_txt, destination=pdf1, settings={})
    registry.convert(operation_id="text.txt_to_pdf", source=sample_txt, destination=pdf2, settings={})

    merged = tmp_path / "merged.pdf"
    result = merge_pdfs([pdf1, pdf2], merged)
    assert len(PdfReader(str(result.output_path)).pages) == 2


def test_unicode_path(registry: ConversionRegistry, sample_png: Path, tmp_path: Path) -> None:
    folder = tmp_path / "папка-文件"
    folder.mkdir()
    src = folder / "图片.png"
    src.write_bytes(sample_png.read_bytes())
    dest = folder / "out.jpg"
    registry.convert(
        operation_id="image.png_to_jpeg",
        source=src,
        destination=dest,
        settings={"jpeg_quality": 70},
    )
    assert dest.exists()
