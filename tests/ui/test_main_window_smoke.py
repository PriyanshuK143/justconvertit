from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from omniconvert.core.registry import build_default_registry
from omniconvert.services.settings import SettingsStore
from omniconvert.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_constructs(qapp, tmp_path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    win = MainWindow(build_default_registry(), settings_store=store)
    assert win.windowTitle().startswith("justconvertit")
    win.close()
