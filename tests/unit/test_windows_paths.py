"""Path / filesystem edge cases relevant to Windows and cross-platform use."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from omniconvert.core.errors import DetectionError, OutputError, UnsupportedConversionError
from omniconvert.core.output import unique_path
from omniconvert.core.registry import ConversionRegistry
from omniconvert.platform.paths import is_writable_dir, user_cache_dir, user_config_dir, user_temp_dir


def test_user_dirs_are_pathlib_under_home_or_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))
    cfg = user_config_dir()
    cache = user_cache_dir()
    assert isinstance(cfg, Path)
    assert isinstance(cache, Path)
    assert "justconvertit" in cfg.parts or "omniconvert" in cfg.parts


def test_unicode_and_spaces_in_path(registry: ConversionRegistry, tmp_path: Path) -> None:
    folder = tmp_path / "My Documents" / "测试 folder"
    folder.mkdir(parents=True)
    src = folder / "photo sample.png"
    Image.new("RGB", (16, 16), (12, 34, 56)).save(src)
    dest = folder / "photo sample_converted.jpg"
    result = registry.convert(
        operation_id="image.png_to_jpeg",
        source=src,
        destination=dest,
        settings={"jpeg_quality": 80, "transparency_background": "#FFFFFF"},
    )
    assert result.output_path.exists()
    assert " " in str(result.output_path)
    assert "测试" in str(result.output_path)


def test_unique_path_never_overwrites(tmp_path: Path) -> None:
    existing = tmp_path / "out.jpg"
    existing.write_bytes(b"x")
    nxt = unique_path(tmp_path, "out.jpg")
    assert nxt != existing
    assert not nxt.exists()
    assert nxt.name.startswith("out (")


def test_missing_input_file(registry: ConversionRegistry, tmp_path: Path) -> None:
    missing = tmp_path / "gone.png"
    with pytest.raises((FileNotFoundError, OSError, DetectionError, Exception)):
        registry.convert(
            operation_id="image.png_to_jpeg",
            source=missing,
            destination=tmp_path / "o.jpg",
            settings={},
        )


def test_corrupt_png_fails_gracefully(registry: ConversionRegistry, tmp_path: Path) -> None:
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not-a-png")
    with pytest.raises(Exception):
        registry.convert(
            operation_id="image.png_to_jpeg",
            source=bad,
            destination=tmp_path / "o.jpg",
            settings={"jpeg_quality": 80, "transparency_background": "#FFFFFF"},
        )


def test_unsupported_extension_detection(tmp_path: Path) -> None:
    from omniconvert.core.detection import detect_file

    weird = tmp_path / "file.xyz"
    weird.write_bytes(b"\x00\x01\x02\x03")
    with pytest.raises(DetectionError):
        detect_file(weird)


def test_temp_and_writable(tmp_path: Path) -> None:
    t = user_temp_dir()
    assert isinstance(t, Path)
    assert is_writable_dir(tmp_path)


def test_refuse_unknown_operation(registry: ConversionRegistry, sample_png: Path, tmp_path: Path) -> None:
    with pytest.raises(UnsupportedConversionError):
        registry.convert(
            operation_id="no.such.op",
            source=sample_png,
            destination=tmp_path / "x.bin",
            settings={},
        )


def test_output_error_on_bad_destination_parent(registry: ConversionRegistry, sample_png: Path, tmp_path: Path) -> None:
    # Parent that cannot be created as a directory (file in the way).
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    dest = blocker / "nested" / "out.jpg"
    with pytest.raises((OutputError, OSError, Exception)):
        registry.convert(
            operation_id="image.png_to_jpeg",
            source=sample_png,
            destination=dest,
            settings={"jpeg_quality": 80, "transparency_background": "#FFFFFF"},
        )
