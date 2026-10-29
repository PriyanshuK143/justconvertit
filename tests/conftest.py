from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from omniconvert.core.registry import build_default_registry, reset_registry_for_tests
from omniconvert.services.dependencies import reset_dependency_service_for_tests


@pytest.fixture()
def registry():
    reset_registry_for_tests()
    reset_dependency_service_for_tests()
    return build_default_registry()


@pytest.fixture()
def fixtures_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def sample_png(tmp_path: Path) -> Path:
    path = tmp_path / "sample.png"
    img = Image.new("RGBA", (64, 48), (30, 144, 255, 128))
    img.save(path, format="PNG")
    return path


@pytest.fixture()
def sample_jpeg(tmp_path: Path) -> Path:
    path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (32, 32), (200, 40, 40))
    img.save(path, format="JPEG", quality=85)
    return path


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    path = tmp_path / "sample.csv"
    path.write_text("name,age\nAda,36\nBob,28\n", encoding="utf-8")
    return path


@pytest.fixture()
def sample_json(tmp_path: Path) -> Path:
    path = tmp_path / "sample.json"
    path.write_text('[{"name":"Ada","age":36},{"name":"Bob","age":28}]', encoding="utf-8")
    return path


@pytest.fixture()
def sample_txt(tmp_path: Path) -> Path:
    path = tmp_path / "sample.txt"
    path.write_text("Hello justconvertit\nLine 2\n", encoding="utf-8")
    return path
