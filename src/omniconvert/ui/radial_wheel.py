"""Circular gamepad wheel — single concentric disc, light theme."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget

from omniconvert.core.converter import ConversionOperation
from omniconvert.product import APP_NAME
from omniconvert.ui.icons import paint_convert_mark, paint_file_mark, paint_format_icon

_MAX_PADS = 8
# Cap so a single option never becomes a near-full C-ring.
_MAX_PAD_SPAN_DEG = 56.0
_SINGLE_PAD_SPAN_DEG = 58.0
_CLUSTER_GAP_DEG = 12.0
# How far a hovered pad grows outward when it "pops".
_POP_SCALE = 0.08
# Shared layout for chip + full-ring modes (same hub / gap proportions).
_HUB_FRAC = 0.40
_HUB_PAD_GAP = 0.10
# Thin wedges look broken on Windows HiDPI — always use action chips with a file.


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
    filesDropped = Signal(list)  # list[str] local paths when multiple files dropped
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
        # Idle breathe 0..2π — keeps pads feeling alive when waiting for a drag.
        self._pulse_phase = 0.0
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
        if has_file and self._segments and not self._pop_timer.isActive():
            self._pop_timer.start()
        self.update()

    def set_wheel_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.update()

    def selected_operation_id(self) -> str | None:
        if 0 <= self._selected_index < len(self._segments):
            return self._segments[self._selected_index].operation.operation_id
        return None

    def _chip_mode(self) -> bool:
        """Action chips only — wedge pads overlap / clip badly on Windows HiDPI."""
        return bool(self._has_file and self._segments)

    def _rebuild_segments(self) -> None:
        """Place action chips around the hub (never thin overlapping wedges).

        1–3 options: compact cluster near the top.
        4–8 options: even spacing around the circle so chips do not collide.
        """
        self._segments.clear()
        n = len(self._operations)
        if n == 0:
            return

        if n == 1:
            span = _SINGLE_PAD_SPAN_DEG
            mid = 90.0
            start = (mid - span / 2.0) % 360.0
            self._segments.append(_Segment(self._operations[0], start, span, mid))
            return

        if n <= 3:
            span = min(_MAX_PAD_SPAN_DEG, 46.0 + (4 - n) * 3.0)
            step = span + _CLUSTER_GAP_DEG
            total = n * span + (n - 1) * _CLUSTER_GAP_DEG
            first_mid = 90.0 + total / 2.0 - span / 2.0
            for i, op in enumerate(self._operations):
                mid = (first_mid - i * step) % 360.0
                start = (mid - span / 2.0) % 360.0
                self._segments.append(_Segment(op, start, span, mid))
            return

        # Full circle of chips — equal gaps, no wedge fill.
        slot = 360.0 / n
        span = min(42.0, slot * 0.55)
        for i, op in enumerate(self._operations):
            mid = (90.0 - i * slot) % 360.0
            start = (mid - span / 2.0) % 360.0
            self._segments.append(_Segment(op, start, span, mid))

    def _geometry(self) -> tuple[QPointF, float, float, float]:
        """center, pad_outer, pad_inner, hub — same proportions in chip + ring modes."""
        side = min(self.width(), self.height())
        # Leave room for pop-out growth past the nominal outer radius.
        outer = side / 2.0 - 14.0
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        if self._has_file and self._segments:
            hub = outer * _HUB_FRAC
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
        if not self._segments:
            return -1
        if self._chip_mode():
            c, outer, inner, _ = self._geometry()
            for i, seg in enumerate(self._segments):
                if self._chip_rect(c, outer, inner, seg, i).contains(pos):
                    return i
            # Still allow classic ring hit as a forgiving fallback.
        if not self._is_on_ring(pos):
            return -1
        ang = self._qt_angle(pos)
        for i, seg in enumerate(self._segments):
            rel = (ang - seg.start_angle_deg) % 360.0
            if rel < seg.span_deg:
                return i
        return -1

    def _tick_pop(self) -> None:
        if not self._pop and not (self._has_file and self._segments):
            self._pop_timer.stop()
            return
        changed = False
        # Gentle idle pulse — keep small so chips never look stacked on Windows.
        if self._has_file and self._segments and not self._puck_dragging:
            self._pulse_phase = (self._pulse_phase + 0.03) % (math.pi * 2.0)
            changed = True
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

    def paintEvent(self, event) -> None:  # noqa: N802
        _ = event
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            c, outer, inner, hub = self._geometry()

            if self._transparent_bg:
                painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
            else:
                painter.fillRect(self.rect(), self._disc)

            show_pads = bool(self._has_file and self._segments)
            if show_pads:
                self._paint_drag_hints(painter, c, hub, inner, outer)
                # Always chips with a file — never thin overlapping wedges.
                for i, seg in enumerate(self._segments):
                    self._paint_action_chip(painter, c, outer, inner, seg, i)

            hub_rect = QRectF(c.x() - hub, c.y() - hub, hub * 2, hub * 2)
            self._paint_hub_chrome(painter, c, hub, hub_rect)

            if not self._puck_dragging:
                self._paint_hub_text(painter, hub_rect)

            if self._banner:
                self._paint_banner(painter, c, outer, inner)

            if self._puck_dragging and self._puck_pos is not None:
                painter.setPen(QPen(self._pad_hot, 2.5, Qt.PenStyle.DashLine))
                painter.drawLine(c, self._puck_pos)
                painter.setBrush(self._pad_hot)
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.drawEllipse(self._puck_pos, 17, 17)
        except Exception:  # noqa: BLE001 — never let paint crash the orb
            import logging

            logging.getLogger("omniconvert.ui").exception("wheel paint failed")
        finally:
            painter.end()

    def _paint_hub_chrome(
        self, painter: QPainter, c: QPointF, hub: float, hub_rect: QRectF
    ) -> None:
        """Crisp hub fill + blue rim — same look for few chips and full ring.

        Soft blur/halo was only obvious in chip mode (empty air around the hub)
        and looked inconsistent next to solid chip/pad borders.
        """
        breathe = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(self._pulse_phase))
        painter.setBrush(self._hub_fill)
        if self._has_file or self._press_on_hub:
            # Match action-chip border: solid blue stroke that gently pulses.
            rim_w = 2.6 + 0.9 * breathe
            rim = QColor(self._hub_rim_active)
            rim.setAlpha(int(200 + 55 * breathe))
            painter.setPen(QPen(rim, rim_w))
        else:
            painter.setPen(QPen(self._hub_rim, 2.5))
        painter.drawEllipse(hub_rect)
        if self._has_file:
            dash = QPen(QColor("#93c5fd"), 1.5, Qt.PenStyle.DashLine)
            dash.setDashPattern([3, 3])
            painter.setPen(dash)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(c, hub * 0.78, hub * 0.78)

    def _paint_banner(
        self, painter: QPainter, c: QPointF, outer: float, inner: float
    ) -> None:
        """Status pill — opaque so it stays readable over pads / hub rim."""
        _ = inner
        font = QFont(self.font())
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        fm = QFontMetrics(font)
        max_w = int(min(outer * 1.55, self.width() - 24))
        text = fm.elidedText(self._banner, Qt.TextElideMode.ElideMiddle, max_w - 20)
        text_w = fm.horizontalAdvance(text)
        pill_h = 24.0
        pill_w = min(float(max_w), text_w + 20.0)

        _, _, _, hub = self._geometry()
        # Chip mode clusters pads at the top → use the open south arc.
        # Full ring: float just under the hub, over whatever pad is there.
        if self._chip_mode():
            y = c.y() + outer * 0.70
        else:
            y = c.y() + hub + 14.0
            # Keep the pill inside the circular orb.
            y = min(y, c.y() + outer - pill_h / 2 - 4.0)

        rect = QRectF(c.x() - pill_w / 2, y - pill_h / 2, pill_w, pill_h)
        painter.setPen(QPen(QColor("#94a3b8"), 1.2))
        painter.setBrush(QColor(255, 255, 255, 245))
        painter.drawRoundedRect(rect, pill_h / 2, pill_h / 2)
        painter.setPen(self._banner_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_hub_text(self, painter: QPainter, hub_rect: QRectF) -> None:
        """Brand/file mark + label + hint, vertically centered as one stack."""
        single_line = not (self._has_file and self._segments)
        pad = 14
        avail = max(48, int(hub_rect.width() - pad * 2))
        if self._has_file and len(self._segments) == 1:
            sub = f"drag to {self._segments[0].operation.segment_label}"
        elif self._has_file and self._segments:
            sub = "drag to an action"
        else:
            sub = self._center_sub

        icon_size = min(56.0, hub_rect.width() * 0.34)
        gap_icon = 10.0
        gap_sub = 4.0

        font = QFont(self.font())
        font.setBold(True)
        label = self._center_label
        point = 13 if single_line else 10
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
                widest = max((fm.horizontalAdvance(ln) for ln in lines), default=0)
                if widest <= avail:
                    break
            point -= 1
        else:
            fm = QFontMetrics(font)
            lines = [fm.elidedText(label, Qt.TextElideMode.ElideMiddle, avail)]

        fm = QFontMetrics(font)
        name_h = fm.lineSpacing() * len(lines)

        sub_font = QFont(self.font())
        sub_font.setPointSize(8)
        sub_font.setBold(False)
        sub_fm = QFontMetrics(sub_font)
        sub_h = sub_fm.height() if sub else 0.0

        stack_h = icon_size + gap_icon + name_h + (gap_sub + sub_h if sub else 0.0)
        top = hub_rect.center().y() - stack_h / 2.0

        icon_rect = QRectF(
            hub_rect.center().x() - icon_size / 2,
            top,
            icon_size,
            icon_size,
        )
        if self._has_file:
            paint_file_mark(painter, icon_rect, QColor("#2563eb"))
        else:
            paint_convert_mark(painter, icon_rect, QColor("#2563eb"))

        y = icon_rect.bottom() + gap_icon
        painter.setPen(self._text)
        painter.setFont(font)
        for ln in lines:
            line_rect = QRectF(hub_rect.left() + pad, y, hub_rect.width() - pad * 2, fm.lineSpacing())
            painter.drawText(line_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, ln)
            y += fm.lineSpacing()

        if sub:
            painter.setPen(self._muted)
            painter.setFont(sub_font)
            shown = sub_fm.elidedText(sub, Qt.TextElideMode.ElideMiddle, avail)
            sub_rect = QRectF(
                hub_rect.left() + pad,
                y + gap_sub,
                hub_rect.width() - pad * 2,
                sub_h,
            )
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, shown)

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

    def _chip_rect(
        self,
        c: QPointF,
        outer: float,
        inner: float,
        seg: _Segment,
        index: int,
    ) -> QRectF:
        pop = self._pop[index] if index < len(self._pop) else 0.0
        breathe = 0.5 + 0.5 * math.sin(self._pulse_phase + index * 0.9)
        grow = outer * _POP_SCALE * max(pop, 0.06 * breathe)
        r = (outer + inner) / 2.0 + grow * 0.25
        pt = _point_on_circle(c, r, seg.mid_angle_deg)
        # Scale chips down when many actions share the ring (Windows HiDPI safety).
        band = max(48.0, outer - inner)
        n = max(len(self._segments), 1)
        if n <= 2:
            base_w, base_h = 88.0, 76.0
        elif n <= 4:
            base_w, base_h = 78.0, 68.0
        else:
            base_w, base_h = 68.0, 60.0
        w = min(base_w, max(56.0, band * (0.95 if n <= 4 else 0.82)))
        h = min(base_h, max(50.0, band * (0.88 if n <= 4 else 0.75)))
        w += 4.0 * pop
        h += 3.0 * pop
        return QRectF(pt.x() - w / 2.0, pt.y() - h / 2.0, w, h)

    def _paint_drag_hints(
        self,
        painter: QPainter,
        c: QPointF,
        hub: float,
        inner: float,
        outer: float,
    ) -> None:
        """Animated chevrons from hub toward each action chip."""
        if self._puck_dragging:
            return
        breathe = 0.5 + 0.5 * math.sin(self._pulse_phase)
        for i, seg in enumerate(self._segments):
            pop = self._pop[i] if i < len(self._pop) else 0.0
            if pop > 0.55:
                continue
            start_r = hub + 6.0
            end_r = (inner + outer) / 2.0 - 28.0
            if end_r <= start_r + 8:
                continue
            for step in (0.28, 0.52, 0.76):
                # March chevrons outward with the pulse.
                t = (step + 0.12 * breathe) % 1.0
                if t < 0.12 or t > 0.92:
                    continue
                r = start_r + (end_r - start_r) * t
                pt = _point_on_circle(c, r, seg.mid_angle_deg)
                alpha = int(40 + 110 * (1.0 - abs(t - 0.5) * 1.6) * (0.55 + 0.45 * breathe))
                color = QColor(self._pad_hot)
                color.setAlpha(max(0, min(180, alpha)))
                self._paint_chevron(painter, pt, seg.mid_angle_deg, color)

    def _paint_chevron(
        self, painter: QPainter, tip: QPointF, qt_angle_deg: float, color: QColor
    ) -> None:
        rad = math.radians(qt_angle_deg)
        # Point outward along the ray from hub center.
        dx, dy = math.cos(rad), -math.sin(rad)
        px, py = -dy, dx
        size = 7.0
        back = QPointF(tip.x() - dx * size, tip.y() - dy * size)
        left = QPointF(back.x() + px * size * 0.7, back.y() + py * size * 0.7)
        right = QPointF(back.x() - px * size * 0.7, back.y() - py * size * 0.7)
        path = QPainterPath()
        path.moveTo(tip)
        path.lineTo(left)
        path.lineTo(right)
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPath(path)

    def _paint_action_chip(
        self,
        painter: QPainter,
        c: QPointF,
        outer: float,
        inner: float,
        seg: _Segment,
        index: int,
    ) -> None:
        """Rounded interactive chip — clearer affordance than a lonely wedge."""
        pop = self._pop[index] if index < len(self._pop) else 0.0
        hot = pop > 0.15
        breathe = 0.5 + 0.5 * math.sin(self._pulse_phase + index * 0.9)
        rect = self._chip_rect(c, outer, inner, seg, index)
        radius = 16.0

        # Light shadow only — no soft blue blur (matches pad / hub chrome).
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._pad_shadow)
        painter.drawRoundedRect(
            rect.translated(0, 2 + 2 * pop), radius, radius
        )

        # Card body with light gradient
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        if hot:
            grad.setColorAt(0.0, QColor("#3b82f6"))
            grad.setColorAt(1.0, QColor("#1d4ed8"))
        else:
            grad.setColorAt(0.0, QColor("#eff6ff"))
            grad.setColorAt(1.0, QColor("#dbeafe"))
        painter.setBrush(grad)
        # Crisp blue stroke — same language as hub rim and pad outlines.
        rim_w = 2.4 if hot else (1.8 + 0.4 * breathe)
        painter.setPen(QPen(self._pad_hot if hot else QColor("#2563eb"), rim_w))
        painter.drawRoundedRect(rect, radius, radius)

        label = seg.operation.segment_label
        # Square icon tile — avoids PDF/letter glyphs getting clipped.
        side = min(40.0, rect.width() * 0.52) + 4.0 * pop
        icon_rect = QRectF(
            rect.center().x() - side / 2,
            rect.top() + 10,
            side,
            side,
        )
        paint_format_icon(
            painter,
            icon_rect,
            format_id=seg.operation.target_format,
            label=label,
            hot=hot,
        )

        painter.setPen(self._label_on_hot if hot else self._text)
        font = QFont(self.font())
        font.setPointSize(12 if hot else 11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(rect.left(), icon_rect.bottom() + 4, rect.width(), 20),
            Qt.AlignmentFlag.AlignCenter,
            label,
        )

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
        # Idle float matches chip mode (staggered per pad); hover still pops more.
        breathe = 0.5 + 0.5 * math.sin(self._pulse_phase + index * 0.9)
        idle = 0.18 * breathe
        grow = outer * _POP_SCALE * max(pop, idle)
        pad_outer = outer + grow
        pad_inner = max(inner - grow * 0.15, inner * 0.92)
        path = self._pad_path(c, pad_outer, pad_inner, seg.start_angle_deg, seg.span_deg)

        if pop > 0.05 or idle > 0.08:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._pad_shadow)
            shadow = self._pad_path(
                QPointF(c.x(), c.y() + 2 + 3 * max(pop, idle)),
                pad_outer,
                pad_inner,
                seg.start_angle_deg,
                seg.span_deg,
            )
            painter.drawPath(shadow)

        # Crisp outline (no soft blur halo) — matches chips + hub.
        rim_w = 2.2 if hot else (1.6 + 0.35 * breathe)
        painter.setPen(QPen(self._pad_hot if hot else QColor("#2563eb"), rim_w))
        fill = QColor(self._pad_hot if hot else self._pad)
        if hot:
            fill.setAlpha(int(200 + 55 * pop))
        painter.setBrush(fill)
        painter.drawPath(path)

        pt = _point_on_circle(c, (pad_outer + pad_inner) / 2.0, seg.mid_angle_deg)
        label = seg.operation.segment_label
        side = 32.0
        icon_rect = QRectF(pt.x() - side / 2, pt.y() - side / 2 - 6, side, side)
        paint_format_icon(
            painter,
            icon_rect,
            format_id=seg.operation.target_format,
            label=label,
            hot=hot,
        )
        painter.setPen(self._label_on_hot if hot else self._text)
        font = QFont(self.font())
        font.setPointSize(10 if hot else 9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(pt.x() - 40, icon_rect.bottom() + 2, 80, 18),
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

        # Reposition: outer rim, air-gap ring, or Alt/Meta+hub (works with a file too).
        alt_move = bool(
            event.modifiers()
            & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)
        )
        if self._has_file and self._segments and self._is_on_move_rim(pos):
            self._start_system_or_fallback_move(event)
            event.accept()
            return
        if idx == -2 and alt_move:
            self._start_system_or_fallback_move(event)
            event.accept()
            return

        # Empty hub outer ring: move on press (required on Wayland).
        if idx == -2 and self._hub_drag_zone(pos) and not (
            self._has_file and self._segments and self._enabled
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
        """Bands used to reposition the orb after a file is loaded.

        Includes the air gap between hub and pads (easier to grab) plus the
        outer rim — so the orb does not feel stuck once pads appear.
        """
        _, outer, inner, hub = self._geometry()
        d = self._dist_from_center(pos)
        in_gap = (hub + 2.0) <= d <= max(inner - 2.0, hub + 4.0)
        on_edge = (outer - 28.0) <= d <= outer + 4.0
        # Also allow empty gaps between pad wedges (not on a pad).
        if in_gap or on_edge:
            return True
        if d > hub + 2.0 and d < outer - 4.0 and self._index_for_pos(pos) < 0:
            return True
        return False

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
            idx == -2
            and (
                self._hub_drag_zone(pos)
                and not (self._has_file and self._segments)
            )
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
        paths = [u.toLocalFile() for u in urls if u.toLocalFile()]
        if not paths:
            return
        idx = self._index_for_pos(event.position())
        if len(paths) > 1:
            self.filesDropped.emit(paths)
        else:
            self.fileDropped.emit(paths[0])
            if idx >= 0 and self._has_file and self._enabled and self._segments:
                self._selected_index = idx
                self.formatSelected.emit(self._segments[idx].operation.operation_id)
        event.acceptProposedAction()
