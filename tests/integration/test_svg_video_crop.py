from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from omniconvert.converters.media_ffmpeg import FFmpegConverter
from omniconvert.converters.svg_inkscape import InkscapeConverter
from omniconvert.core.formats import FormatId
from omniconvert.core.registry import ConversionRegistry


def _make_gif(path: Path) -> Path:
    frames = [Image.new("RGB", (64, 48), c) for c in ((255, 0, 0), (0, 255, 0))]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=80, loop=0)
    return path


@pytest.mark.skipif(not FFmpegConverter().is_available(), reason="FFmpeg missing")
def test_video_crop(registry: ConversionRegistry, tmp_path: Path) -> None:
    gif = _make_gif(tmp_path / "a.gif")
    mp4 = tmp_path / "a.mp4"
    registry.convert(
        operation_id="media.gif_to_mp4",
        source=gif,
        destination=mp4,
        settings={},
    )
    out = tmp_path / "cropped.mp4"
    registry.convert(
        operation_id="media.video_crop",
        source=mp4,
        destination=out,
        settings={"left_pct": 10, "right_pct": 10, "top_pct": 10, "bottom_pct": 10},
    )
    assert out.stat().st_size > 50


@pytest.mark.skipif(not InkscapeConverter().is_available(), reason="Inkscape missing")
def test_svg_to_png_pdf(registry: ConversionRegistry, tmp_path: Path) -> None:
    svg = tmp_path / "i.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30">'
        '<rect width="40" height="30" fill="#2244aa"/></svg>',
        encoding="utf-8",
    )
    png = tmp_path / "i.png"
    registry.convert(
        operation_id="svg.to_png",
        source=svg,
        destination=png,
        settings={},
    )
    with Image.open(png) as img:
        assert img.size[0] >= 10
    pdf = tmp_path / "i.pdf"
    registry.convert(
        operation_id="svg.to_pdf",
        source=svg,
        destination=pdf,
        settings={},
    )
    assert pdf.read_bytes()[:4] == b"%PDF"


def test_svg_ops_hidden_without_inkscape(registry: ConversionRegistry) -> None:
    if InkscapeConverter().is_available():
        pytest.skip("Inkscape installed")
    ops = {o.operation_id for o in registry.available_operations_for(FormatId.SVG)}
    assert "svg.to_png" not in ops
    assert "svg.to_pdf" not in ops


def test_inkscape_hint_mentions_install() -> None:
    if shutil.which("inkscape"):
        pytest.skip("Inkscape on PATH")
    msg = InkscapeConverter().availability_message().lower()
    assert "inkscape" in msg
