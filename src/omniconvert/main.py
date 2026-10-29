"""Application entry point."""

from __future__ import annotations

import argparse
import faulthandler
import logging
import os
import signal
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from omniconvert.core.registry import get_registry
from omniconvert.services.dependencies import get_dependency_service
from omniconvert.services.logging_setup import setup_logging
from omniconvert.services.settings import SettingsStore
from omniconvert.ui.main_window import MainWindow
from omniconvert.ui.theme import apply_theme
from omniconvert.version import __version__

log = logging.getLogger("omniconvert")


def _configure_windows_identity() -> None:
    """Taskbar grouping / jump-list identity on Windows."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            "justconvertit.Desktop.1"
        )
    except Exception:
        log.debug("Could not set AppUserModelID", exc_info=True)


def _enable_high_dpi() -> None:
    """Scale cleanly at 100%/125%/150%/200% on Windows and Linux."""
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass


def _app_icon() -> QIcon:
    here = Path(__file__).resolve().parent
    for name in ("resources/omniconvert.png", "resources/omniconvert.ico"):
        path = here / name
        if path.is_file():
            return QIcon(str(path))
    return QIcon()


def _run_smoke_convert(operation_id: str, source: Path, destination: Path) -> int:
    """Headless conversion for offline packaging checks (no GUI, no network)."""
    setup_logging()
    settings = SettingsStore().load()
    get_dependency_service().configure(
        libreoffice_path=settings.libreoffice_path,
        ffmpeg_path=settings.ffmpeg_path,
    )
    registry = get_registry()
    result = registry.convert(
        operation_id=operation_id,
        source=source,
        destination=destination,
        settings={"jpeg_quality": 85, "transparency_background": "#FFFFFF"},
    )
    print(f"smoke-ok {result.output_path} bytes={result.bytes_written}")
    return 0


def _install_signal_handlers(app: QApplication) -> QTimer:
    def _quit(*_args: object) -> None:
        log.info("Interrupt received — quitting.")
        app.quit()

    signal.signal(signal.SIGINT, _quit)
    signal.signal(signal.SIGTERM, _quit)

    tick = QTimer()
    tick.setInterval(200)
    tick.timeout.connect(lambda: None)
    tick.start()
    return tick


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--smoke-convert",
        nargs=3,
        metavar=("OPERATION", "SOURCE", "DEST"),
        help="Run one local conversion and exit (packaging / offline checks).",
    )
    args, qt_argv = parser.parse_known_args(argv[1:])
    if args.smoke_convert:
        op, src, dst = args.smoke_convert
        return _run_smoke_convert(op, Path(src), Path(dst))

    _enable_high_dpi()
    _configure_windows_identity()
    faulthandler.enable()
    setup_logging()

    settings_store = SettingsStore()
    settings = settings_store.load()

    # Create Qt first so a bad display fails fast; keep startup free of
    # Snap LibreOffice --version (multi-second) and heavy converter imports.
    app = QApplication([argv[0], *qt_argv])
    app.setApplicationName("justconvertit")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("justconvertit")
    app.setWindowIcon(_app_icon())
    apply_theme(app, settings.theme)
    app.setQuitOnLastWindowClosed(True)

    app._omniconvert_signal_timer = _install_signal_handlers(app)  # type: ignore[attr-defined]

    get_dependency_service().configure(
        libreoffice_path=settings.libreoffice_path,
        ffmpeg_path=settings.ffmpeg_path,
        probe_versions=False,
    )

    window = MainWindow(get_registry(), settings_store=settings_store)
    window.show()
    log.info("justconvertit %s started", __version__)
    code = app.exec()
    window.jobs.shutdown()
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
