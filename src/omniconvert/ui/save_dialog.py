"""Popup to choose output folder and filename before conversion."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class SaveAsDialog(QDialog):
    """Rename + location chooser. Defaults to the uploaded file's folder."""

    def __init__(
        self,
        *,
        title: str,
        default_dir: Path,
        default_name: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save converted file")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        heading = QLabel(title)
        heading.setObjectName("appTitle")
        root.addWidget(heading)

        hint = QLabel("Choose where to save. Defaults to the uploaded file’s folder.")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        root.addWidget(hint)

        form = QFormLayout()
        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(str(default_dir))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        folder_row.addWidget(self.folder_edit, stretch=1)
        folder_row.addWidget(browse)
        form.addRow("Folder", folder_row)

        self.name_edit = QLineEdit(default_name)
        self.name_edit.selectAll()
        form.addRow("File name", self.name_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        if parent is not None:
            self.setStyleSheet(parent.styleSheet())

    def _browse(self) -> None:
        start = self.folder_edit.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Output folder", start)
        if path:
            self.folder_edit.setText(path)

    def _accept(self) -> None:
        folder = self.folder_edit.text().strip()
        name = self.name_edit.text().strip()
        if not folder or not name:
            return
        if "/" in name or "\\" in name:
            self.name_edit.setFocus()
            return
        self.accept()

    def result_path_parts(self) -> tuple[Path, str]:
        return Path(self.folder_edit.text().strip()), self.name_edit.text().strip()
