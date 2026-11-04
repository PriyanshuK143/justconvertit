from __future__ import annotations

from pathlib import Path
import zipfile

import pytest
from PIL import Image

from omniconvert.core.detection import detect_file
from omniconvert.core.errors import DetectionError
from omniconvert.core.formats import FormatId


def test_detect_gif(tmp_path: Path) -> None:
    path = tmp_path / "anim.gif"
    frames = []
    for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255)):
        frames.append(Image.new("RGB", (16, 16), color))
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=50,
        loop=0,
        format="GIF",
    )
    assert detect_file(path).format_id is FormatId.GIF


def test_detect_image_frames_zip(tmp_path: Path) -> None:
    zpath = tmp_path / "frames.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for i in range(3):
            img = Image.new("RGB", (8, 8), (i * 40, 10, 20))
            buf = tmp_path / f"f{i}.png"
            img.save(buf)
            zf.write(buf, arcname=f"frame_{i:04d}.png")
    assert detect_file(zpath).format_id is FormatId.ZIP


def test_reject_non_image_zip(tmp_path: Path) -> None:
    zpath = tmp_path / "misc.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("readme.txt", "hello")
    with pytest.raises(DetectionError):
        detect_file(zpath)
