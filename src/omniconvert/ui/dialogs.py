"""Settings and About dialogs."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from omniconvert.product import ABOUT_BLURB, APP_NAME, PRIVACY_SUMMARY
from omniconvert.services.dependencies import get_dependency_service
from omniconvert.services.engine_setup import (
    EngineSetupResult,
    install_engines,
    install_recommended_engines,
    linux_manual_hint,
    windows_manual_hint,
)
from omniconvert.services.settings import AppSettings
from omniconvert.ui.theme import apply_theme, resolve_theme
from omniconvert.version import __version__


class _EngineInstallWorker(QThread):
    finished_result = Signal(object)

    def __init__(
        self,
        packages: tuple[str, ...] = ("ffmpeg", "libreoffice"),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._packages = packages

    def run(self) -> None:  # noqa: N802
        if set(self._packages) == {"ffmpeg", "libreoffice"}:
            self.finished_result.emit(install_recommended_engines())
        else:
            self.finished_result.emit(install_engines(self._packages))


def run_engine_install_with_ui(
    parent: QWidget | None = None,
    *,
    packages: tuple[str, ...] = ("ffmpeg", "libreoffice"),
) -> EngineSetupResult:
    """Show a blocking progress dialog while apt/winget installs optional engines."""
    labels = []
    if "ffmpeg" in packages:
        labels.append("FFmpeg")
    if "libreoffice" in packages:
        labels.append("LibreOffice")
    label = " and ".join(labels) if labels else "optional tools"
    manager = "winget" if sys.platform.startswith("win") else "apt"
    progress = QProgressDialog(
        f"Installing {label} via {manager}…\n"
        "Needs internet. Windows may show a winget / UAC prompt.",
        None,
        0,
        0,
        parent,
    )
    progress.setWindowTitle("Installing tools")
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.setCancelButton(None)
    progress.show()
    QApplication.processEvents()

    worker = _EngineInstallWorker(packages=packages, parent=parent)
    result_box: list[EngineSetupResult] = []

    def _done(result: object) -> None:
        if isinstance(result, EngineSetupResult):
            result_box.append(result)
        progress.close()

    worker.finished_result.connect(_done)
    worker.start()
    while worker.isRunning():
        QApplication.processEvents()
        worker.wait(50)

    if result_box:
        return result_box[0]
    return EngineSetupResult(ok=False, message="Install did not finish.")


def show_engine_install_result(parent: QWidget | None, result: EngineSetupResult) -> None:
    if result.ok:
        QMessageBox.information(parent, "Tools ready", result.message)
        return
    text = result.message
    if result.command_hint:
        text = f"{text}\n\n{result.command_hint}"
    if result.detail:
        text = f"{text}\n\n{result.detail[:400]}"
    QMessageBox.warning(parent, "Install incomplete", text)


class FirstRunEnginesDialog(QDialog):
    """One-time prompt to install LibreOffice + FFmpeg via the OS package manager."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Recommended tools")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)

        title = QLabel("Install recommended tools?")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        body = QLabel(
            f"Optional: {APP_NAME} can install LibreOffice and FFmpeg with apt "
            "for Office↔PDF and audio/video conversions.\n\n"
            "• Needs internet and your password once\n"
            f"• Stays on the system if you uninstall {APP_NAME}\n"
            "• Skip anytime — core image/PDF/document tools already work offline\n\n"
            "On Windows this prompt is skipped; tools install only when you use a "
            "feature that needs them (or from Settings)."
        )
        body.setWordWrap(True)
        layout.addWidget(body)

        if sys.platform.startswith("linux"):
            hint = QLabel(f"Command used: {linux_manual_hint()}")
        elif sys.platform.startswith("win"):
            hint = QLabel(f"Uses winget:\n{windows_manual_hint()}")
        else:
            hint = QLabel("Automatic install is not available on this platform.")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(hint)

        buttons = QDialogButtonBox()
        install_btn = buttons.addButton(
            "Install recommended tools", QDialogButtonBox.ButtonRole.AcceptRole
        )
        install_btn.setObjectName("primaryButton")
        buttons.addButton("Skip for now", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def _style_combo_popup(combo: QComboBox, *, dark: bool) -> None:
    """Force readable popup colors (Linux themes often ignore QSS on the view)."""
    view = combo.view()
    if view is None:
        return
    if dark:
        bg, fg, sel_bg, sel_fg = "#111827", "#f9fafb", "#2563eb", "#ffffff"
    else:
        bg, fg, sel_bg, sel_fg = "#ffffff", "#111827", "#2563eb", "#ffffff"
    view.setStyleSheet(
        f"""
        QAbstractItemView {{
            background-color: {bg};
            color: {fg};
            border: 1px solid {'#4b5563' if dark else '#d0d7de'};
            outline: 0;
            padding: 4px;
        }}
        QAbstractItemView::item {{
            min-height: 30px;
            padding: 6px 12px;
            color: {fg};
            background-color: {bg};
        }}
        QAbstractItemView::item:hover {{
            background-color: {'#1e3a5f' if dark else '#dbeafe'};
            color: {fg};
        }}
        QAbstractItemView::item:selected {{
            background-color: {sel_bg};
            color: {sel_fg};
        }}
        """
    )
    pal = view.palette()
    pal.setColor(QPalette.ColorRole.Base, QColor(bg))
    pal.setColor(QPalette.ColorRole.Text, QColor(fg))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(sel_bg))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(sel_fg))
    view.setPalette(pal)
    combo.setPalette(pal)


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self.setMinimumHeight(460)
        self._settings = settings
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)

        title = QLabel("Settings")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        general = QLabel("General")
        general.setObjectName("sectionTitle")
        layout.addWidget(general)

        row = QHBoxLayout()
        self.output_edit = QLineEdit(settings.default_output_dir)
        self.output_edit.setPlaceholderText("Same folder as the original file")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.output_edit, stretch=1)
        row.addWidget(browse)
        form.addRow("Default output folder", row)

        self.quality = QSpinBox()
        self.quality.setRange(1, 95)
        self.quality.setValue(settings.jpeg_quality)
        self.quality.setToolTip("Higher looks better; files get larger.")
        form.addRow("JPEG quality", self.quality)

        self.bg = QLineEdit(settings.transparency_background)
        self.bg.setPlaceholderText("#FFFFFF")
        self.bg.setToolTip("Fill color when saving transparent images as JPEG.")
        form.addRow("Transparency background", self.bg)

        self.theme = QComboBox()
        self.theme.setMinimumHeight(34)
        self.theme.addItem("Match system", "system")
        self.theme.addItem("Light", "light")
        self.theme.addItem("Dark", "dark")
        idx = max(0, self.theme.findData(settings.theme or "system"))
        self.theme.setCurrentIndex(idx)
        self.theme.currentIndexChanged.connect(self._preview_theme)
        form.addRow("Theme", self.theme)

        layout.addLayout(form)

        engines = QLabel("Optional tools")
        engines.setObjectName("sectionTitle")
        layout.addWidget(engines)

        eng_form = QFormLayout()
        eng_form.setSpacing(10)
        eng_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.lo_edit = QLineEdit(settings.libreoffice_path)
        self.lo_edit.setPlaceholderText("Auto: /usr/bin/soffice — or browse")
        lo_row = QHBoxLayout()
        lo_browse = QPushButton("Browse…")
        lo_browse.clicked.connect(lambda: self._browse_exe(self.lo_edit, "LibreOffice"))
        lo_row.addWidget(self.lo_edit, stretch=1)
        lo_row.addWidget(lo_browse)
        eng_form.addRow("LibreOffice", lo_row)

        self.ff_edit = QLineEdit(settings.ffmpeg_path)
        self.ff_edit.setPlaceholderText("Auto-detect, or choose ffmpeg")
        ff_row = QHBoxLayout()
        ff_browse = QPushButton("Browse…")
        ff_browse.clicked.connect(lambda: self._browse_exe(self.ff_edit, "FFmpeg"))
        ff_row.addWidget(self.ff_edit, stretch=1)
        ff_row.addWidget(ff_browse)
        eng_form.addRow("FFmpeg", ff_row)
        layout.addLayout(eng_form)

        self.deps = QLabel(self._deps_text())
        self.deps.setWordWrap(True)
        self.deps.setObjectName("subtitle")
        self.deps.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.deps)

        actions = QHBoxLayout()
        refresh = QPushButton("Re-check tools")
        refresh.setToolTip("Look again for LibreOffice and FFmpeg.")
        refresh.clicked.connect(self._refresh_deps)
        install_ff = QPushButton("Install FFmpeg…")
        install_ff.setToolTip(
            "Install FFmpeg only via winget (Windows) or apt (Linux). "
            "Needed for audio/video conversions."
        )
        install_ff.clicked.connect(lambda: self._install_engines(("ffmpeg",)))
        install_lo = QPushButton("Install LibreOffice…")
        install_lo.setToolTip(
            "Install LibreOffice via winget/apt. Needed for high-fidelity Office↔PDF."
        )
        install_lo.clicked.connect(lambda: self._install_engines(("libreoffice",)))
        clear = QPushButton("Clear recent history")
        clear.clicked.connect(self._clear_history)
        actions.addWidget(refresh)
        actions.addWidget(install_ff)
        actions.addWidget(install_lo)
        actions.addWidget(clear)
        layout.addLayout(actions)

        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setObjectName("primaryButton")
            ok_btn.setText("Save")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._style_theme_combo()

    def _style_theme_combo(self) -> None:
        dark = resolve_theme(str(self.theme.currentData() or "system")) == "dark"
        _style_combo_popup(self.theme, dark=dark)

    def _preview_theme(self) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, str(self.theme.currentData() or "system"))
        self._style_theme_combo()

    def _deps_text(self) -> str:
        return get_dependency_service().summary_text()

    def _apply_path_overrides(self, *, probe_versions: bool = False) -> None:
        get_dependency_service().configure(
            libreoffice_path=self.lo_edit.text().strip(),
            ffmpeg_path=self.ff_edit.text().strip(),
            probe_versions=probe_versions,
        )
        self.deps.setText(self._deps_text())

    def _refresh_deps(self) -> None:
        self._apply_path_overrides(probe_versions=True)

    def _install_engines(self, packages: tuple[str, ...] = ("ffmpeg", "libreoffice")) -> None:
        result = run_engine_install_with_ui(self, packages=packages)
        self._apply_path_overrides(probe_versions=True)
        show_engine_install_result(self, result)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Default output folder")
        if path:
            self.output_edit.setText(path)

    def _browse_exe(self, target: QLineEdit, label: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {label} executable",
            str(Path.home()),
            "Executables (*.exe);;All files (*)"
            if __import__("sys").platform.startswith("win")
            else "All files (*)",
        )
        if path:
            target.setText(path)
            self._apply_path_overrides()

    def _clear_history(self) -> None:
        self._settings.recent_history = []

    def reject(self) -> None:  # noqa: N802
        # Restore theme if user cancels after previewing.
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, self._settings.theme)
        super().reject()

    def result_settings(self) -> AppSettings:
        self._settings.default_output_dir = self.output_edit.text().strip()
        self._settings.jpeg_quality = self.quality.value()
        self._settings.transparency_background = self.bg.text().strip() or "#FFFFFF"
        self._settings.theme = str(self.theme.currentData() or "system")
        self._settings.libreoffice_path = self.lo_edit.text().strip()
        self._settings.ffmpeg_path = self.ff_edit.text().strip()
        self._apply_path_overrides(probe_versions=False)
        return self._settings


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)
        title = QLabel(f"{APP_NAME} {__version__}")
        title.setObjectName("appTitle")
        layout.addWidget(title)
        body = QLabel(ABOUT_BLURB)
        body.setWordWrap(True)
        layout.addWidget(body)
        privacy = QLabel(PRIVACY_SUMMARY)
        privacy.setWordWrap(True)
        privacy.setObjectName("subtitle")
        layout.addWidget(privacy)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setObjectName("primaryButton")
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
