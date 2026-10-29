from __future__ import annotations

from pathlib import Path

from PIL import Image

from omniconvert.core.formats import FormatId
from omniconvert.core.registry import ConversionRegistry


def test_png_to_jpeg_flattens_alpha(registry: ConversionRegistry, sample_png: Path, tmp_path: Path) -> None:
    dest = tmp_path / "out.jpg"
    result = registry.convert(
        operation_id="image.png_to_jpeg",
        source=sample_png,
        destination=dest,
        settings={"jpeg_quality": 80, "transparency_background": "#00FF00"},
    )
    assert result.output_path.exists()
    with Image.open(result.output_path) as img:
        assert img.format == "JPEG"
        assert img.mode == "RGB"


def test_jpeg_to_png(registry: ConversionRegistry, sample_jpeg: Path, tmp_path: Path) -> None:
    dest = tmp_path / "out.png"
    registry.convert(
        operation_id="image.jpeg_to_png",
        source=sample_jpeg,
        destination=dest,
        settings={},
    )
    with Image.open(dest) as img:
        assert img.format == "PNG"


def test_png_to_webp_bmp_tiff(registry: ConversionRegistry, sample_png: Path, tmp_path: Path) -> None:
    for op_id, fmt in [
        ("image.png_to_webp", "WEBP"),
        ("image.png_to_bmp", "BMP"),
        ("image.png_to_tiff", "TIFF"),
    ]:
        dest = tmp_path / f"out.{fmt.lower()}"
        registry.convert(operation_id=op_id, source=sample_png, destination=dest, settings={})
        with Image.open(dest) as img:
            assert img.format == fmt


def test_image_to_pdf(registry: ConversionRegistry, sample_png: Path, tmp_path: Path) -> None:
    dest = tmp_path / "img.pdf"
    result = registry.convert(
        operation_id="pdf.image_png_to_pdf",
        source=sample_png,
        destination=dest,
        settings={},
    )
    assert result.bytes_written > 100
    assert dest.read_bytes()[:4] == b"%PDF"
