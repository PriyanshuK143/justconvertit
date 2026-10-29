"""Frameless circular desktop orb — wheel only, no square chrome."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPen,
    QRegion,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from omniconvert.core.converter import ConversionOperation, SettingSpec
from omniconvert.core.detection import detect_file, format_size
from omniconvert.core.errors import AppError
from omniconvert.product import APP_NAME
from omniconvert.core.formats import DetectedFile
from omniconvert.core.output import default_output_name
from omniconvert.core.registry import ConversionRegistry
from omniconvert.platform.paths import is_writable_dir
from omniconvert.platform.reveal import open_path, reveal_in_file_manager
from omniconvert.services.dependencies import get_dependency_service
from omniconvert.services.engine_setup import needs_engine_setup
from omniconvert.services.jobs import JobManager
from omniconvert.services.settings import AppSettings, SettingsStore
from omniconvert.ui.dialogs import (
    AboutDialog,
    FirstRunEnginesDialog,
    SettingsDialog,
    run_engine_install_with_ui,
    show_engine_install_result,
)
from omniconvert.ui.radial_wheel import RadialWheel
from omniconvert.ui.save_dialog import SaveAsDialog
from omniconvert.ui.theme import apply_theme
from omniconvert.version import __version__

log = logging.getLogger("omniconvert.ui")

ORB_SIZE = 440
# Launch shows only the center button; expands to ORB_SIZE after a file is loaded.
HUB_SIZE = 240


class _OptionsPopup(QDialog):
    """Tiny options sheet when a conversion has settings."""

    def __init__(
        self,
        op: ConversionOperation,
        app_settings: AppSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(op.label)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._widgets: dict[str, QWidget] = {}
        self._op = op

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        title = QLabel(op.label)
        title.setObjectName("appTitle")
        root.addWidget(title)

        form = QFormLayout()
        for spec in op.settings:
            w = self._make_widget(spec, app_settings)
            self._widgets[spec.key] = w
            form.addRow(spec.label, w)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        if parent is not None:
            self.setStyleSheet(parent.styleSheet())

    def _make_widget(self, spec: SettingSpec, app_settings: AppSettings) -> QWidget:
        if spec.kind == "int":
            box = QSpinBox()
            box.setRange(int(spec.minimum or 0), int(spec.maximum or 100))
            default = (
                app_settings.jpeg_quality
                if spec.key == "jpeg_quality"
                else int(spec.default)
            )
            box.setValue(int(default))
            return box
        edit = QLineEdit(str(spec.default))
        if spec.key == "transparency_background":
            edit.setText(app_settings.transparency_background)
        return edit

    def values(self) -> dict:
        out: dict = {}
        for spec in self._op.settings:
            w = self._widgets.get(spec.key)
            if isinstance(w, QSpinBox):
                out[spec.key] = w.value()
            elif isinstance(w, QLineEdit):
                out[spec.key] = w.text()
            else:
                out[spec.key] = spec.default
        return out


class MainWindow(QWidget):
    """Circular floating wheel only."""

    def __init__(
        self,
        registry: ConversionRegistry,
        settings_store: SettingsStore | None = None,
    ) -> None:
        super().__init__()
        self.registry = registry
        self.settings_store = settings_store or SettingsStore()
        self.settings: AppSettings = self.settings_store.load()
        get_dependency_service().configure(
            libreoffice_path=self.settings.libreoffice_path,
            ffmpeg_path=self.settings.ffmpeg_path,
            probe_versions=False,
        )
        self.jobs = JobManager(registry, self)

        self.detected: DetectedFile | None = None
        self._source_path: Path | None = None
        self._current_ops: list[ConversionOperation] = []
        self._selected_op: ConversionOperation | None = None
        self._last_output: Path | None = None
        self._output_dir: Path | None = None
        self._always_on_top = True
        self._hover_chrome = False
        self._status_text = "Click center to open"
        self._status_kind = "info"

        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.setObjectName("desktopOrb")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._orb_size = HUB_SIZE
        self.setFixedSize(HUB_SIZE, HUB_SIZE)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._engines_prompt_armed = False
        self._build_ui()
        self._apply_circle_mask()
        self._connect()
        self._install_shortcuts()
        self._place_on_screen()

    def _apply_circle_mask(self) -> None:
        """True circle window — no square box."""
        s = self._orb_size
        self.setMask(QRegion(QRect(0, 0, s, s), QRegion.RegionType.Ellipse))

    def _set_orb_size(self, size: int) -> None:
        """Resize the circular window while keeping its center fixed on screen."""
        if size == self._orb_size:
            self._apply_circle_mask()
            self._position_close_btn()
            return
        cx = self.x() + self._orb_size // 2
        cy = self.y() + self._orb_size // 2
        self._orb_size = size
        self.setFixedSize(size, size)
        self.wheel.setFixedSize(size, size)
        self._apply_circle_mask()
        self.move(cx - size // 2, cy - size // 2)
        self._position_close_btn()

    def _position_close_btn(self) -> None:
        """Pin × to the upper-right of the painted hub (not the outer empty rim)."""
        s = self._orb_size
        outer = s / 2.0 - 6.0
        hub_r = outer * (0.38 if self.detected is not None else 0.52)
        cx = cy = s / 2.0
        # Upper-right on the hub rim, inset so the circular mask still covers it.
        bx = int(cx + hub_r * 0.55 - 6)
        by = int(cy - hub_r * 0.55 - 6)
        self.close_btn.move(max(4, bx), max(4, by))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.wheel = RadialWheel()
        self.wheel.setFixedSize(HUB_SIZE, HUB_SIZE)
        self.wheel.set_transparent_background(True)
        layout.addWidget(self.wheel)

        self.close_btn = QPushButton("×", self)
        self.close_btn.setObjectName("orbClose")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self._quit_app)
        self.close_btn.setVisible(False)
        self._position_close_btn()

        # Status is drawn on the wheel overlay via set_banner — no external tray.
        self.status = QLabel(self)  # kept for polish helpers; hidden
        self.status.hide()
        self.progress_chip = QLabel(self)
        self.progress_chip.hide()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # Needed before Wayland startSystemMove() can reposition the orb.
        _ = self.winId()
        self._apply_circle_mask()
        self._position_close_btn()
        if not self._engines_prompt_armed:
            self._engines_prompt_armed = True
            QTimer.singleShot(0, self._maybe_prompt_engines)

    def _maybe_prompt_engines(self) -> None:
        if not needs_engine_setup(engines_setup_done=self.settings.engines_setup_done):
            return
        dlg = FirstRunEnginesDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = run_engine_install_with_ui(self)
            show_engine_install_result(self, result)
            if result.ok:
                self._set_status("Optional tools ready", "ok")
            else:
                self._set_status("Optional tools incomplete — see Settings", "info")
        self.settings.engines_setup_done = True
        self.settings_store.save(self.settings)

    def _connect(self) -> None:
        self.wheel.openRequested.connect(self.open_file_dialog)
        self.wheel.fileDropped.connect(self.load_path)
        self.wheel.formatSelected.connect(self._on_format_selected_deferred)
        self.wheel.windowDragMoved.connect(self.move)
        self.jobs.job_progress.connect(self._on_progress)
        self.jobs.job_succeeded.connect(self._on_success)
        self.jobs.job_failed.connect(self._on_failure)
        self.jobs.job_cancelled.connect(self._on_cancelled)
        self.jobs.busy_changed.connect(self._on_busy)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.jobs.shutdown()
        super().closeEvent(event)

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence.StandardKey.Open, self, self.open_file_dialog)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self._quit_app)
        QShortcut(QKeySequence.StandardKey.Quit, self, self._quit_app)
        QShortcut(QKeySequence("Ctrl+,"), self, self.open_settings)

    def _quit_app(self) -> None:
        self.jobs.shutdown(timeout_ms=1500)
        app = QApplication.instance()
        if app is not None:
            app.quit()
        self.close()

    def _place_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.move(geo.right() - self.width() - 24, geo.bottom() - self.height() - 48)

    def paintEvent(self, event) -> None:  # noqa: N802
        _ = event
        # Fully transparent shell; wheel paints the disc.
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.end()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover_chrome = True
        self.close_btn.setVisible(True)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_chrome = False
        self.close_btn.setVisible(False)
        self.update()
        super().leaveEvent(event)

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        recent = menu.addAction("Open recent file", self._open_recent_converted)
        recent.setEnabled(self._recent_converted_path() is not None)
        if self._last_output and self._last_output.exists():
            menu.addAction("Show in folder", self._reveal_result)
        menu.addSeparator()
        menu.addAction("Choose output folder…", self._browse_output)
        menu.addAction("Settings…", self.open_settings)
        top_act = menu.addAction("Always on top")
        top_act.setCheckable(True)
        top_act.setChecked(self._always_on_top)
        top_act.toggled.connect(self._set_always_on_top)
        if self.jobs.is_busy:
            menu.addSeparator()
            menu.addAction("Cancel conversion", self.jobs.cancel)
        menu.addSeparator()
        menu.addAction("About…", self.open_about)
        menu.addAction("Quit", self._quit_app)
        menu.exec(self.mapToGlobal(pos))

    def _recent_converted_path(self) -> Path | None:
        """Most recently converted output file that still exists."""
        if self._last_output and self._last_output.exists():
            return self._last_output
        for entry in self.settings.recent_history:
            if entry.get("status") not in {"ok", "succeeded"}:
                continue
            raw = entry.get("output_path") or ""
            path = Path(raw)
            if path.is_file():
                return path
        return None

    def _open_recent_converted(self) -> None:
        path = self._recent_converted_path()
        if path is None:
            self._set_status("No recent converted file", "err")
            return
        open_path(path)
        self._set_status(f"Opened {path.name}", "ok")

    def _set_always_on_top(self, enabled: bool) -> None:
        self._always_on_top = enabled
        flags = Qt.WindowType.FramelessWindowHint
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._apply_circle_mask()
        self.show()

    def open_file_dialog(self) -> None:
        was_on_top = self._always_on_top
        if was_on_top:
            self._set_always_on_top(False)
        try:
            path, _ = QFileDialog.getOpenFileName(
                self,
                f"Open file — {APP_NAME}",
                str(Path.home()),
            )
        finally:
            if was_on_top:
                self._set_always_on_top(True)
            self.raise_()
            self.activateWindow()
        if path:
            QTimer.singleShot(0, lambda p=path: self.load_path(p))

    def load_path(self, path: str) -> None:
        if self.jobs.is_busy:
            self._set_status("Busy — cancel first (right-click)", "err")
            return
        self._set_status("Opening…", "info")
        QApplication.processEvents()
        try:
            detected = detect_file(Path(path))
        except AppError as exc:
            self._set_status(exc.user_message, "err")
            return
        except OSError as exc:
            self._set_status(f"Could not read file: {exc}", "err")
            return
        except Exception as exc:  # noqa: BLE001
            self._set_status("Could not open that file.", "err")
            log.exception("load_path failed: %s", exc)
            return

        self.detected = detected
        self._source_path = Path(path).resolve()
        self._selected_op = None
        self._last_output = None
        # Default output = uploaded file's folder
        self._output_dir = self._source_path.parent

        try:
            ops = self.registry.available_operations_for(detected.format_id)
        except Exception as exc:  # noqa: BLE001
            log.exception("registry lookup failed: %s", exc)
            ops = []

        self._current_ops = ops
        labels = [op.segment_label for op in ops[:8]]
        log.info("Loaded %s → %d ops: %s", detected.format_id, len(ops), labels)

        # Prefer original filename for display (not a truncated stem-only guess).
        display_name = self._source_path.name
        # Expand from center-only hub to the full format wheel.
        self._set_orb_size(ORB_SIZE)
        self.wheel.set_operations(ops)
        self.wheel.set_has_file(True)
        self.wheel.set_center_text(
            display_name,
            f"{detected.format_id.label} · {format_size(detected.size_bytes)}",
        )
        self.wheel.set_wheel_enabled(bool(ops))

        # Do not repeat format names here — pads already show them.
        if not ops:
            self._set_status(f"No conversions for {detected.format_id.label}", "err")
        else:
            self._set_status("", "info")  # clear banner; hub says "drag to a pad"
        _ = labels

    def _on_format_selected_deferred(self, operation_id: str) -> None:
        QTimer.singleShot(0, lambda: self._on_format_selected(operation_id))

    def _on_format_selected(self, operation_id: str) -> None:
        if not self.detected or not self._source_path:
            return
        if self.jobs.is_busy:
            self._set_status("Already converting…", "info")
            return
        try:
            op = self.registry.get_operation(operation_id)
        except AppError as exc:
            self._set_status(exc.user_message, "err")
            return

        self._selected_op = op
        settings = self._default_settings(op)
        if op.settings:
            popup = _OptionsPopup(op, self.settings, None)
            popup.setStyleSheet(self.styleSheet())
            if popup.exec() != QDialog.DialogCode.Accepted:
                self._set_status("Cancelled", "info")
                return
            settings.update(popup.values())

        # Always ask for rename + location; default folder = uploaded file path.
        default_dir = self._output_dir or self._source_path.parent
        default_name = default_output_name(self._source_path, op.target_format)
        save = SaveAsDialog(
            title=f"Save as {op.target_format.label}",
            default_dir=default_dir,
            default_name=default_name,
            parent=None,
        )
        save.setStyleSheet(self.styleSheet())
        if save.exec() != QDialog.DialogCode.Accepted:
            self._set_status("Cancelled", "info")
            return
        out_dir, out_name = save.result_path_parts()
        if not is_writable_dir(out_dir):
            self._set_status("Output folder is not writable", "err")
            return
        self._output_dir = out_dir
        self._start_conversion(settings, out_dir=out_dir, out_name=out_name)

    def _default_settings(self, op: ConversionOperation) -> dict:
        values: dict = {
            "jpeg_quality": self.settings.jpeg_quality,
            "transparency_background": self.settings.transparency_background,
        }
        for spec in op.settings:
            values.setdefault(spec.key, spec.default)
        return values

    def _start_conversion(
        self,
        settings: dict,
        *,
        out_dir: Path | None = None,
        out_name: str | None = None,
    ) -> None:
        if not self.detected or not self._selected_op:
            return
        dest_dir = out_dir or self._output_dir or Path(self.detected.path).parent
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._set_status(f"Bad output folder: {exc}", "err")
            return

        name = out_name or default_output_name(
            Path(self.detected.path), self._selected_op.target_format
        )
        try:
            self.jobs.start(
                source_path=Path(self.detected.path),
                source_format=self.detected.format_id,
                target_format=self._selected_op.target_format.value,
                output_dir=dest_dir,
                output_name=name,
                settings=settings,
                operation_id=self._selected_op.operation_id,
            )
        except RuntimeError as exc:
            self._set_status(str(exc), "err")

    def _on_progress(self, job_id: str, fraction: object, message: str) -> None:
        _ = job_id
        if fraction is None:
            self._set_status(message or "Working…", "info")
        else:
            pct = int(float(fraction) * 100)
            self._set_status(f"{pct}% · {message or 'Working…'}", "info")

    def _on_success(self, job_id: str, path: str, message: str) -> None:
        _ = job_id, message
        self._last_output = Path(path)
        self._set_status(f"Done · {Path(path).name}", "ok")
        self.settings_store.add_history(
            self.settings,
            source_name=Path(path).name,
            target_format=self._selected_op.target_format.value if self._selected_op else "",
            output_path=path,
            status="succeeded",
        )
        QTimer.singleShot(3000, lambda: self._set_status("Right-click · open result", "info"))

    def _on_failure(self, job_id: str, message: str) -> None:
        _ = job_id
        self._set_status(message, "err")
        self.settings_store.add_history(
            self.settings,
            source_name=self.detected.display_name if self.detected else "",
            target_format=self._selected_op.target_format.value if self._selected_op else "",
            output_path="",
            status="failed",
        )

    def _on_cancelled(self, job_id: str) -> None:
        _ = job_id
        self._set_status("Cancelled", "info")

    def _on_busy(self, busy: bool) -> None:
        self.wheel.set_wheel_enabled(not busy and bool(self._current_ops))
        if busy:
            self._set_status("Converting…", "info")

    def _set_status(self, text: str, kind: str) -> None:
        self._status_text = text
        self._status_kind = kind
        # Banner lives on the wheel (inside the circle).
        # "ok" uses black — green was hard to read on the blue pad ring.
        color = {"ok": "#0f172a", "err": "#b91c1c", "info": "#334155"}.get(kind, "#334155")
        self.wheel.set_banner(text, color)

    def _browse_output(self) -> None:
        start = str(self._output_dir or Path.home())
        path = QFileDialog.getExistingDirectory(None, f"Output folder — {APP_NAME}", start)
        if path:
            self._output_dir = Path(path)
            self.settings.default_output_dir = path
            self.settings_store.save(self.settings)
            self._set_status(f"Output → {Path(path).name}", "info")

    def _open_result(self) -> None:
        if self._last_output and self._last_output.exists():
            open_path(self._last_output)

    def _reveal_result(self) -> None:
        if self._last_output and self._last_output.exists():
            reveal_in_file_manager(self._last_output)

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.settings = dlg.result_settings()
            self.settings_store.save(self.settings)
            get_dependency_service().configure(
                libreoffice_path=self.settings.libreoffice_path,
                ffmpeg_path=self.settings.ffmpeg_path,
                probe_versions=False,
            )
            app = QApplication.instance()
            if isinstance(app, QApplication):
                apply_theme(app, self.settings.theme)
            if self.settings.default_output_dir:
                self._output_dir = Path(self.settings.default_output_dir)
            # Refresh wheel pads if a file is loaded (optional engines may appear/disappear).
            if self.detected is not None:
                self._current_ops = self.registry.available_operations_for(self.detected.format_id)
                self.wheel.set_operations(self._current_ops)
            self._set_status("Settings saved", "ok")

    def open_about(self) -> None:
        AboutDialog(self).exec()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._last_output:
            self._open_result()
            return
        super().mouseDoubleClickEvent(event)
