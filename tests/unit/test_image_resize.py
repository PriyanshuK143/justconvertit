from __future__ import annotations

from pathlib import Path

from PIL import Image

from omniconvert.core.registry import ConversionRegistry


def test_image_resize_shrinks_long_edge(
    registry: ConversionRegistry, tmp_path: Path
) -> None:
    src = tmp_path / "wide.png"
    Image.new("RGB", (2000, 500), (10, 20, 30)).save(src)
    out = tmp_path / "out.png"
    registry.convert(
        operation_id="image.resize",
        source=src,
        destination=out,
        settings={"max_edge": 1000},
    )
    with Image.open(out) as img:
        assert img.size == (1000, 250)


def test_image_resize_leaves_small_images(
    registry: ConversionRegistry, sample_png: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out.png"
    registry.convert(
        operation_id="image.resize",
        source=sample_png,
        destination=out,
        settings={"max_edge": 1280},
    )
    with Image.open(sample_png) as src, Image.open(out) as img:
        assert img.size == src.size
