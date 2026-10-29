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
