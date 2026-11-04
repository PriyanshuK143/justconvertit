# -*- mode: python ; coding: utf-8 -*-
# Build on Windows after: pip install -r requirements-release.txt && pip install -e .
#   pyinstaller --noconfirm --clean packaging/windows/omniconvert.spec
#
# Bundles the Python runtime + app deps. Does NOT bundle LibreOffice or FFmpeg.
# No updater, network client, or telemetry is included.

from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH).resolve().parents[1]
RTHOOK = str(ROOT / "packaging" / "rthooks" / "pyi_rth_omniconvert_stdio.py")

# Heavy / unused modules — keep the Setup.exe smaller for friends.
EXCLUDES = [
    "pandas",
    "numpy",
    "matplotlib",
    "scipy",
    "tkinter",
    "unittest",
    "pytest",
    "pygments",
    "py",
    "IPython",
    "notebook",
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtDesigner",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtHttpServer",
    "PySide6.QtRemoteObjects",
]

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
        "omniconvert.converters.image_pillow",
        "omniconvert.converters.tabular",
        "omniconvert.converters.text_ops",
        "omniconvert.converters.pdf_ops",
        "omniconvert.converters.office_pure",
        "omniconvert.converters.office_libreoffice",
        "omniconvert.converters.media_ffmpeg",
        "omniconvert.converters.svg_inkscape",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[RTHOOK],
    excludes=EXCLUDES,
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
    # Do not dump source paths / line numbers to end users.
    disable_windowed_traceback=True,
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
