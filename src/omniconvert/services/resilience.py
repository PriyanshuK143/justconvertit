"""Keep the UI alive when converters / Qt callbacks throw.

Unexpected errors are logged locally. The user sees a short status line —
never a traceback dialog, and the process keeps running.
"""

from __future__ import annotations

import logging
import sys
import threading
import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

log = logging.getLogger("omniconvert.resilience")

F = TypeVar("F", bound=Callable[..., Any])

# Optional UI callback: (message, kind) where kind is ok|err|info
_ui_reporter: Callable[[str, str], None] | None = None


def set_ui_error_reporter(callback: Callable[[str, str], None] | None) -> None:
    """Register a soft status sink (usually MainWindow._set_status)."""
    global _ui_reporter
    _ui_reporter = callback


def report_soft_error(message: str = "Something went wrong — try another file.") -> None:
    """Show a brief banner if a reporter is wired; always log."""
    log.error("%s", message)
    reporter = _ui_reporter
    if reporter is not None:
        try:
            reporter(message, "err")
        except Exception:  # noqa: BLE001 — never recurse into a crash loop
            log.exception("UI error reporter failed")


def _format_exc(exc_type: type[BaseException] | None, exc: BaseException | None, tb) -> str:
    if exc_type is None or exc is None:
        return "unknown error"
    return "".join(traceback.format_exception(exc_type, exc, tb))


def install_exception_hooks() -> None:
    """Contain uncaught exceptions in the main thread and worker threads."""

    def _sys_hook(exc_type, exc, tb) -> None:  # noqa: ANN001
        if issubclass(exc_type, KeyboardInterrupt):
            # Avoid dumping to a missing stderr in windowed builds.
            return
        # Full detail only in the local log file — never in a UI dialog.
        log.error("Uncaught exception:\n%s", _format_exc(exc_type, exc, tb))
        report_soft_error("Something went wrong — the app kept running.")

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type and issubclass(args.exc_type, SystemExit):
            return
        log.error(
            "Uncaught thread exception in %s:\n%s",
            args.thread.name if args.thread else "?",
            _format_exc(args.exc_type, args.exc_value, args.exc_traceback),
        )
        report_soft_error("A background step failed — try again.")

    sys.excepthook = _sys_hook
    threading.excepthook = _thread_hook  # type: ignore[attr-defined]


def install_qt_message_silence() -> None:
    """Downgrade noisy Qt warnings; never abort on Qt fatal in release use."""
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except Exception:  # noqa: BLE001
        return

    def _handler(mode, context, message: str) -> None:  # noqa: ANN001
        text = message or ""
        # Skip empty / spammy font/glyph noise.
        if not text.strip():
            return
        if mode == QtMsgType.QtFatalMsg:
            log.error("Qt fatal (contained): %s", text)
            report_soft_error("Display glitch contained — keep going.")
            return
        if mode == QtMsgType.QtCriticalMsg:
            log.error("Qt critical: %s", text)
            return
        if mode == QtMsgType.QtWarningMsg:
            log.debug("Qt warning: %s", text)
            return
        log.debug("Qt: %s", text)

    try:
        qInstallMessageHandler(_handler)
    except Exception:  # noqa: BLE001
        log.debug("Could not install Qt message handler", exc_info=True)


def safe_slot(
    *,
    user_message: str = "Something went wrong — try again.",
) -> Callable[[F], F]:
    """Decorator for Qt slots / UI callbacks — never let exceptions escape."""

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception:  # noqa: BLE001
                log.exception("UI handler %s failed", getattr(fn, "__qualname__", fn))
                report_soft_error(user_message)
                return None

        return wrapper  # type: ignore[return-value]

    return decorator


def call_soft(fn: Callable[[], Any], *, user_message: str | None = None) -> Any:
    """Run a callable; on failure log and optionally banner."""
    try:
        return fn()
    except Exception:  # noqa: BLE001
        log.exception("Soft-call failed")
        if user_message:
            report_soft_error(user_message)
        return None
