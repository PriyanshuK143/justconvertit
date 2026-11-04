"""Per-format vector icons for the radial orb (reference-style, no image assets)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
)

from omniconvert.core.formats import FormatId

# Brand-adjacent accent colors from the reference sheet (stylized, not official marks).
_COLORS = {
    FormatId.PNG: "#2563eb",
    FormatId.JPEG: "#7c3aed",
    FormatId.WEBP: "#16a34a",
    FormatId.BMP: "#ea580c",
    FormatId.TIFF: "#db2777",
    FormatId.GIF: "#8b5cf6",
    FormatId.SVG: "#06b6d4",
    FormatId.TXT: "#2563eb",
    FormatId.MD: "#1e3a8a",
    FormatId.HTML: "#ea580c",
    FormatId.JSON: "#7c3aed",
    FormatId.CSV: "#16a34a",
    FormatId.PDF: "#dc2626",
    FormatId.DOCX: "#2563eb",
    FormatId.PPTX: "#ea580c",
    FormatId.XLSX: "#16a34a",
    FormatId.MP3: "#7c3aed",
    FormatId.WAV: "#2563eb",
    FormatId.MP4: "#2563eb",
    FormatId.MKV: "#7c3aed",
    FormatId.ZIP: "#2563eb",
}


def _aa(painter: QPainter) -> None:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)


def _accent(fmt: FormatId | None) -> QColor:
    if fmt is None:
        return QColor("#2563eb")
    return QColor(_COLORS.get(fmt, "#2563eb"))


def _inset(rect: QRectF, frac: float = 0.14) -> QRectF:
    """Keep glyph comfortably inside the tile."""
    m = min(rect.width(), rect.height()) * frac
    return rect.adjusted(m, m, -m, -m)


def _fit_text(painter: QPainter, text: str, box: QRectF, *, bold: bool = True) -> QFont:
    font = QFont()
    font.setBold(bold)
    size = max(6, int(min(box.height() * 0.55, box.width() / max(len(text), 1) * 1.15)))
    font.setPointSize(size)
    fm = QFontMetrics(font)
    while size > 5 and (
        fm.horizontalAdvance(text) > box.width() * 0.92
        or fm.height() > box.height() * 0.95
    ):
        size -= 1
        font.setPointSize(size)
        fm = QFontMetrics(font)
    painter.setFont(font)
    return font


def _tile(painter: QPainter, rect: QRectF, *, hot: bool) -> None:
    """White rounded tile under every symbol."""
    painter.setPen(QPen(QColor("#e2e8f0"), 1.0))
    painter.setBrush(QColor("#eff6ff") if hot else QColor("#ffffff"))
    radius = min(8.0, min(rect.width(), rect.height()) * 0.22)
    painter.drawRoundedRect(rect, radius, radius)


def paint_convert_mark(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Crisp circular convert arrows — empty-hub brand mark."""
    painter.save()
    _aa(painter)
    box = _inset(rect, 0.12)
    pen = QPen(
        color,
        max(2.6, box.width() * 0.09),
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    # Two arc arrows around the center
    ring = box.adjusted(box.width() * 0.08, box.height() * 0.08, -box.width() * 0.08, -box.height() * 0.08)
    painter.drawArc(ring, 40 * 16, 140 * 16)
    painter.drawArc(ring, 220 * 16, 140 * 16)
    # Arrow heads
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    s = box.width() * 0.12
    # Top-right head
    p1 = QPointF(ring.center().x() + ring.width() * 0.32, ring.top() + ring.height() * 0.18)
    tri1 = QPainterPath()
    tri1.moveTo(p1)
    tri1.lineTo(p1 + QPointF(-s, s * 0.2))
    tri1.lineTo(p1 + QPointF(-s * 0.15, s))
    tri1.closeSubpath()
    painter.drawPath(tri1)
    # Bottom-left head
    p2 = QPointF(ring.center().x() - ring.width() * 0.32, ring.bottom() - ring.height() * 0.18)
    tri2 = QPainterPath()
    tri2.moveTo(p2)
    tri2.lineTo(p2 + QPointF(s, -s * 0.2))
    tri2.lineTo(p2 + QPointF(s * 0.15, -s))
    tri2.closeSubpath()
    painter.drawPath(tri2)
    painter.restore()


def paint_file_mark(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Simple document mark — used when a source file is loaded."""
    painter.save()
    _aa(painter)
    box = _inset(rect, 0.10)
    fold = min(box.width(), box.height()) * 0.28
    path = QPainterPath()
    path.moveTo(box.left() + box.width() * 0.18, box.top() + box.height() * 0.08)
    path.lineTo(box.right() - box.width() * 0.18 - fold, box.top() + box.height() * 0.08)
    path.lineTo(box.right() - box.width() * 0.18, box.top() + box.height() * 0.08 + fold)
    path.lineTo(box.right() - box.width() * 0.18, box.bottom() - box.height() * 0.10)
    path.lineTo(box.left() + box.width() * 0.18, box.bottom() - box.height() * 0.10)
    path.closeSubpath()
    painter.setPen(QPen(color, max(1.6, box.width() * 0.05)))
    painter.setBrush(QColor("#eff6ff"))
    painter.drawPath(path)
    # Fold
    fold_path = QPainterPath()
    fold_path.moveTo(box.right() - box.width() * 0.18 - fold, box.top() + box.height() * 0.08)
    fold_path.lineTo(box.right() - box.width() * 0.18, box.top() + box.height() * 0.08 + fold)
    fold_path.lineTo(box.right() - box.width() * 0.18 - fold, box.top() + box.height() * 0.08 + fold)
    fold_path.closeSubpath()
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPath(fold_path)
    # Text lines
    painter.setPen(QPen(color, max(1.5, box.width() * 0.05), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for frac in (0.42, 0.58, 0.74):
        y = box.top() + box.height() * frac
        painter.drawLine(
            QPointF(box.left() + box.width() * 0.28, y),
            QPointF(box.right() - box.width() * 0.28, y),
        )
    painter.restore()


# Back-compat alias used by older call sites / tests
def paint_cloud_upload(painter: QPainter, rect: QRectF, color: QColor) -> None:
    paint_convert_mark(painter, rect, color)


def _paint_landscape(painter: QPainter, r: QRectF, color: QColor, *, gif: bool = False) -> None:
    box = _inset(r, 0.06)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(box, 4, 4)
    sun = QRectF(
        box.left() + box.width() * 0.58,
        box.top() + box.height() * 0.16,
        box.width() * 0.20,
        box.height() * 0.20,
    )
    painter.setBrush(QColor("#ffffff"))
    painter.drawEllipse(sun)
    peak = QPainterPath()
    peak.moveTo(box.left() + box.width() * 0.08, box.bottom() - box.height() * 0.14)
    peak.lineTo(box.left() + box.width() * 0.38, box.top() + box.height() * 0.42)
    peak.lineTo(box.left() + box.width() * 0.62, box.bottom() - box.height() * 0.14)
    peak.closeSubpath()
    painter.drawPath(peak)
    peak2 = QPainterPath()
    peak2.moveTo(box.left() + box.width() * 0.45, box.bottom() - box.height() * 0.14)
    peak2.lineTo(box.left() + box.width() * 0.72, box.top() + box.height() * 0.50)
    peak2.lineTo(box.left() + box.width() * 0.94, box.bottom() - box.height() * 0.14)
    peak2.closeSubpath()
    soft = QColor("#ffffff")
    soft.setAlpha(200)
    painter.setBrush(soft)
    painter.drawPath(peak2)
    if gif:
        br = min(box.width(), box.height()) * 0.22
        badge = QRectF(box.center().x() - br, box.center().y() - br, br * 2, br * 2)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(badge)
        tri = QPainterPath()
        tri.moveTo(badge.center().x() - br * 0.25, badge.center().y() - br * 0.4)
        tri.lineTo(badge.center().x() - br * 0.25, badge.center().y() + br * 0.4)
        tri.lineTo(badge.center().x() + br * 0.45, badge.center().y())
        tri.closeSubpath()
        painter.setBrush(color)
        painter.drawPath(tri)


def _paint_webp_globe(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.10)
    painter.setPen(QPen(color, max(1.4, box.width() * 0.06)))
    painter.setBrush(QColor("#ffffff"))
    painter.drawEllipse(box)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    cx, cy = box.center().x(), box.center().y()
    painter.drawEllipse(
        QRectF(cx - box.width() * 0.18, box.top() + 2, box.width() * 0.36, box.height() - 4)
    )
    painter.drawLine(QPointF(box.left() + 2, cy), QPointF(box.right() - 2, cy))
    painter.drawLine(
        QPointF(box.left() + 3, cy - box.height() * 0.2),
        QPointF(box.right() - 3, cy - box.height() * 0.2),
    )
    painter.drawLine(
        QPointF(box.left() + 3, cy + box.height() * 0.2),
        QPointF(box.right() - 3, cy + box.height() * 0.2),
    )


def _paint_svg_pen(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.12)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    body = QPainterPath()
    body.moveTo(box.left() + box.width() * 0.58, box.top() + box.height() * 0.12)
    body.lineTo(box.left() + box.width() * 0.82, box.top() + box.height() * 0.36)
    body.lineTo(box.left() + box.width() * 0.40, box.bottom() - box.height() * 0.28)
    body.lineTo(box.left() + box.width() * 0.18, box.bottom() - box.height() * 0.48)
    body.closeSubpath()
    painter.drawPath(body)
    tip = QPainterPath()
    tip.moveTo(box.left() + box.width() * 0.18, box.bottom() - box.height() * 0.48)
    tip.lineTo(box.left() + box.width() * 0.40, box.bottom() - box.height() * 0.28)
    tip.lineTo(box.left() + box.width() * 0.14, box.bottom() - box.height() * 0.14)
    tip.closeSubpath()
    painter.setBrush(QColor("#0e7490"))
    painter.drawPath(tip)


def _paint_txt(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.10)
    painter.setPen(QPen(color, 1.3))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(box, 3, 3)
    painter.setPen(QPen(color, max(1.4, box.width() * 0.06), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for i, frac in enumerate((0.30, 0.48, 0.66, 0.84)):
        y = box.top() + box.height() * frac
        right = box.right() - box.width() * 0.18 if i < 3 else box.center().x() + 2
        painter.drawLine(QPointF(box.left() + box.width() * 0.18, y), QPointF(right, y))


def _paint_md(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.10)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(box, 5, 5)
    painter.setPen(QColor("#ffffff"))
    text_box = box.adjusted(2, 2, -2, -2)
    _fit_text(painter, "M↓", text_box)
    painter.drawText(text_box, Qt.AlignmentFlag.AlignCenter, "M↓")


def _paint_html5(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.10)
    shield = QPainterPath()
    shield.moveTo(box.left() + box.width() * 0.16, box.top() + box.height() * 0.10)
    shield.lineTo(box.right() - box.width() * 0.16, box.top() + box.height() * 0.10)
    shield.lineTo(box.right() - box.width() * 0.20, box.top() + box.height() * 0.62)
    shield.lineTo(box.center().x(), box.bottom() - box.height() * 0.08)
    shield.lineTo(box.left() + box.width() * 0.20, box.top() + box.height() * 0.62)
    shield.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(shield)
    painter.setPen(QColor("#ffffff"))
    text_box = QRectF(box.left(), box.top() + box.height() * 0.12, box.width(), box.height() * 0.50)
    _fit_text(painter, "5", text_box)
    painter.drawText(text_box, Qt.AlignmentFlag.AlignCenter, "5")


def _paint_json(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.14)
    pen = QPen(color, max(1.8, box.width() * 0.08), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    left = QPainterPath()
    left.moveTo(box.center().x() - 1, box.top())
    left.cubicTo(box.left(), box.top(), box.left(), box.center().y(), box.center().x() - 1, box.center().y())
    left.cubicTo(box.left(), box.center().y(), box.left(), box.bottom(), box.center().x() - 1, box.bottom())
    painter.drawPath(left)
    right = QPainterPath()
    right.moveTo(box.center().x() + 1, box.top())
    right.cubicTo(box.right(), box.top(), box.right(), box.center().y(), box.center().x() + 1, box.center().y())
    right.cubicTo(box.right(), box.center().y(), box.right(), box.bottom(), box.center().x() + 1, box.bottom())
    painter.drawPath(right)


def _paint_csv(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.10)
    painter.setPen(QPen(color, 1.2))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(box, 3, 3)
    painter.setPen(QPen(color, 1.1))
    for i in (1, 2):
        x = box.left() + box.width() * (0.33 * i)
        painter.drawLine(QPointF(x, box.top() + 2), QPointF(x, box.bottom() - 2))
        y = box.top() + box.height() * (0.33 * i)
        painter.drawLine(QPointF(box.left() + 2, y), QPointF(box.right() - 2, y))
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRect(QRectF(box.left() + 1, box.top() + 1, box.width() - 2, box.height() * 0.28))


def _paint_letter_badge(painter: QPainter, r: QRectF, color: QColor, letter: str) -> None:
    box = _inset(r, 0.10)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(box, min(6.0, box.width() * 0.2), min(6.0, box.height() * 0.2))
    painter.setPen(QColor("#ffffff"))
    text_box = _inset(box, 0.12)
    _fit_text(painter, letter, text_box)
    painter.drawText(text_box, Qt.AlignmentFlag.AlignCenter, letter)


def _paint_pdf(painter: QPainter, r: QRectF, color: QColor) -> None:
    """Red badge with 'PDF' fully inside — never clipped by the tile."""
    box = _inset(r, 0.10)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    rad = min(5.0, min(box.width(), box.height()) * 0.18)
    painter.drawRoundedRect(box, rad, rad)
    painter.setPen(QColor("#ffffff"))
    text_box = _inset(box, 0.10)
    _fit_text(painter, "PDF", text_box)
    painter.drawText(text_box, Qt.AlignmentFlag.AlignCenter, "PDF")


def _paint_mp3(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.12)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(
        QRectF(
            box.left() + box.width() * 0.18,
            box.top() + box.height() * 0.52,
            box.width() * 0.36,
            box.height() * 0.30,
        )
    )
    painter.drawRect(
        QRectF(
            box.left() + box.width() * 0.46,
            box.top() + box.height() * 0.16,
            box.width() * 0.10,
            box.height() * 0.55,
        )
    )
    beam = QPainterPath()
    beam.moveTo(box.left() + box.width() * 0.56, box.top() + box.height() * 0.16)
    beam.quadTo(
        box.left() + box.width() * 0.82,
        box.top() + box.height() * 0.28,
        box.left() + box.width() * 0.74,
        box.top() + box.height() * 0.50,
    )
    beam.lineTo(box.left() + box.width() * 0.56, box.top() + box.height() * 0.42)
    beam.closeSubpath()
    painter.drawPath(beam)


def _paint_wav(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.12)
    painter.setPen(QPen(color, max(1.8, box.width() * 0.07), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    base = box.center().y()
    heights = (0.20, 0.38, 0.58, 0.82, 0.58, 0.38, 0.24)
    gap = box.width() / (len(heights) + 1)
    for i, hf in enumerate(heights):
        x = box.left() + gap * (i + 1)
        h = box.height() * hf
        painter.drawLine(QPointF(x, base - h / 2), QPointF(x, base + h / 2))


def _paint_mp4(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.08)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    frame = box.adjusted(0, box.height() * 0.16, 0, -box.height() * 0.16)
    painter.drawRoundedRect(frame, 3, 3)
    painter.setBrush(QColor("#ffffff"))
    for yf in (0.30, 0.50, 0.70):
        y = box.top() + box.height() * yf
        painter.drawRect(QRectF(box.left() + 3, y - 1.5, 3.5, 3.5))
        painter.drawRect(QRectF(box.right() - 6.5, y - 1.5, 3.5, 3.5))
    tri = QPainterPath()
    cx, cy = box.center().x() - 1, box.center().y()
    tri.moveTo(cx - 3, cy - 5)
    tri.lineTo(cx - 3, cy + 5)
    tri.lineTo(cx + 6, cy)
    tri.closeSubpath()
    painter.drawPath(tri)


def _paint_mkv(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.10)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    board = QRectF(box.left(), box.top() + box.height() * 0.36, box.width(), box.height() * 0.52)
    painter.drawRoundedRect(board, 3, 3)
    clap = QPainterPath()
    clap.moveTo(board.left(), board.top())
    clap.lineTo(board.right(), board.top() - box.height() * 0.16)
    clap.lineTo(board.right(), board.top())
    clap.closeSubpath()
    painter.drawPath(clap)
    painter.setBrush(QColor("#ffffff"))
    for i in range(4):
        x0 = board.left() + board.width() * (i / 4)
        painter.drawRect(
            QRectF(x0, board.top() - box.height() * 0.14, board.width() / 8, box.height() * 0.10)
        )
    tri = QPainterPath()
    cx, cy = board.center().x() - 1, board.center().y()
    tri.moveTo(cx - 2.5, cy - 4)
    tri.lineTo(cx - 2.5, cy + 4)
    tri.lineTo(cx + 5, cy)
    tri.closeSubpath()
    painter.drawPath(tri)


def _paint_zip(painter: QPainter, r: QRectF, color: QColor) -> None:
    box = _inset(r, 0.10)
    painter.setPen(QPen(color, 1.3))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(box, 3, 3)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    cx = box.center().x()
    n = 5
    for i in range(n):
        y = box.top() + 6 + i * (box.height() - 14) / max(n - 1, 1)
        painter.drawRect(QRectF(cx - 4, y, 3.5, 2.5))
        painter.drawRect(QRectF(cx + 0.5, y + 1.2, 3.5, 2.5))
    painter.drawRoundedRect(QRectF(cx - 5, box.top() + 3, 10, 7), 2, 2)


def paint_format_icon(
    painter: QPainter,
    rect: QRectF,
    *,
    format_id: FormatId | None,
    label: str,
    hot: bool = False,
) -> None:
    """Draw a distinctive symbol for each supported format, clipped to the tile."""
    painter.save()
    _aa(painter)
    # Clip so glyphs can never spill outside the white tile.
    clip = QPainterPath()
    radius = min(8.0, min(rect.width(), rect.height()) * 0.22)
    clip.addRoundedRect(rect, radius, radius)
    painter.setClipPath(clip)

    _tile(painter, rect, hot=hot)
    # Generous inner margin — fixes PDF/letter overflow on small pads.
    r = _inset(rect, 0.12)
    color = _accent(format_id)

    if (label or "").strip().lower().startswith("more"):
        _paint_letter_badge(painter, r, color, "···")
        painter.restore()
        return

    dispatch = {
        FormatId.PNG: lambda: _paint_landscape(painter, r, color),
        FormatId.JPEG: lambda: _paint_landscape(painter, r, color),
        FormatId.BMP: lambda: _paint_landscape(painter, r, color),
        FormatId.TIFF: lambda: _paint_landscape(painter, r, color),
        FormatId.GIF: lambda: _paint_landscape(painter, r, color, gif=True),
        FormatId.WEBP: lambda: _paint_webp_globe(painter, r, color),
        FormatId.SVG: lambda: _paint_svg_pen(painter, r, color),
        FormatId.TXT: lambda: _paint_txt(painter, r, color),
        FormatId.MD: lambda: _paint_md(painter, r, color),
        FormatId.HTML: lambda: _paint_html5(painter, r, color),
        FormatId.JSON: lambda: _paint_json(painter, r, color),
        FormatId.CSV: lambda: _paint_csv(painter, r, color),
        FormatId.PDF: lambda: _paint_pdf(painter, r, color),
        FormatId.DOCX: lambda: _paint_letter_badge(painter, r, color, "W"),
        FormatId.PPTX: lambda: _paint_letter_badge(painter, r, color, "P"),
        FormatId.XLSX: lambda: _paint_letter_badge(painter, r, color, "X"),
        FormatId.MP3: lambda: _paint_mp3(painter, r, color),
        FormatId.WAV: lambda: _paint_wav(painter, r, color),
        FormatId.MP4: lambda: _paint_mp4(painter, r, color),
        FormatId.MKV: lambda: _paint_mkv(painter, r, color),
        FormatId.ZIP: lambda: _paint_zip(painter, r, color),
    }
    painter_fn = dispatch.get(format_id) if format_id is not None else None
    if painter_fn is not None:
        painter_fn()
    else:
        _paint_txt(painter, r, color)
    painter.restore()
