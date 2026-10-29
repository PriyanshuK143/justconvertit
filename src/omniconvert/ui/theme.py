"""Application stylesheets — light (default) and dark."""

from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication


_COMBO_LIGHT = """
QComboBox {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 22px;
    color: #111827;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QComboBox:hover {
    border-color: #3b82f6;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    background: transparent;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    outline: 0;
    padding: 4px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QComboBox QAbstractItemView::item {
    min-height: 30px;
    padding: 6px 12px;
    color: #111827;
    background-color: #ffffff;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #dbeafe;
    color: #111827;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
"""

_COMBO_DARK = """
QComboBox {
    background-color: #111827;
    border: 1px solid #4b5563;
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 22px;
    color: #f9fafb;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QComboBox:hover {
    border-color: #60a5fa;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    background: transparent;
}
QComboBox QAbstractItemView {
    background-color: #111827;
    color: #f9fafb;
    border: 1px solid #4b5563;
    border-radius: 8px;
    outline: 0;
    padding: 4px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QComboBox QAbstractItemView::item {
    min-height: 30px;
    padding: 6px 12px;
    color: #f9fafb;
    background-color: #111827;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #1e3a5f;
    color: #f9fafb;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
"""

LIGHT_QSS = f"""
QWidget {{
    color: #1f2933;
    font-family: "Segoe UI", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 12px;
}}
QWidget#desktopOrb {{
    background: transparent;
}}
QDialog {{
    background-color: #f8fafc;
    color: #1f2933;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}}
QLabel {{
    color: #1f2933;
    background: transparent;
}}
QLabel#appTitle {{
    font-size: 16px;
    font-weight: 600;
    color: #0f172a;
}}
QLabel#sectionTitle {{
    font-size: 12px;
    font-weight: 600;
    color: #334155;
    padding-top: 8px;
}}
QLabel#subtitle {{
    color: #64748b;
    font-size: 11px;
}}
QLabel#statusOk {{ color: #15803d; background: transparent; }}
QLabel#statusErr {{ color: #b91c1c; background: transparent; }}
QLabel#statusInfo {{ color: #4b5563; background: transparent; }}
QLabel#progressChip {{
    color: #1d4ed8;
    background: transparent;
    font-size: 11px;
}}
QPushButton {{
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 14px;
    color: #0f172a;
}}
QPushButton:hover {{
    background-color: #eff6ff;
    border-color: #3b82f6;
}}
QPushButton:pressed {{
    background-color: #e2e8f0;
}}
QPushButton:disabled {{
    color: #94a3b8;
    background-color: #f1f5f9;
}}
QPushButton#primaryButton {{
    background-color: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#primaryButton:hover {{
    background-color: #1d4ed8;
    border-color: #1d4ed8;
    color: #ffffff;
}}
QPushButton#orbClose {{
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 14px;
    padding: 0;
    font-size: 16px;
    font-weight: 600;
    color: #374151;
}}
QPushButton#orbClose:hover {{
    background-color: #ef4444;
    border-color: #ef4444;
    color: #ffffff;
}}
QLineEdit, QSpinBox {{
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 7px 10px;
    min-height: 20px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    color: #0f172a;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: #2563eb;
}}
QLineEdit:disabled, QSpinBox:disabled {{
    background-color: #f1f5f9;
    color: #94a3b8;
}}
{_COMBO_LIGHT}
QMenu {{
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px;
    color: #0f172a;
}}
QMenu::item {{
    padding: 8px 18px;
    border-radius: 6px;
    color: #0f172a;
}}
QMenu::item:selected {{
    background-color: #2563eb;
    color: #ffffff;
}}
QMenu::item:disabled {{
    color: #94a3b8;
}}
QMessageBox {{
    background-color: #ffffff;
}}
QDialogButtonBox QPushButton {{
    min-width: 84px;
}}
QFormLayout {{
    color: #1f2933;
}}
"""

DARK_QSS = f"""
QWidget {{
    color: #e5e7eb;
    font-family: "Segoe UI", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 12px;
}}
QWidget#desktopOrb {{
    background: transparent;
}}
QDialog {{
    background-color: #0f172a;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 12px;
}}
QLabel {{
    color: #e5e7eb;
    background: transparent;
}}
QLabel#appTitle {{
    font-size: 16px;
    font-weight: 600;
    color: #f8fafc;
}}
QLabel#sectionTitle {{
    font-size: 12px;
    font-weight: 600;
    color: #cbd5e1;
    padding-top: 8px;
}}
QLabel#subtitle {{
    color: #94a3b8;
    font-size: 11px;
}}
QLabel#statusOk {{ color: #4ade80; background: transparent; }}
QLabel#statusErr {{ color: #f87171; background: transparent; }}
QLabel#statusInfo {{ color: #9ca3af; background: transparent; }}
QLabel#progressChip {{
    color: #93c5fd;
    background: transparent;
    font-size: 11px;
}}
QPushButton {{
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 8px 14px;
    color: #f1f5f9;
}}
QPushButton:hover {{
    background-color: #334155;
    border-color: #60a5fa;
}}
QPushButton:pressed {{
    background-color: #0f172a;
}}
QPushButton:disabled {{
    color: #64748b;
    background-color: #1e293b;
}}
QPushButton#primaryButton {{
    background-color: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#primaryButton:hover {{
    background-color: #3b82f6;
    border-color: #3b82f6;
    color: #ffffff;
}}
QPushButton#orbClose {{
    background-color: #334155;
    border: 1px solid #475569;
    border-radius: 14px;
    padding: 0;
    font-size: 16px;
    font-weight: 600;
    color: #e5e7eb;
}}
QPushButton#orbClose:hover {{
    background-color: #ef4444;
    border-color: #ef4444;
    color: #ffffff;
}}
QLineEdit, QSpinBox {{
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 7px 10px;
    min-height: 20px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    color: #f8fafc;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: #60a5fa;
}}
QLineEdit:disabled, QSpinBox:disabled {{
    background-color: #0f172a;
    color: #64748b;
}}
{_COMBO_DARK}
QMenu {{
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 4px;
    color: #f1f5f9;
}}
QMenu::item {{
    padding: 8px 18px;
    border-radius: 6px;
    color: #f1f5f9;
}}
QMenu::item:selected {{
    background-color: #2563eb;
    color: #ffffff;
}}
QMenu::item:disabled {{
    color: #64748b;
}}
QMessageBox {{
    background-color: #0f172a;
}}
QDialogButtonBox QPushButton {{
    min-width: 84px;
}}
"""


def system_prefers_dark() -> bool:
    """Best-effort OS appearance probe (Windows/Linux via Qt)."""
    try:
        hints = QGuiApplication.styleHints()
        scheme = hints.colorScheme()
        return int(scheme) == 1
    except Exception:
        if sys.platform.startswith("win"):
            return False
        return False


def resolve_theme(preference: str) -> str:
    pref = (preference or "system").strip().lower()
    if pref in {"light", "dark"}:
        return pref
    return "dark" if system_prefers_dark() else "light"


def stylesheet_for(preference: str) -> str:
    return DARK_QSS if resolve_theme(preference) == "dark" else LIGHT_QSS


def apply_theme(app: QApplication, preference: str) -> None:
    app.setStyleSheet(stylesheet_for(preference))
