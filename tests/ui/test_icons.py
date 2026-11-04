from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from omniconvert.core.formats import FormatId
from omniconvert.ui.icons import paint_convert_mark, paint_file_mark, paint_format_icon


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _paint_to_image(callback) -> QImage:
    img = QImage(QSize(64, 64), QImage.Format.Format_ARGB32)
    img.fill(QColor("#f8fafc"))
    painter = QPainter(img)
    callback(painter)
    painter.end()
    return img


def _has_non_bg(img: QImage, bg: QColor = QColor("#f8fafc")) -> bool:
    return any(
        img.pixelColor(x, y) != bg for x in range(8, 56) for y in range(8, 56)
    )


def test_hub_marks_draw_pixels(qapp) -> None:
    img1 = _paint_to_image(
        lambda p: paint_convert_mark(p, QRectF(8, 8, 48, 48), QColor("#2563eb"))
    )
    img2 = _paint_to_image(
        lambda p: paint_file_mark(p, QRectF(8, 8, 48, 48), QColor("#2563eb"))
    )
    assert _has_non_bg(img1)
    assert _has_non_bg(img2)


@pytest.mark.parametrize(
    "fmt",
    [
        FormatId.PNG,
        FormatId.JPEG,
        FormatId.WEBP,
        FormatId.BMP,
        FormatId.TIFF,
        FormatId.GIF,
        FormatId.SVG,
        FormatId.TXT,
        FormatId.MD,
        FormatId.HTML,
        FormatId.JSON,
        FormatId.CSV,
        FormatId.PDF,
        FormatId.DOCX,
        FormatId.PPTX,
        FormatId.XLSX,
        FormatId.MP3,
        FormatId.WAV,
        FormatId.MP4,
        FormatId.MKV,
        FormatId.ZIP,
    ],
)
def test_every_format_has_symbol(qapp, fmt: FormatId) -> None:
    img = _paint_to_image(
        lambda p: paint_format_icon(
            p,
            QRectF(8, 8, 48, 48),
            format_id=fmt,
            label=fmt.label,
            hot=False,
        )
    )
    assert _has_non_bg(img), f"No pixels drawn for {fmt}"
