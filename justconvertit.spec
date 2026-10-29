# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/omniconvert/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[('docs/THIRD_PARTY_NOTICES.md', 'docs'), ('docs/PRIVACY.md', 'docs'), ('LICENSE', '.')],
    hiddenimports=['omniconvert.converters.image_pillow', 'omniconvert.converters.tabular', 'omniconvert.converters.text_ops', 'omniconvert.converters.pdf_ops', 'omniconvert.converters.office_pure', 'omniconvert.converters.office_libreoffice', 'omniconvert.converters.media_ffmpeg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngine', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='justconvertit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='justconvertit',
)
