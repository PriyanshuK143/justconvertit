from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QDialog

from omniconvert.ui.crop_dialog import ImageCropDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_image_crop_dialog_returns_margins(qapp, tmp_path: Path) -> None:
    src = tmp_path / "photo.png"
    Image.new("RGB", (200, 160), (40, 80, 120)).save(src)
    dlg = ImageCropDialog(src, None)
    assert dlg.canvas.image_size() == (200, 160)
    # Default inset selection should convert to non-zero margins.
    dlg._on_accept()
    assert dlg.result() == QDialog.DialogCode.Accepted
    values = dlg.values()
    assert values["left_pct"] > 0
    assert values["right_pct"] > 0
    assert values["top_pct"] > 0
    assert values["bottom_pct"] > 0
    dlg.close()
