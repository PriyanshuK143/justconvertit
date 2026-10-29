from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from omniconvert.core.detection import detect_file
from omniconvert.core.errors import DetectionError, ValidationError
from omniconvert.core.formats import FormatId


def test_detect_png(sample_png: Path) -> None:
    d = detect_file(sample_png)
    assert d.format_id is FormatId.PNG


def test_detect_jpeg(sample_jpeg: Path) -> None:
    d = detect_file(sample_jpeg)
    assert d.format_id is FormatId.JPEG


def test_detect_csv(sample_csv: Path) -> None:
    assert detect_file(sample_csv).format_id is FormatId.CSV


def test_detect_json(sample_json: Path) -> None:
    assert detect_file(sample_json).format_id is FormatId.JSON


def test_misleading_extension(tmp_path: Path, sample_png: Path) -> None:
    fake = tmp_path / "not-really.jpg"
    fake.write_bytes(sample_png.read_bytes())
    with pytest.raises(DetectionError):
        detect_file(fake)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        detect_file(tmp_path / "nope.bin")


def test_corrupt_json_extension(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(DetectionError):
        detect_file(p)


def test_empty_txt(tmp_path: Path) -> None:
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    assert detect_file(p).format_id is FormatId.TXT
