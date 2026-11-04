"""Application entry point."""

from __future__ import annotations

import argparse
import faulthandler
import logging
import os
import signal
import sys
from pathlib import Path


def _ensure_stdio() -> None:
    """Windowed PyInstaller builds set stdout/stderr to None — restore safely."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")  # noqa: SIM115


# Must run before any logging / faulthandler / argparse use.
_ensure_stdio()

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from omniconvert.core.registry import get_registry
from omniconvert.services.dependencies import get_dependency_service
from omniconvert.services.logging_setup import setup_logging
from omniconvert.services.resilience import (
    install_exception_hooks,
    install_qt_message_silence,
    set_ui_error_reporter,
)
from omniconvert.services.settings import SettingsStore
from omniconvert.ui.main_window import MainWindow
from omniconvert.ui.theme import apply_theme
from omniconvert.version import __version__

log = logging.getLogger("omniconvert")

_USER_STARTUP_ERROR = (
    "JustConvertIt could not start.\n\n"
    "Try reinstalling the app. If it keeps failing, contact support "
    "without sending personal files."
)


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


def _enable_faulthandler() -> None:
    """Fault dumps only when a real stderr exists (never crash windowed builds)."""
    try:
        err = sys.stderr
        if err is None:
            return
        faulthandler.enable(file=err)
    except Exception:
        pass


def _app_icon() -> QIcon:
    here = Path(__file__).resolve().parent
    for name in ("resources/omniconvert.png", "resources/omniconvert.ico"):
        path = here / name
        if path.is_file():
            return QIcon(str(path))
    return QIcon()


def _show_fatal_dialog(message: str) -> None:
    """User-facing fatal error — no paths, no line numbers, no traceback."""
    try:
        app = QApplication.instance()
        created = False
        if app is None:
            app = QApplication(sys.argv[:1] or ["justconvertit"])
            created = True
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("JustConvertIt")
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()
        if created:
            app.quit()
    except Exception:
        pass


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
    _ensure_stdio()
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
    _enable_faulthandler()
    setup_logging()
    install_exception_hooks()

    settings_store = SettingsStore()
    try:
        settings = settings_store.load()
    except Exception:  # noqa: BLE001 — never die on corrupt settings
        log.exception("Settings load failed; using defaults")
        from omniconvert.services.settings import AppSettings

        settings = AppSettings()

    # Create Qt first so a bad display fails fast; keep startup free of
    # Snap LibreOffice --version (multi-second) and heavy converter imports.
    try:
        app = QApplication([argv[0], *qt_argv])
    except Exception:
        log.exception("Could not start the display")
        _show_fatal_dialog(
            "JustConvertIt could not open a display window.\n\n"
            "Check your graphics drivers and try again."
        )
        return 1
    app.setApplicationName("justconvertit")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("justconvertit")
    app.setWindowIcon(_app_icon())
    install_qt_message_silence()
    try:
        apply_theme(app, settings.theme)
    except Exception:
        log.exception("Theme apply failed; continuing")
    app.setQuitOnLastWindowClosed(True)

    app._omniconvert_signal_timer = _install_signal_handlers(app)  # type: ignore[attr-defined]

    get_dependency_service().configure(
        libreoffice_path=settings.libreoffice_path,
        ffmpeg_path=settings.ffmpeg_path,
        probe_versions=False,
    )

    try:
        window = MainWindow(get_registry(), settings_store=settings_store)
    except Exception:
        log.exception("Main window failed to open")
        _show_fatal_dialog(_USER_STARTUP_ERROR)
        return 1
    set_ui_error_reporter(window._set_status)
    window.show()
    log.info("justconvertit %s started", __version__)
    try:
        code = app.exec()
    except Exception:
        log.exception("Event loop crashed; exiting cleanly")
        _show_fatal_dialog(
            "JustConvertIt hit an unexpected problem and needs to close.\n\n"
            "Your files were not uploaded. Try opening the app again."
        )
        code = 1
    try:
        window.jobs.shutdown()
    except Exception:
        log.exception("Shutdown cleanup failed")
    set_ui_error_reporter(None)
    return int(code)


if __name__ == "__main__":
    _ensure_stdio()
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        # Never let a raw traceback reach the PyInstaller error dialog.
        try:
            logging.getLogger("omniconvert").exception("Fatal startup error")
        except Exception:
            pass
        _show_fatal_dialog(_USER_STARTUP_ERROR)
        raise SystemExit(1)
