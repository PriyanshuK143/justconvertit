"""Frameless circular desktop orb — wheel only, no square chrome."""

from __future__ import annotations

import logging
import sys
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
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
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
from omniconvert.services.resilience import call_soft, safe_slot
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
from omniconvert.ui.wheel_actions import split_wheel_actions
from omniconvert.version import __version__

log = logging.getLogger("omniconvert.ui")

# Slightly larger on Windows so action chips stay readable under HiDPI scaling.
ORB_SIZE = 500 if sys.platform.startswith("win") else 460
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
        if spec.kind == "choice" and spec.choices:
            combo = QComboBox()
            combo.addItems(list(spec.choices))
            current = str(spec.default)
            idx = combo.findText(current)
            combo.setCurrentIndex(max(0, idx))
            return combo
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
            elif isinstance(w, QComboBox):
                out[spec.key] = w.currentText()
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
        self._batch_paths: list[Path] = []
        self._batch_active = False
        self._batch_ok = 0
        self._batch_fail = 0
        self._overflow_ops: list[ConversionOperation] = []
        self._always_on_top = True
        self._hover_chrome = False
        self._status_text = "Click center to open"
        self._status_kind = "info"
        # Last known on-screen top-left (Wayland/X11 often report 0,0 wrongly).
        self._anchor_pos: QPoint | None = None

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

    def _remember_anchor(self) -> None:
        """Store a believable top-left so resize does not jump to 0,0."""
        geo = self.frameGeometry()
        if geo.width() < 1 or geo.height() < 1:
            return
        # (0,0) is usually a fake Wayland/XWayland reading, not a real place.
        if geo.x() == 0 and geo.y() == 0 and self._anchor_pos is not None:
            return
        if geo.x() == 0 and geo.y() == 0:
            return
        self._anchor_pos = QPoint(geo.x(), geo.y())

    def _ensure_on_screen(self) -> None:
        """Clamp the orb fully into the available screen (fixes left-edge clip)."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        geo = self.frameGeometry()
        w, h = geo.width(), geo.height()
        if w < 1 or h < 1:
            return
        x = geo.x()
        y = geo.y()
        # Prefer remembered anchor when current coords look fake.
        if x == 0 and y == 0 and self._anchor_pos is not None:
            x, y = self._anchor_pos.x(), self._anchor_pos.y()
        x = max(avail.left(), min(x, avail.right() - w + 1))
        y = max(avail.top(), min(y, avail.bottom() - h + 1))
        if x != geo.x() or y != geo.y():
            self.move(x, y)
        self._anchor_pos = QPoint(x, y)

    def _set_orb_size(self, size: int) -> None:
        """Resize the circular window without jumping off-screen."""
        if size == self._orb_size:
            self._apply_circle_mask()
            self._position_close_btn()
            return

        from PySide6.QtGui import QGuiApplication

        wayland = QGuiApplication.platformName().lower().startswith("wayland")
        old = self._orb_size
        self._remember_anchor()

        # Prefer real frame geometry; fall back to last good anchor.
        geo = self.frameGeometry()
        if (geo.x() == 0 and geo.y() == 0) and self._anchor_pos is not None:
            old_tl = QPoint(self._anchor_pos)
        else:
            old_tl = QPoint(geo.x(), geo.y())
        cx = old_tl.x() + old // 2
        cy = old_tl.y() + old // 2

        self._orb_size = size
        self.setFixedSize(size, size)
        self.wheel.setFixedSize(size, size)
        self._apply_circle_mask()

        # Keep visual center stable when the platform allows move(); always clamp.
        if not wayland or self._anchor_pos is not None:
            self.move(int(cx - size // 2), int(cy - size // 2))
        self._ensure_on_screen()
        self._position_close_btn()

    def _position_close_btn(self) -> None:
        """Pin × to the upper-right of the painted hub (not the outer empty rim)."""
        s = self._orb_size
        outer = s / 2.0 - 6.0
        hub_r = outer * (0.42 if self.detected is not None else 0.52)
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
        self.wheel.set_center_text(APP_NAME, "Click or drop a file")
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
        # Windows: never nag at launch — install tools only when a conversion needs them.
        if not needs_engine_setup(engines_setup_done=self.settings.engines_setup_done):
            if sys.platform.startswith("win") and not self.settings.engines_setup_done:
                self.settings.engines_setup_done = True
                self.settings_store.save(self.settings)
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
        self.wheel.filesDropped.connect(self.load_paths)
        self.wheel.formatSelected.connect(self._on_format_selected_deferred)
        self.wheel.windowDragMoved.connect(self._on_window_drag_moved)
        self.jobs.job_progress.connect(self._on_progress)
        self.jobs.job_succeeded.connect(self._on_success)
        self.jobs.job_failed.connect(self._on_failure)
        self.jobs.job_cancelled.connect(self._on_cancelled)
        self.jobs.busy_changed.connect(self._on_busy)
        self.jobs.batch_progress.connect(self._on_batch_progress)

    def _on_window_drag_moved(self, top_left: QPoint) -> None:
        self.move(top_left)
        self._anchor_pos = QPoint(top_left)

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
        self._remember_anchor()
        self._ensure_on_screen()

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
        menu.addAction("Open file…", self.open_file_dialog)
        menu.addAction("Open multiple…", self.open_multiple_dialog)
        recent = menu.addAction("Open recent file", self._open_recent_converted)
        recent.setEnabled(self._recent_converted_path() is not None)
        if self._last_output and self._last_output.exists():
            menu.addAction("Show in folder", self._reveal_result)
        menu.addSeparator()
        menu.addAction("Merge PDFs…", self._merge_pdfs_dialog)
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

    def open_multiple_dialog(self) -> None:
        was_on_top = self._always_on_top
        if was_on_top:
            self._set_always_on_top(False)
        try:
            paths, _ = QFileDialog.getOpenFileNames(
                self,
                f"Open multiple — {APP_NAME}",
                str(Path.home()),
            )
        finally:
            if was_on_top:
                self._set_always_on_top(True)
            self.raise_()
            self.activateWindow()
        if paths:
            QTimer.singleShot(0, lambda p=list(paths): self.load_paths(p))

    @safe_slot(user_message="Could not open those files.")
    def load_paths(self, paths: list) -> None:
        cleaned = [str(p) for p in paths if str(p).strip()]
        if not cleaned:
            return
        if len(cleaned) == 1:
            self.load_path(cleaned[0])
            return
        if self.jobs.is_busy:
            self._set_status("Busy — cancel first (right-click)", "err")
            return
        detected_list: list[tuple[Path, DetectedFile]] = []
        for raw in cleaned:
            try:
                path = Path(raw).resolve()
                detected_list.append((path, detect_file(path)))
            except AppError as exc:
                self._set_status(exc.user_message, "err")
                return
            except OSError as exc:
                self._set_status(f"Could not read file: {exc}", "err")
                return
        formats = {d.format_id for _, d in detected_list}
        if len(formats) != 1:
            self._set_status("Batch needs the same file type", "err")
            return
        first_path, first_det = detected_list[0]
        self._batch_paths = [p for p, _ in detected_list]
        self.load_path(str(first_path))
        # Restore batch list after load_path clears it
        self._batch_paths = [p for p, _ in detected_list]
        n = len(self._batch_paths)
        self.wheel.set_center_text(
            f"{n} files",
            f"{first_det.format_id.label} · batch",
        )
        self._set_status(f"Batch · {n} files — pick a conversion", "info")

    @safe_slot(user_message="Could not open that file.")
    def load_path(self, path: str) -> None:
        if self.jobs.is_busy:
            self._set_status("Busy — cancel first (right-click)", "err")
            return
        self._batch_paths = []
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
            # Include ops that need FFmpeg/LibreOffice even if not installed yet,
            # so choosing them can offer a one-click winget/apt install.
            ops = self.registry.available_operations_for(
                detected.format_id, include_unavailable=True
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("registry lookup failed: %s", exc)
            ops = []

        wheel_ops, overflow = split_wheel_actions(ops)
        self._current_ops = ops
        self._overflow_ops = overflow
        labels = [op.segment_label for op in wheel_ops]
        log.info(
            "Loaded %s → %d ops (%d on wheel, %d overflow): %s",
            detected.format_id,
            len(ops),
            len(wheel_ops),
            len(overflow),
            labels,
        )

        # Prefer original filename for display (not a truncated stem-only guess).
        display_name = self._source_path.name
        # Expand from center-only hub to the full format wheel.
        self._set_orb_size(ORB_SIZE)
        self.wheel.set_operations(wheel_ops)
        self.wheel.set_has_file(True)
        self.wheel.set_center_text(
            display_name,
            f"{detected.format_id.label} · {format_size(detected.size_bytes)}",
        )
        self.wheel.set_wheel_enabled(bool(wheel_ops))

        # Do not repeat format names here — pads already show them.
        if not ops:
            self._set_status(f"No conversions for {detected.format_id.label}", "err")
        else:
            self._set_status("", "info")  # clear banner; hub says "drag to a pad"

    def _on_format_selected_deferred(self, operation_id: str) -> None:
        QTimer.singleShot(0, lambda: self._on_format_selected(operation_id))

    @safe_slot(user_message="Couldn't start that conversion.")
    def _on_format_selected(self, operation_id: str) -> None:
        if not self.detected or not self._source_path:
            return
        if self.jobs.is_busy:
            self._set_status("Already converting…", "info")
            return
        if operation_id == "ui.more_actions":
            self._show_more_actions_menu()
            return
        try:
            op = self.registry.get_operation(operation_id)
        except AppError as exc:
            self._set_status(exc.user_message, "err")
            return

        self._selected_op = op
        if not self._ensure_engines_for_operation(op):
            return
        settings = self._default_settings(op)

        # Merge+ pad: pick additional PDFs then save once.
        if op.operation_id == "pdf.merge":
            extras = self._pick_merge_extras()
            if extras is None:
                self._set_status("Cancelled", "info")
                return
            if not extras:
                self._set_status("Pick at least one more PDF to merge", "err")
                return
            settings["merge_paths"] = [str(p) for p in extras]

        if op.operation_id == "image.crop" and self._source_path is not None:
            if len(self._batch_paths) > 1:
                self._set_status("Crop works on one image at a time", "err")
                return
            from omniconvert.ui.crop_dialog import ImageCropDialog

            try:
                popup = ImageCropDialog(self._source_path, None)
            except Exception:  # noqa: BLE001
                log.exception("Crop preview failed")
                self._set_status("Could not open crop preview for that image.", "err")
                return
            popup.setStyleSheet(self.styleSheet())
            if popup.exec() != QDialog.DialogCode.Accepted:
                self._set_status("Cancelled", "info")
                return
            settings.update(popup.values())
        elif op.settings and op.operation_id != "pdf.merge":
            popup = _OptionsPopup(op, self.settings, None)
            popup.setStyleSheet(self.styleSheet())
            if popup.exec() != QDialog.DialogCode.Accepted:
                self._set_status("Cancelled", "info")
                return
            settings.update(popup.values())

        batch = [p for p in self._batch_paths if p.is_file()]
        use_batch = len(batch) > 1 and op.supports_batch and op.operation_id != "pdf.merge"
        if len(batch) > 1 and not use_batch and op.operation_id != "pdf.merge":
            self._set_status("That conversion does not support batch", "err")
            return

        default_dir = self._output_dir or self._source_path.parent
        if use_batch:
            out_dir = QFileDialog.getExistingDirectory(
                None,
                f"Output folder for {len(batch)} files — {APP_NAME}",
                str(default_dir),
            )
            if not out_dir:
                self._set_status("Cancelled", "info")
                return
            out_path = Path(out_dir)
            if not is_writable_dir(out_path):
                self._set_status("Output folder is not writable", "err")
                return
            self._output_dir = out_path
            self._start_batch(batch, settings, out_dir=out_path)
            return

        # Always ask for rename + location; default folder = uploaded file path.
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

    def _ensure_engines_for_operation(self, op: ConversionOperation) -> bool:
        """If the op needs FFmpeg/LibreOffice, offer winget/apt install on demand."""
        deps = get_dependency_service()
        deps.refresh(probe_versions=False)
        requires = set(op.requires_external or ())
        needed: list[str] = []
        if "ffmpeg" in requires and not deps.ffmpeg.available:
            needed.append("ffmpeg")
        if "libreoffice" in requires and not deps.libreoffice.available:
            needed.append("libreoffice")
        if not needed:
            return True

        labels = []
        if "ffmpeg" in needed:
            labels.append("FFmpeg (audio/video)")
        if "libreoffice" in needed:
            labels.append("LibreOffice (Office ↔ PDF)")
        pretty = " and ".join(labels)
        manager = "winget" if sys.platform.startswith("win") else "apt"
        reply = QMessageBox.question(
            self,
            "Optional tool needed",
            f"This conversion needs {pretty}.\n\n"
            f"Install now with {manager}? (internet + approval once)\n"
            "You can also skip and pick another format.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._set_status("Install skipped — pick another format", "info")
            return False

        result = run_engine_install_with_ui(self, packages=tuple(needed))
        show_engine_install_result(self, result)
        deps.refresh(probe_versions=True)
        still = []
        if "ffmpeg" in needed and not deps.ffmpeg.available:
            still.append("FFmpeg")
        if "libreoffice" in needed and not deps.libreoffice.available:
            still.append("LibreOffice")
        if still:
            self._set_status(
                f"Still missing {', '.join(still)} — try Settings",
                "err",
            )
            return False
        self._set_status("Tool ready — continuing", "ok")
        return True

    def _show_more_actions_menu(self) -> None:
        """Overflow conversions that did not fit on the orb."""
        if not self._overflow_ops:
            self._set_status("No extra actions", "info")
            return
        menu = QMenu(self)
        menu.setTitle("More conversions")
        for op in self._overflow_ops:
            act = menu.addAction(op.label)
            act.setData(op.operation_id)
        chosen = menu.exec(self.mapToGlobal(self.rect().center()))
        if chosen is None:
            self._set_status("Cancelled", "info")
            QTimer.singleShot(1800, lambda: self._set_status("", "info"))
            return
        op_id = chosen.data()
        if isinstance(op_id, str) and op_id:
            self._on_format_selected(op_id)

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
        self._batch_active = False
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

    def _start_batch(
        self,
        paths: list[Path],
        settings: dict,
        *,
        out_dir: Path,
    ) -> None:
        if not self.detected or not self._selected_op:
            return
        op = self._selected_op
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._set_status(f"Bad output folder: {exc}", "err")
            return
        specs: list[dict] = []
        for path in paths:
            specs.append(
                {
                    "source_path": path,
                    "source_format": self.detected.format_id,
                    "target_format": op.target_format.value,
                    "output_dir": out_dir,
                    "output_name": default_output_name(path, op.target_format),
                    "settings": dict(settings),
                    "operation_id": op.operation_id,
                }
            )
        self._batch_active = True
        self._batch_ok = 0
        self._batch_fail = 0
        try:
            self.jobs.start_batch(specs)
        except RuntimeError as exc:
            self._batch_active = False
            self._set_status(str(exc), "err")

    def _pick_merge_extras(self) -> list[Path] | None:
        """Return additional PDFs, or None if cancelled."""
        was_on_top = self._always_on_top
        if was_on_top:
            self._set_always_on_top(False)
        try:
            paths, _ = QFileDialog.getOpenFileNames(
                self,
                f"Add PDFs to merge — {APP_NAME}",
                str(self._source_path.parent if self._source_path else Path.home()),
                "PDF files (*.pdf)",
            )
        finally:
            if was_on_top:
                self._set_always_on_top(True)
            self.raise_()
            self.activateWindow()
        if paths is None:
            return None
        # Empty list means user closed with no selection — treat as cancel if dialog returns [].
        # getOpenFileNames returns [] on cancel.
        return [Path(p) for p in paths]

    @safe_slot(user_message="Could not merge PDFs.")
    def _merge_pdfs_dialog(self) -> None:
        if self.jobs.is_busy:
            self._set_status("Busy — cancel first (right-click)", "err")
            return
        was_on_top = self._always_on_top
        if was_on_top:
            self._set_always_on_top(False)
        try:
            paths, _ = QFileDialog.getOpenFileNames(
                self,
                f"Merge PDFs — {APP_NAME}",
                str(Path.home()),
                "PDF files (*.pdf)",
            )
        finally:
            if was_on_top:
                self._set_always_on_top(True)
            self.raise_()
            self.activateWindow()
        if not paths or len(paths) < 2:
            self._set_status("Select at least two PDFs to merge", "err")
            return
        first = Path(paths[0])
        try:
            detected = detect_file(first)
        except AppError as exc:
            self._set_status(exc.user_message, "err")
            return
        self.detected = detected
        self._source_path = first.resolve()
        self._batch_paths = []
        try:
            op = self.registry.get_operation("pdf.merge")
        except AppError as exc:
            self._set_status(exc.user_message, "err")
            return
        self._selected_op = op
        settings = self._default_settings(op)
        settings["merge_paths"] = [str(Path(p).resolve()) for p in paths[1:]]
        default_dir = first.parent
        save = SaveAsDialog(
            title="Save merged PDF",
            default_dir=default_dir,
            default_name="merged.pdf",
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

    @safe_slot(user_message="Conversion update failed.")
    def _on_progress(self, job_id: str, fraction: object, message: str) -> None:
        _ = job_id
        if fraction is None:
            self._set_status(message or "Working…", "info")
        else:
            try:
                pct = int(float(fraction) * 100)
            except (TypeError, ValueError):
                pct = 0
            self._set_status(f"{pct}% · {message or 'Working…'}", "info")

    @safe_slot(user_message="Batch update failed.")
    def _on_batch_progress(self, done: int, total: int, message: str) -> None:
        if total <= 0:
            return
        self._set_status(message or f"Batch {done}/{total}", "info")

    @safe_slot(user_message="Saved, but the finish step had a glitch.")
    def _on_success(self, job_id: str, path: str, message: str) -> None:
        _ = job_id, message
        self._last_output = Path(path)
        out = Path(path)
        call_soft(
            lambda: self.settings_store.add_history(
                self.settings,
                source_name=out.name,
                target_format=(
                    self._selected_op.target_format.value if self._selected_op else ""
                ),
                output_path=path,
                status="succeeded",
            )
        )
        if self._batch_active:
            self._batch_ok += 1
            self._set_status(f"Batch · saved {out.name}", "ok")
            return

        self._set_status(f"Done · {out.name}", "ok")
        # Ask whether to open the converted file (Yes / No).
        reply = QMessageBox.question(
            self,
            "Conversion complete",
            f"Saved:\n{out.name}\n\nOpen the file now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes and out.exists():
            try:
                open_path(out)
            except Exception:  # noqa: BLE001
                log.exception("open_path after convert failed")
                self._set_status("Saved — could not open the file automatically.", "info")
        else:
            QTimer.singleShot(2500, lambda: self._set_status("Right-click · open result", "info"))

    @safe_slot(user_message="Conversion failed.")
    def _on_failure(self, job_id: str, message: str) -> None:
        _ = job_id
        if self._batch_active:
            self._batch_fail += 1
        self._set_status(message or "Conversion failed.", "err")
        call_soft(
            lambda: self.settings_store.add_history(
                self.settings,
                source_name=self.detected.display_name if self.detected else "",
                target_format=(
                    self._selected_op.target_format.value if self._selected_op else ""
                ),
                output_path="",
                status="failed",
            )
        )

    @safe_slot(user_message="Cancelled.")
    def _on_cancelled(self, job_id: str) -> None:
        _ = job_id
        self._batch_active = False
        self._set_status("Cancelled", "info")

    @safe_slot(user_message="UI update glitch — keep going.")
    def _on_busy(self, busy: bool) -> None:
        self.wheel.set_wheel_enabled(not busy and bool(self._current_ops))
        if busy:
            self._set_status("Converting…", "info")
            return
        if self._batch_active:
            ok, fail = self._batch_ok, self._batch_fail
            self._batch_active = False
            self._batch_paths = []
            summary = f"Batch done · {ok} ok"
            if fail:
                summary += f", {fail} failed"
            self._set_status(summary, "ok" if fail == 0 else "err")
            if self._last_output and self._last_output.exists() and ok > 0:
                reply = QMessageBox.question(
                    self,
                    "Batch complete",
                    f"{summary}.\n\nOpen the last output file?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        open_path(self._last_output)
                    except Exception:  # noqa: BLE001
                        log.exception("open_path after batch failed")

    def _set_status(self, text: str, kind: str) -> None:
        self._status_text = text
        self._status_kind = kind
        # Banner lives on the wheel (inside the circle).
        # "ok" uses black — green was hard to read on the blue pad ring.
        color = {"ok": "#0f172a", "err": "#b91c1c", "info": "#334155"}.get(kind, "#334155")
        self.wheel.set_banner(text, color)
        # Auto-clear transient banners so "Cancelled" does not stick over chips.
        lowered = (text or "").strip().lower()
        if lowered in {"cancelled", "canceled"} or (
            kind == "info" and lowered.startswith("cancelled")
        ):
            QTimer.singleShot(1600, lambda: self._clear_transient_banner(text))

    def _clear_transient_banner(self, expected: str) -> None:
        if self._status_text == expected:
            self._set_status("", "info")

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
                ops = self.registry.available_operations_for(
                    self.detected.format_id, include_unavailable=True
                )
                wheel_ops, overflow = split_wheel_actions(ops)
                self._current_ops = ops
                self._overflow_ops = overflow
                self.wheel.set_operations(wheel_ops)
            self._set_status("Settings saved", "ok")

    def open_about(self) -> None:
        AboutDialog(self).exec()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._last_output:
            self._open_result()
            return
        super().mouseDoubleClickEvent(event)
