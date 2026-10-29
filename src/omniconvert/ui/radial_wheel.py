"""Circular gamepad wheel — single concentric disc, light theme."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget

from omniconvert.core.converter import ConversionOperation
from omniconvert.product import APP_NAME

_MAX_PADS = 8
# Fraction of each slice used by the pad (rest is a slim gap between sides).
_PAD_FILL = 0.92
# How far a hovered pad grows outward when it "pops".
_POP_SCALE = 0.10
# Radial air gap between hub rim and pad inner edge, as a fraction of outer radius.
_HUB_PAD_GAP = 0.045


@dataclass
class _Segment:
    operation: ConversionOperation
    start_angle_deg: float
    span_deg: float
    mid_angle_deg: float


def _point_on_circle(center: QPointF, radius: float, qt_angle_deg: float) -> QPointF:
    rad = math.radians(qt_angle_deg)
    return QPointF(
        center.x() + radius * math.cos(rad),
        center.y() - radius * math.sin(rad),
    )


class RadialWheel(QWidget):
    """Gamepad orb: empty hub opens a file; with a file, drag the puck to a pad."""

    formatSelected = Signal(str)
    fileDropped = Signal(str)
    openRequested = Signal()
    # Global mouse position while the user drags the orb across the desktop.
    windowDragMoved = Signal(QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self._operations: list[ConversionOperation] = []
        self._segments: list[_Segment] = []
        self._hover_index: int = -1
        self._selected_index: int = -1
        self._center_label = APP_NAME
        self._center_sub = ""
        self._has_file = False
        self._enabled = True

        self._puck_dragging = False
        self._puck_pos: QPointF | None = None
        self._press_on_hub = False
        self._press_pos = QPointF()
        self._drag_threshold = 10.0
        self._window_dragging = False
        self._window_drag_offset: QPoint | None = None
        self._transparent_bg = False
        self._banner = ""
        self._banner_color = QColor("#334155")
        # Per-pad pop amount 0..1, animated toward hover target.
        self._pop: list[float] = []
        self._pop_timer = QTimer(self)
        self._pop_timer.setInterval(16)
        self._pop_timer.timeout.connect(self._tick_pop)

        # Light theme palette — high-contrast labels on pads
        self._disc = QColor("#f3f4f6")
        self._disc_edge = QColor("#9ca3af")
        self._pad = QColor("#dbeafe")
        self._pad_hot = QColor("#2563eb")
        self._pad_line = QColor("#93c5fd")
        self._hub_fill = QColor("#ffffff")
        self._hub_rim = QColor("#64748b")
        self._hub_rim_active = QColor("#1d4ed8")
        self._text = QColor("#0f172a")
        self._muted = QColor("#334155")
        self._label_on_hot = QColor("#ffffff")
        self._pad_shadow = QColor(15, 23, 42, 55)

    def set_transparent_background(self, enabled: bool) -> None:
        self._transparent_bg = enabled
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, enabled)
        self.update()

    def set_banner(self, text: str, color: str = "#334155") -> None:
        """Optional status near the bottom rim. Empty string hides it."""
        self._banner = (text or "").strip()
        self._banner_color = QColor(color)
        self.update()

    def set_operations(self, operations: list[ConversionOperation]) -> None:
        self._operations = list(operations)[:_MAX_PADS]
        self._rebuild_segments()
        self._pop = [0.0] * len(self._segments)
        self._hover_index = -1
        self._selected_index = -1
        self._puck_dragging = False
        self._puck_pos = None
        if self._segments:
            self._pop_timer.start()
        else:
            self._pop_timer.stop()
        self.update()

    def set_center_text(self, title: str, subtitle: str = "") -> None:
        self._center_label = title
        self._center_sub = subtitle
        self.update()

    def set_has_file(self, has_file: bool) -> None:
        self._has_file = has_file
        self.update()

    def set_wheel_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.update()

    def selected_operation_id(self) -> str | None:
        if 0 <= self._selected_index < len(self._segments):
            return self._segments[self._selected_index].operation.operation_id
        return None

    def _rebuild_segments(self) -> None:
        """Even pads, first mid-angle at TOP (90°), then clockwise.

        Each pad uses only part of its slice so neighboring sides stay detached.
        """
        self._segments.clear()
        n = len(self._operations)
        if n == 0:
            return
        slot = 360.0 / n
        span = slot * _PAD_FILL
        for i, op in enumerate(self._operations):
            mid = (90.0 - i * slot) % 360.0  # clockwise from top
            start = (mid - span / 2.0) % 360.0
            self._segments.append(_Segment(op, start, span, mid))

    def _geometry(self) -> tuple[QPointF, float, float, float]:
        """center, pad_outer, pad_inner, hub — gap between hub and pads is intentional."""
        side = min(self.width(), self.height())
        # Leave room for pop-out growth past the nominal outer radius.
        outer = side / 2.0 - 14.0
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        if self._has_file and self._segments:
            hub = outer * 0.40
            # Modest gap so pads stay detached without a huge empty ring.
            pad_inner = hub + outer * _HUB_PAD_GAP
            pad_outer = outer
        else:
            hub = outer * 0.52
            pad_inner = hub
            pad_outer = outer
        return center, pad_outer, pad_inner, hub

    def _dist_from_center(self, pos: QPointF) -> float:
        c, _, _, _ = self._geometry()
        return math.hypot(pos.x() - c.x(), pos.y() - c.y())

    def _qt_angle(self, pos: QPointF) -> float:
        c, _, _, _ = self._geometry()
        dx = pos.x() - c.x()
        dy = pos.y() - c.y()
        return (math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0

    def _is_on_hub(self, pos: QPointF) -> bool:
        _, _, _, hub = self._geometry()
        return self._dist_from_center(pos) <= hub

    def _is_on_ring(self, pos: QPointF) -> bool:
        _, outer, inner, _ = self._geometry()
        d = self._dist_from_center(pos)
        # Include a little extra for popped pads.
        return inner <= d <= outer * (1.0 + _POP_SCALE)

    def _index_for_pos(self, pos: QPointF) -> int:
        if self._is_on_hub(pos):
            return -2
        if not self._segments or not self._is_on_ring(pos):
            return -1
        ang = self._qt_angle(pos)
        for i, seg in enumerate(self._segments):
            rel = (ang - seg.start_angle_deg) % 360.0
            if rel < seg.span_deg:
                return i
        return -1

    def _tick_pop(self) -> None:
        if not self._pop:
            self._pop_timer.stop()
            return
        changed = False
        for i in range(len(self._pop)):
            target = 1.0 if i == self._hover_index or i == self._selected_index else 0.0
            cur = self._pop[i]
            nxt = cur + (target - cur) * 0.28
            if abs(nxt - target) < 0.01:
                nxt = target
            if abs(nxt - cur) > 0.001:
                self._pop[i] = nxt
                changed = True
        if changed:
            self.update()
        elif self._hover_index < 0 and self._selected_index < 0 and all(p == 0 for p in self._pop):
            # Idle — keep timer cheap when nothing is popping.
            pass

    def paintEvent(self, event) -> None:  # noqa: N802
        _ = event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        c, outer, inner, hub = self._geometry()

        if self._transparent_bg:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        else:
            painter.fillRect(self.rect(), self._disc)

        show_pads = bool(self._has_file and self._segments)
        if show_pads:
            # Detached pads only — no continuous disc joining them to the hub.
            for i, seg in enumerate(self._segments):
                self._paint_pad(painter, c, outer, inner, seg, i)

        hub_rect = QRectF(c.x() - hub, c.y() - hub, hub * 2, hub * 2)
        painter.setBrush(self._hub_fill)
        rim = self._hub_rim_active if (self._has_file or self._press_on_hub) else self._hub_rim
        painter.setPen(QPen(rim, 2.5))
        painter.drawEllipse(hub_rect)

        if not self._puck_dragging:
            self._paint_hub_text(painter, hub_rect)

        if self._banner:
            self._paint_banner(painter, c, outer, inner)

        if self._puck_dragging and self._puck_pos is not None:
            painter.setPen(QPen(self._pad_hot, 2, Qt.PenStyle.DashLine))
            painter.drawLine(c, self._puck_pos)
            painter.setBrush(self._pad_hot)
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawEllipse(self._puck_pos, 16, 16)

        painter.end()

    def _paint_banner(
        self, painter: QPainter, c: QPointF, outer: float, inner: float
    ) -> None:
        font = QFont(self.font())
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        fm = QFontMetrics(font)
        max_w = int(outer * 1.35)
        text = fm.elidedText(self._banner, Qt.TextElideMode.ElideMiddle, max_w)
        # Sit in the air gap between hub and pads so it stays readable.
        _, _, _, hub = self._geometry()
        y = c.y() + (hub + inner) / 2.0
        rect = QRectF(c.x() - max_w / 2, y - 10, max_w, 20)
        painter.setPen(self._banner_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_hub_text(self, painter: QPainter, hub_rect: QRectF) -> None:
        single_line = not (self._has_file and self._segments)
        pad = 10 if single_line else 16
        avail = max(48, int(hub_rect.width() - pad * 2))
        sub = "drag to a pad" if (self._has_file and self._segments) else self._center_sub
        # Leave room for subtitle when present; otherwise center the title alone.
        if sub:
            name_rect = QRectF(
                hub_rect.left() + pad,
                hub_rect.center().y() - 28,
                hub_rect.width() - pad * 2,
                36,
            )
        else:
            name_rect = QRectF(
                hub_rect.left() + pad,
                hub_rect.center().y() - 18,
                hub_rect.width() - pad * 2,
                36,
            )

        font = QFont(self.font())
        font.setBold(True)
        label = self._center_label
        # Brand / empty hub: keep one line (never "OmniConv" / "ert").
        # Filenames may wrap to 2 lines after a file is loaded.
        point = 13 if single_line else 11
        lines: list[str] = [label]
        while point >= 7:
            font.setPointSize(point)
            fm = QFontMetrics(font)
            if single_line:
                if fm.horizontalAdvance(label) <= avail:
                    lines = [label]
                    break
            else:
                lines = self._wrap_filename(label, fm, avail, max_lines=2)
                block_h = fm.lineSpacing() * len(lines)
                widest = max((fm.horizontalAdvance(ln) for ln in lines), default=0)
                if block_h <= name_rect.height() and widest <= avail:
                    break
            point -= 1
        else:
            fm = QFontMetrics(font)
            lines = [fm.elidedText(label, Qt.TextElideMode.ElideMiddle, avail)]

        painter.setPen(self._text)
        painter.setFont(font)
        fm = QFontMetrics(font)
        total_h = fm.lineSpacing() * len(lines)
        y = name_rect.center().y() - total_h / 2
        for ln in lines:
            line_rect = QRectF(name_rect.left(), y, name_rect.width(), fm.lineSpacing())
            painter.drawText(line_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, ln)
            y += fm.lineSpacing()

        if sub:
            painter.setPen(self._muted)
            sub_font = QFont(self.font())
            sub_font.setPointSize(8)
            sub_font.setBold(False)
            painter.setFont(sub_font)
            sub_fm = QFontMetrics(sub_font)
            sub = sub_fm.elidedText(sub, Qt.TextElideMode.ElideMiddle, avail)
            sub_rect = QRectF(
                hub_rect.left() + pad,
                hub_rect.center().y() + 14,
                hub_rect.width() - pad * 2,
                16,
            )
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, sub)

    def _wrap_filename(self, text: str, fm: QFontMetrics, max_width: int, max_lines: int = 2) -> list[str]:
        """Wrap a filename onto up to max_lines; elide last line if still too long."""
        if fm.horizontalAdvance(text) <= max_width:
            return [text]

        # Prefer breaking on separators; otherwise mid-string.
        break_chars = (" ", "-", "_", ".", "/")
        lines: list[str] = []
        remaining = text
        while remaining and len(lines) < max_lines:
            if fm.horizontalAdvance(remaining) <= max_width:
                lines.append(remaining)
                return lines
            # Find longest prefix that fits.
            cut = len(remaining)
            for i in range(len(remaining), 0, -1):
                if fm.horizontalAdvance(remaining[:i]) <= max_width:
                    cut = i
                    break
            # Prefer breaking at a separator near the cut.
            best = -1
            window = remaining[:cut]
            for i, ch in enumerate(window):
                if ch in break_chars and i > cut * 0.35:
                    best = i + 1
            if best > 0 and len(lines) < max_lines - 1:
                cut = best
            chunk = remaining[:cut]
            remaining = remaining[cut:]
            if len(lines) == max_lines - 1 and remaining:
                lines.append(fm.elidedText(chunk + remaining, Qt.TextElideMode.ElideMiddle, max_width))
                return lines
            lines.append(chunk)
        return lines or [fm.elidedText(text, Qt.TextElideMode.ElideMiddle, max_width)]

    def _pad_path(
        self, c: QPointF, outer: float, inner: float, start: float, span: float
    ) -> QPainterPath:
        outer_rect = QRectF(c.x() - outer, c.y() - outer, outer * 2, outer * 2)
        inner_rect = QRectF(c.x() - inner, c.y() - inner, inner * 2, inner * 2)
        path = QPainterPath()
        # Ring segment without going through center (cleaner donut pads)
        path.arcMoveTo(outer_rect, start)
        path.arcTo(outer_rect, start, span)
        path.arcTo(inner_rect, start + span, -span)
        path.closeSubpath()
        return path

    def _paint_pad(
        self,
        painter: QPainter,
        c: QPointF,
        outer: float,
        inner: float,
        seg: _Segment,
        index: int,
    ) -> None:
        pop = self._pop[index] if index < len(self._pop) else 0.0
        hot = pop > 0.15
        # Grow outward (and slightly thicker) when dragged onto / hovered.
        grow = outer * _POP_SCALE * pop
        pad_outer = outer + grow
        pad_inner = max(inner - grow * 0.15, inner * 0.92)
        path = self._pad_path(c, pad_outer, pad_inner, seg.start_angle_deg, seg.span_deg)

        if pop > 0.05:
            # Soft shadow under the popped pad.
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._pad_shadow)
            shadow = self._pad_path(
                QPointF(c.x(), c.y() + 3 + 4 * pop),
                pad_outer,
                pad_inner,
                seg.start_angle_deg,
                seg.span_deg,
            )
            painter.drawPath(shadow)

        painter.setPen(QPen(self._pad_hot if hot else self._pad_line, 2.0 if hot else 1.5))
        fill = QColor(self._pad_hot if hot else self._pad)
        if hot:
            fill.setAlpha(int(200 + 55 * pop))
        painter.setBrush(fill)
        painter.drawPath(path)

        pt = _point_on_circle(c, (pad_outer + pad_inner) / 2.0, seg.mid_angle_deg)
        painter.setPen(self._label_on_hot if hot else self._text)
        font = QFont(self.font())
        font.setPointSize(13 if hot else 11)
        font.setBold(True)
        painter.setFont(font)
        label = seg.operation.segment_label
        painter.drawText(
            QRectF(pt.x() - 46, pt.y() - 14, 92, 28),
            Qt.AlignmentFlag.AlignCenter,
            label,
        )

    def _start_system_or_fallback_move(self, event: QMouseEvent) -> bool:
        """Begin moving the frameless window.

        On Wayland, ``QWidget.move()`` is ignored — the compositor must drive the
        move via ``QWindow.startSystemMove()``, which must run from a mouse-press
        handler. Falls back to manual move signals on X11.
        """
        win = self.window()
        if win is None:
            return False
        # Ensure a native window exists before asking the compositor to move it.
        _ = win.winId()
        handle = win.windowHandle()
        self._window_dragging = True
        self._press_on_hub = False
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        if handle is not None:
            try:
                if handle.startSystemMove():
                    return True
            except Exception:
                pass
        # X11 / fallback: track offset and emit positions from mouse-move.
        self._window_drag_offset = (
            event.globalPosition().toPoint() - win.frameGeometry().topLeft()
        )
        return True

    def _update_window_drag(self, event: QMouseEvent) -> None:
        if self._window_drag_offset is None:
            return
        top_left = event.globalPosition().toPoint() - self._window_drag_offset
        self.windowDragMoved.emit(top_left)

    def _hub_drag_zone(self, pos: QPointF) -> bool:
        """Outer band of the hub — press here to move (Wayland-safe).

        Wayland requires ``startSystemMove()`` from the mouse-press handler, so
        the move zone must be pressed directly (not after a drag threshold).
        """
        _, _, _, hub = self._geometry()
        d = self._dist_from_center(pos)
        return hub * 0.35 <= d <= hub + 1.0

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        idx = self._index_for_pos(pos)
        self._press_pos = QPointF(pos)
        self._press_on_hub = idx == -2
        self._window_dragging = False
        self._window_drag_offset = None

        # Outer rim (with a file loaded) — drag the whole orb.
        if self._has_file and self._segments and self._is_on_move_rim(pos):
            self._start_system_or_fallback_move(event)
            event.accept()
            return

        # Empty (or any) hub outer ring: move on press (required on Wayland).
        if idx == -2 and self._hub_drag_zone(pos) and not (
            self._has_file and self._segments and self._enabled
        ):
            self._start_system_or_fallback_move(event)
            event.accept()
            return

        # Empty hub: also allow Alt/Meta + press anywhere on hub to move.
        if (
            idx == -2
            and not (self._has_file and self._segments)
            and (event.modifiers() & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier))
        ):
            self._start_system_or_fallback_move(event)
            event.accept()
            return

        if idx == -2:
            if self._has_file and self._segments and self._enabled:
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            event.accept()
            return

        if idx >= 0 and self._enabled and self._segments:
            self._selected_index = idx
            self.update()
            self.formatSelected.emit(self._segments[idx].operation.operation_id)
            event.accept()
            return
        event.ignore()

    def _is_on_move_rim(self, pos: QPointF) -> bool:
        """Thin outer band used to reposition the orb after a file is loaded."""
        _, outer, inner, _ = self._geometry()
        d = self._dist_from_center(pos)
        return (outer - 22.0) <= d <= outer + 2.0

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position()

        if self._window_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            # Only used for X11 fallback (system move consumes the gesture).
            self._update_window_drag(event)
            event.accept()
            return

        if self._press_on_hub and (event.buttons() & Qt.MouseButton.LeftButton):
            dist = math.hypot(pos.x() - self._press_pos.x(), pos.y() - self._press_pos.y())
            if self._has_file and self._segments and self._enabled:
                if dist >= self._drag_threshold:
                    self._puck_dragging = True
                    self._puck_pos = QPointF(pos)
                    hover = self._index_for_pos(pos)
                    self._hover_index = hover if hover >= 0 else -1
                    self.update()
                event.accept()
                return
            # Empty hub center: if user drags, fall back to manual move (X11).
            if dist >= self._drag_threshold and self._window_drag_offset is None:
                win = self.window()
                if win is not None:
                    self._window_dragging = True
                    self._window_drag_offset = (
                        event.globalPosition().toPoint() - win.frameGeometry().topLeft()
                    )
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                self._update_window_drag(event)
                event.accept()
                return

        if self._puck_dragging:
            self._puck_pos = QPointF(pos)
            hover = self._index_for_pos(pos)
            self._hover_index = hover if hover >= 0 else -1
            self.update()
            event.accept()
            return

        idx = self._index_for_pos(pos)
        hover = idx if idx >= 0 else -1
        if hover != self._hover_index:
            self._hover_index = hover
            self.update()
        if (self._has_file and self._is_on_move_rim(pos)) or (
            idx == -2 and self._hub_drag_zone(pos) and not (self._has_file and self._segments)
        ):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        elif idx == -2 or idx >= 0:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()

        if self._window_dragging:
            self._window_dragging = False
            self._window_drag_offset = None
            self._press_on_hub = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if self._puck_dragging:
            idx = self._index_for_pos(pos)
            self._puck_dragging = False
            self._puck_pos = None
            self._press_on_hub = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if idx >= 0 and self._enabled:
                self._selected_index = idx
                self.formatSelected.emit(self._segments[idx].operation.operation_id)
            self.update()
            event.accept()
            return

        if self._press_on_hub:
            self._press_on_hub = False
            self.openRequested.emit()
            event.accept()
            return

        self._press_on_hub = False

    def leaveEvent(self, event) -> None:  # noqa: N802
        _ = event
        if not self._puck_dragging:
            self._hover_index = -1
            self.update()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Space):
            if not self._segments or not self._has_file:
                self.openRequested.emit()
            elif self._selected_index >= 0:
                self.formatSelected.emit(self._segments[self._selected_index].operation.operation_id)
            return

        mapping = {
            Qt.Key.Key_Up: 90.0,
            Qt.Key.Key_Right: 0.0,
            Qt.Key.Key_Down: 270.0,
            Qt.Key.Key_Left: 180.0,
        }
        if event.key() in mapping and self._segments:
            target = mapping[event.key()]
            best_i, best_d = 0, 999.0
            for i, seg in enumerate(self._segments):
                d = min(abs(seg.mid_angle_deg - target), 360 - abs(seg.mid_angle_deg - target))
                if d < best_d:
                    best_d, best_i = d, i
            self._selected_index = best_i
            self._hover_index = best_i
            self.update()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if not path:
            return
        idx = self._index_for_pos(event.position())
        self.fileDropped.emit(path)
        if idx >= 0 and self._has_file and self._enabled and self._segments:
            self._selected_index = idx
            self.formatSelected.emit(self._segments[idx].operation.operation_id)
        event.acceptProposedAction()
