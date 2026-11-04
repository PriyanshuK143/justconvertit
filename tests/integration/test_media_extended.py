from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from omniconvert.converters.media_ffmpeg import FFmpegConverter
from omniconvert.core.formats import FormatId
from omniconvert.core.registry import ConversionRegistry


pytestmark = pytest.mark.skipif(
    not FFmpegConverter().is_available(),
    reason="FFmpeg not installed",
)


def _make_gif(path: Path) -> Path:
    frames = [Image.new("RGB", (32, 32), c) for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=80,
        loop=0,
        format="GIF",
    )
    return path


def test_gif_to_mp4_and_back(registry: ConversionRegistry, tmp_path: Path) -> None:
    gif = _make_gif(tmp_path / "a.gif")
    mp4 = tmp_path / "a.mp4"
    registry.convert(
        operation_id="media.gif_to_mp4",
        source=gif,
        destination=mp4,
        settings={},
    )
    assert mp4.stat().st_size > 100
    assert mp4.read_bytes()[4:8] == b"ftyp" or mp4.stat().st_size > 100

    back = tmp_path / "back.gif"
    registry.convert(
        operation_id="media.video_to_gif",
        source=mp4,
        destination=back,
        settings={"fps": "5", "max_seconds": "3"},
    )
    assert back.read_bytes()[:3] in {b"GIF"}
    assert detect_file_safe(back) is FormatId.GIF


def test_video_frames_roundtrip(registry: ConversionRegistry, tmp_path: Path) -> None:
    gif = _make_gif(tmp_path / "src.gif")
    mp4 = tmp_path / "src.mp4"
    registry.convert(
        operation_id="media.gif_to_mp4",
        source=gif,
        destination=mp4,
        settings={},
    )
    zpath = tmp_path / "frames.zip"
    registry.convert(
        operation_id="media.video_to_frames_zip",
        source=mp4,
        destination=zpath,
        settings={"fps": "5"},
    )
    with zipfile.ZipFile(zpath) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".png")]
        assert len(names) >= 1
        assert len(names) <= 300

    out = tmp_path / "from_frames.mp4"
    registry.convert(
        operation_id="media.frames_zip_to_mp4",
        source=zpath,
        destination=out,
        settings={"fps": "5"},
    )
    assert out.stat().st_size > 100


def test_video_to_frames_rejects_bad_fps(registry: ConversionRegistry, tmp_path: Path) -> None:
    from omniconvert.core.errors import ValidationError

    gif = _make_gif(tmp_path / "src.gif")
    mp4 = tmp_path / "src.mp4"
    registry.convert(
        operation_id="media.gif_to_mp4",
        source=gif,
        destination=mp4,
        settings={},
    )
    with pytest.raises(ValidationError):
        registry.convert(
            operation_id="media.video_to_frames_zip",
            source=mp4,
            destination=tmp_path / "bad.zip",
            settings={"fps": "999"},
        )


def detect_file_safe(path: Path) -> FormatId:
    from omniconvert.core.detection import detect_file

    return detect_file(path).format_id


def test_ffmpeg_ops_registered_when_available(registry: ConversionRegistry) -> None:
    assert shutil.which("ffmpeg") or FFmpegConverter().is_available()
    gif_ops = {o.operation_id for o in registry.available_operations_for(FormatId.GIF)}
    assert "media.gif_to_mp4" in gif_ops
    mp4_ops = {o.operation_id for o in registry.available_operations_for(FormatId.MP4)}
    assert "media.video_to_gif" in mp4_ops
    assert "media.video_to_frames_zip" in mp4_ops
    zip_ops = {o.operation_id for o in registry.available_operations_for(FormatId.ZIP)}
    assert "media.frames_zip_to_mp4" in zip_ops
