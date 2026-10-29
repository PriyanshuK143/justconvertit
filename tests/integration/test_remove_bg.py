from __future__ import annotations

from pathlib import Path

from PIL import Image

from omniconvert.core.registry import ConversionRegistry


def test_remove_background_makes_corners_transparent(
    registry: ConversionRegistry, tmp_path: Path
) -> None:
    src = tmp_path / "solid.png"
    img = Image.new("RGB", (40, 40), (255, 255, 255))
    # Opaque subject in the middle
    for x in range(12, 28):
        for y in range(12, 28):
            img.putpixel((x, y), (20, 40, 200))
    img.save(src)

    dest = tmp_path / "cutout.png"
    result = registry.convert(
        operation_id="image.remove_background",
        source=src,
        destination=dest,
        settings={"bg_tolerance": 20},
    )
    assert result.output_path.exists()
    with Image.open(result.output_path) as out:
        assert out.mode == "RGBA"
        assert out.getpixel((0, 0))[3] == 0
        assert out.getpixel((20, 20))[3] == 255
