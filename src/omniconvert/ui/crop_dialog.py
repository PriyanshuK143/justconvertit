"""Visual rectangle crop dialog for images."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from omniconvert.core.crop import min_crop_size, percents_from_pixel_box
from omniconvert.core.errors import ValidationError
from omniconvert.core.limits import MAX_CROP_PERCENT

_HANDLE = 8
_EDGE = 6


def _load_preview_pixmap(path: Path) -> tuple[QPixmap, int, int]:
    """Load image with EXIF orientation applied; return pixmap + natural size."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA")
            elif im.mode == "RGB":
                im = im.convert("RGBA")
            width, height = im.size
            data = im.tobytes("raw", "RGBA")
        qimg = QImage(data, width, height, QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(qimg), width, height
    except (UnidentifiedImageError, OSError, ValueError, MemoryError) as exc:
        raise ValidationError("Could not preview that image for cropping.") from exc


class CropCanvas(QWidget):
    """Image preview with a draggable/resizable crop rectangle."""

    selectionChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(360, 280)
        self.setMouseTracking(True)
        self._pixmap = QPixmap()
        self._img_w = 0
        self._img_h = 0
        # Selection in image-pixel coordinates (left, top, right, bottom).
        self._sel = QRect()
        self._drag_mode: str | None = None
        self._drag_origin = QPoint()
        self._sel_at_press = QRect()
        self._draw_start: QPoint | None = None

    def set_image(self, path: Path) -> None:
        self._pixmap, self._img_w, self._img_h = _load_preview_pixmap(path)
        inset_x = max(1, int(self._img_w * 0.10))
        inset_y = max(1, int(self._img_h * 0.10))
        self._sel = QRect(
            inset_x,
            inset_y,
            max(1, self._img_w - 2 * inset_x),
            max(1, self._img_h - 2 * inset_y),
        )
        self._clamp_selection()
        self.update()
        self.selectionChanged.emit()

    def image_size(self) -> tuple[int, int]:
        return self._img_w, self._img_h

    def selection_box(self) -> tuple[int, int, int, int]:
        r = self._sel.normalized()
        return r.left(), r.top(), r.right() + 1, r.bottom() + 1

    def _image_rect(self) -> QRectF:
        if self._pixmap.isNull() or self._img_w < 1:
            return QRectF()
        side = self.contentsRect()
        scale = min(side.width() / self._img_w, side.height() / self._img_h)
        w = self._img_w * scale
        h = self._img_h * scale
        x = side.x() + (side.width() - w) / 2
        y = side.y() + (side.height() - h) / 2
        return QRectF(x, y, w, h)

    def _to_widget(self, img_pt: QPoint) -> QPoint:
        ir = self._image_rect()
        if ir.isEmpty():
            return QPoint()
        x = ir.left() + img_pt.x() * ir.width() / self._img_w
        y = ir.top() + img_pt.y() * ir.height() / self._img_h
        return QPoint(int(round(x)), int(round(y)))

    def _to_image(self, widget_pt: QPoint) -> QPoint:
        ir = self._image_rect()
        if ir.isEmpty():
            return QPoint()
        x = (widget_pt.x() - ir.left()) * self._img_w / ir.width()
        y = (widget_pt.y() - ir.top()) * self._img_h / ir.height()
        return QPoint(
            max(0, min(self._img_w, int(round(x)))),
            max(0, min(self._img_h, int(round(y)))),
        )

    def _sel_widget_rect(self) -> QRect:
        r = self._sel.normalized()
        tl = self._to_widget(r.topLeft())
        # bottom-right of inclusive pixel box → exclusive edge in widget space
        br = self._to_widget(QPoint(r.right() + 1, r.bottom() + 1))
        return QRect(tl, br).normalized()

    def _clamp_selection(self) -> None:
        if self._img_w < 1 or self._img_h < 1:
            return
        min_w, min_h = min_crop_size(self._img_w, self._img_h)
        max_left = int(self._img_w * MAX_CROP_PERCENT / 100)
        max_top = int(self._img_h * MAX_CROP_PERCENT / 100)
        min_right = self._img_w - int(self._img_w * MAX_CROP_PERCENT / 100)
        min_bottom = self._img_h - int(self._img_h * MAX_CROP_PERCENT / 100)

        r = self._sel.normalized()
        # Inclusive QRect: right/bottom are last included pixels.
        left = max(0, min(r.left(), max_left))
        top = max(0, min(r.top(), max_top))
        right = max(min_right - 1, min(r.right(), self._img_w - 1))
        bottom = max(min_bottom - 1, min(r.bottom(), self._img_h - 1))
        if right - left + 1 < min_w:
            # Expand toward center to satisfy min size within margin caps.
            need = min_w - (right - left + 1)
            left = max(0, left - need // 2)
            right = left + min_w - 1
            if right > self._img_w - 1:
                right = self._img_w - 1
                left = max(0, right - min_w + 1)
            left = min(left, max_left)
            right = max(right, min_right - 1)
        if bottom - top + 1 < min_h:
            need = min_h - (bottom - top + 1)
            top = max(0, top - need // 2)
            bottom = top + min_h - 1
            if bottom > self._img_h - 1:
                bottom = self._img_h - 1
                top = max(0, bottom - min_h + 1)
            top = min(top, max_top)
            bottom = max(bottom, min_bottom - 1)
        self._sel = QRect(QPoint(left, top), QPoint(right, bottom))

    def _hit_test(self, pos: QPoint) -> str:
        wr = self._sel_widget_rect()
        if wr.isEmpty():
            return "draw"
        x, y = pos.x(), pos.y()
        left, top, right, bottom = wr.left(), wr.top(), wr.right(), wr.bottom()
        near_l = abs(x - left) <= _HANDLE
        near_r = abs(x - right) <= _HANDLE
        near_t = abs(y - top) <= _HANDLE
        near_b = abs(y - bottom) <= _HANDLE
        if near_l and near_t:
            return "nw"
        if near_r and near_t:
            return "ne"
        if near_l and near_b:
            return "sw"
        if near_r and near_b:
            return "se"
        if near_l and top - _EDGE <= y <= bottom + _EDGE:
            return "w"
        if near_r and top - _EDGE <= y <= bottom + _EDGE:
            return "e"
        if near_t and left - _EDGE <= x <= right + _EDGE:
            return "n"
        if near_b and left - _EDGE <= x <= right + _EDGE:
            return "s"
        if wr.adjusted(-2, -2, 2, 2).contains(pos):
            return "move"
        return "draw"

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or self._pixmap.isNull():
            return
        pos = event.position().toPoint()
        mode = self._hit_test(pos)
        self._drag_mode = mode
        self._drag_origin = self._to_image(pos)
        self._sel_at_press = QRect(self._sel)
        if mode == "draw":
            self._draw_start = self._drag_origin
            self._sel = QRect(self._drag_origin, self._drag_origin)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position().toPoint()
        if self._drag_mode is None:
            mode = self._hit_test(pos)
            cursors = {
                "nw": Qt.CursorShape.SizeFDiagCursor,
                "se": Qt.CursorShape.SizeFDiagCursor,
                "ne": Qt.CursorShape.SizeBDiagCursor,
                "sw": Qt.CursorShape.SizeBDiagCursor,
                "n": Qt.CursorShape.SizeVerCursor,
                "s": Qt.CursorShape.SizeVerCursor,
                "e": Qt.CursorShape.SizeHorCursor,
                "w": Qt.CursorShape.SizeHorCursor,
                "move": Qt.CursorShape.SizeAllCursor,
                "draw": Qt.CursorShape.CrossCursor,
            }
            self.setCursor(cursors.get(mode, Qt.CursorShape.ArrowCursor))
            return

        cur = self._to_image(pos)
        mode = self._drag_mode
        if mode == "draw" and self._draw_start is not None:
            self._sel = QRect(self._draw_start, cur).normalized()
            # QRect from two points uses inclusive corners; fine for clamp.
            self._clamp_selection()
            self.selectionChanged.emit()
            self.update()
            return

        r = QRect(self._sel_at_press)
        dx = cur.x() - self._drag_origin.x()
        dy = cur.y() - self._drag_origin.y()
        if mode == "move":
            r.translate(dx, dy)
        else:
            if "n" in mode:
                r.setTop(r.top() + dy)
            if "s" in mode:
                r.setBottom(r.bottom() + dy)
            if "w" in mode:
                r.setLeft(r.left() + dx)
            if "e" in mode:
                r.setRight(r.right() + dx)
        self._sel = r.normalized()
        self._clamp_selection()
        self.selectionChanged.emit()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_mode = None
            self._draw_start = None
            self._clamp_selection()
            self.selectionChanged.emit()
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        _ = event
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor("#0f172a"))

            ir = self._image_rect()
            if self._pixmap.isNull() or ir.isEmpty():
                return

            painter.drawPixmap(ir.toRect(), self._pixmap)

            sel = self._sel_widget_rect()
            # Dim outside selection.
            dim = QColor(15, 23, 42, 150)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dim)
            full = ir.toRect()
            if sel.isValid():
                # Top / mid-left / mid-right / bottom bands.
                painter.drawRect(
                    QRect(full.left(), full.top(), full.width(), max(0, sel.top() - full.top()))
                )
                painter.drawRect(
                    QRect(
                        full.left(),
                        sel.top(),
                        max(0, sel.left() - full.left()),
                        sel.height(),
                    )
                )
                painter.drawRect(
                    QRect(
                        sel.right() + 1,
                        sel.top(),
                        max(0, full.right() - sel.right()),
                        sel.height(),
                    )
                )
                painter.drawRect(
                    QRect(
                        full.left(),
                        sel.bottom() + 1,
                        full.width(),
                        max(0, full.bottom() - sel.bottom()),
                    )
                )

                pen = QPen(QColor("#38bdf8"), 2, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(sel.adjusted(0, 0, -1, -1))

                # Corner handles
                painter.setBrush(QColor("#ffffff"))
                painter.setPen(QPen(QColor("#0284c7"), 1.5))
                hs = _HANDLE
                for hx, hy in (
                    (sel.left(), sel.top()),
                    (sel.right(), sel.top()),
                    (sel.left(), sel.bottom()),
                    (sel.right(), sel.bottom()),
                ):
                    painter.drawRect(QRect(hx - hs // 2, hy - hs // 2, hs, hs))
        except Exception:  # noqa: BLE001
            import logging

            logging.getLogger("omniconvert.ui").exception("crop canvas paint failed")
        finally:
            painter.end()


class ImageCropDialog(QDialog):
    """Modal visual crop for image.crop — returns margin percent settings."""

    def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Crop image")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(640, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        hint = QLabel("Drag the rectangle to choose what to keep.")
        hint.setObjectName("mutedLabel")
        root.addWidget(hint)

        self.canvas = CropCanvas(self)
        root.addWidget(self.canvas, stretch=1)

        self._size_label = QLabel("")
        root.addWidget(self._size_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Crop")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._settings: dict[str, int] = {}
        self.canvas.selectionChanged.connect(self._update_size_label)
        self.canvas.set_image(image_path)
        if parent is not None:
            self.setStyleSheet(parent.styleSheet())

    def _update_size_label(self) -> None:
        left, top, right, bottom = self.canvas.selection_box()
        w, h = right - left, bottom - top
        iw, ih = self.canvas.image_size()
        self._size_label.setText(f"Selection {w}×{h} px  ·  image {iw}×{ih}")

    def _on_accept(self) -> None:
        try:
            box = self.canvas.selection_box()
            iw, ih = self.canvas.image_size()
            left_pct, right_pct, top_pct, bottom_pct = percents_from_pixel_box(
                iw, ih, box
            )
            self._settings = {
                "left_pct": left_pct,
                "right_pct": right_pct,
                "top_pct": top_pct,
                "bottom_pct": bottom_pct,
            }
        except ValidationError as exc:
            self._size_label.setText(str(exc))
            return
        self.accept()

    def values(self) -> dict[str, int]:
        return dict(self._settings)
