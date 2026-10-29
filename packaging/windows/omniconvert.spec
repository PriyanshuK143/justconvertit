# -*- mode: python ; coding: utf-8 -*-
# Build on Windows after: pip install -r requirements-release.txt && pip install -e .
#   pyinstaller --noconfirm --clean packaging/windows/omniconvert.spec
#
# Bundles the Python runtime + app deps. Does NOT bundle LibreOffice or FFmpeg.
# No updater, network client, or telemetry is included.

from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH).resolve().parents[1]

a = Analysis(
    [str(ROOT / "src" / "omniconvert" / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(ROOT / "docs" / "THIRD_PARTY_NOTICES.md"), "docs"),
        (str(ROOT / "docs" / "PRIVACY.md"), "docs"),
        (str(ROOT / "LICENSE"), "."),
        (str(ROOT / "src" / "omniconvert" / "resources" / "omniconvert.png"), "omniconvert/resources"),
        (str(ROOT / "src" / "omniconvert" / "resources" / "omniconvert.ico"), "omniconvert/resources"),
    ],
    hiddenimports=[
        "PIL._tkinter_finder",
        "omniconvert.converters.image_pillow",
        "omniconvert.converters.tabular",
        "omniconvert.converters.text_ops",
        "omniconvert.converters.pdf_ops",
        "omniconvert.converters.office_pure",
        "omniconvert.converters.office_libreoffice",
        "omniconvert.converters.media_ffmpeg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "pytest",
        "pygments",
        "py",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="justconvertit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "packaging" / "windows" / "omniconvert.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="justconvertit",
)
