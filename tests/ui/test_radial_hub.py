from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, QSize
from PySide6.QtWidgets import QApplication

from omniconvert.ui.radial_wheel import RadialWheel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_hub_clickable_when_empty(qapp) -> None:
    wheel = RadialWheel()
    wheel.resize(QSize(400, 400))
    # Center of widget should be hub even with zero segments.
    center = QPointF(200, 200)
    assert wheel._index_for_pos(center) == -2
    # Far corner is not hub
    assert wheel._index_for_pos(QPointF(5, 5)) == -1
    wheel.close()


def test_empty_state_has_no_side_pads(qapp) -> None:
    wheel = RadialWheel()
    wheel.resize(QSize(400, 400))
    wheel.set_has_file(False)
    wheel.set_operations([])
    assert wheel._segments == []
    # Launch UI is hub-only — no idle TOP/RIGHT/BOTTOM/LEFT segments.
    assert not (wheel._has_file and wheel._segments)
    wheel.close()


def test_window_drag_signal_exists(qapp) -> None:
    wheel = RadialWheel()
    assert hasattr(wheel, "windowDragMoved")
    wheel.close()


def _fake_op(label: str, op_id: str):
    from omniconvert.core.converter import ConversionOperation
    from omniconvert.core.formats import FormatId

    return ConversionOperation(
        operation_id=op_id,
        label=label,
        source_formats=frozenset({FormatId.HTML}),
        target_format=FormatId.TXT,
        wheel_label=label,
    )


def test_single_option_is_compact_chip_not_full_ring(qapp) -> None:
    wheel = RadialWheel()
    wheel.set_operations([_fake_op("TXT", "text.html_to_txt")])
    assert len(wheel._segments) == 1
    seg = wheel._segments[0]
    # Must not stretch around almost the whole circle (that left an ugly C-gap).
    assert seg.span_deg < 90.0
    assert abs(seg.mid_angle_deg - 90.0) < 1.0
    wheel.close()


def test_few_options_cluster_near_top(qapp) -> None:
    wheel = RadialWheel()
    wheel.set_operations(
        [
            _fake_op("A", "a"),
            _fake_op("B", "b"),
            _fake_op("C", "c"),
        ]
    )
    assert len(wheel._segments) == 3
    for seg in wheel._segments:
        assert seg.span_deg <= 60.0
        # Upper-half cluster centered on top (not spread around the full circle).
        ang = seg.mid_angle_deg % 360.0
        assert 25.0 <= ang <= 155.0
    wheel.close()


def test_chip_mode_for_single_option(qapp) -> None:
    wheel = RadialWheel()
    wheel.resize(QSize(440, 440))
    wheel.set_operations([_fake_op("TXT", "text.html_to_txt")])
    wheel.set_has_file(True)
    assert wheel._chip_mode() is True
    c, outer, inner, _ = wheel._geometry()
    rect = wheel._chip_rect(c, outer, inner, wheel._segments[0], 0)
    # Chip sits above hub center and is a real click/drag target.
    assert rect.center().y() < c.y()
    assert rect.width() >= 80
    assert wheel._index_for_pos(rect.center()) == 0
    wheel.close()


def test_move_rim_includes_air_gap_with_file(qapp) -> None:
    wheel = RadialWheel()
    wheel.resize(QSize(440, 440))
    wheel.set_operations([_fake_op("A", "a"), _fake_op("B", "b"), _fake_op("C", "c"), _fake_op("D", "d"), _fake_op("E", "e")])
    wheel.set_has_file(True)
    c, outer, inner, hub = wheel._geometry()
    # Mid air-gap between hub and pads should be a move grip.
    mid_r = (hub + inner) / 2.0
    gap_pt = QPointF(c.x() + mid_r, c.y())
    assert wheel._is_on_move_rim(gap_pt) is True
    wheel.close()


def test_status_banner_paints_with_pads(qapp) -> None:
    wheel = RadialWheel()
    wheel.resize(QSize(440, 440))
    wheel.set_operations([_fake_op("TIFF", "a"), _fake_op("No BG", "b")])
    wheel.set_has_file(True)
    wheel.set_banner("Done · photo_converted.png", "#0f172a")
    assert wheel._banner.startswith("Done")
    # Must not crash while painting the south status pill over chip layout.
    wheel.grab()
    wheel.close()
