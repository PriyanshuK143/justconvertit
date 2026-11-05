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


def test_png_to_webp(registry: ConversionRegistry, sample_png: Path, tmp_path: Path) -> None:
    dest = tmp_path / "out.webp"
    registry.convert(
        operation_id="image.png_to_webp",
        source=sample_png,
        destination=dest,
        settings={},
    )
    with Image.open(dest) as img:
        assert img.format == "WEBP"


def test_bmp_tiff_targets_removed(registry: ConversionRegistry) -> None:
    ids = {op.operation_id for op in registry.all_operations()}
    assert "image.png_to_bmp" not in ids
    assert "image.png_to_tiff" not in ids
    assert "image.jpeg_to_tiff" not in ids
    assert "image.resize" not in ids
    assert "image.remove_background" not in ids


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
