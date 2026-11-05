#!/usr/bin/env python3
"""Build Windows (.ico) and Linux/app (.png) icons from the master brand art."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE_CANDIDATES = (
    ROOT / "Glossy File Conversion App Icon.png",
    ROOT / "src" / "omniconvert" / "resources" / "app-icon-source.png",
)
RES = ROOT / "src" / "omniconvert" / "resources"
WIN = ROOT / "packaging" / "windows"

# Standard Windows ICO sizes (taskbar / Start / Explorer).
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
# Freedesktop hicolor sizes used by the Ubuntu .deb / menu.
HICOLOR_SIZES = (48, 128, 256, 512)


def _load_source() -> Image.Image:
    for path in SOURCE_CANDIDATES:
        if path.is_file():
            im = Image.open(path).convert("RGBA")
            print(f"source: {path} ({im.size[0]}x{im.size[1]})")
            return im
    raise SystemExit(
        "No brand icon found. Place "
        "'Glossy File Conversion App Icon.png' in the repo root."
    )


def _square_resize(im: Image.Image, size: int) -> Image.Image:
    return im.resize((size, size), Image.Resampling.LANCZOS)


def main() -> int:
    src = _load_source()
    RES.mkdir(parents=True, exist_ok=True)
    WIN.mkdir(parents=True, exist_ok=True)

    # Keep a space-free master next to the generated assets.
    master = RES / "app-icon-source.png"
    if src.size != (1254, 1254):
        # Preserve full fidelity; only re-encode if we loaded the glossy file.
        pass
    src.save(master, format="PNG", optimize=True)

    # In-app / PyInstaller PNG (high-res; Qt scales down).
    app_png = RES / "omniconvert.png"
    _square_resize(src, 512).save(app_png, format="PNG", optimize=True)
    print(f"wrote {app_png.relative_to(ROOT)}")

    # Multi-size Windows ICO (resources + Inno/PyInstaller packaging copy).
    # Pillow resizes from the largest frame when sizes= is passed.
    master_256 = _square_resize(src, 256)
    for dest in (RES / "omniconvert.ico", WIN / "omniconvert.ico"):
        master_256.save(dest, format="ICO", sizes=ICO_SIZES)
        print(f"wrote {dest.relative_to(ROOT)}")

    # Per-size PNGs for Ubuntu hicolor theme folders.
    hicolor = RES / "hicolor"
    for size in HICOLOR_SIZES:
        out = hicolor / f"{size}x{size}" / "apps" / "justconvertit.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        _square_resize(src, size).save(out, format="PNG", optimize=True)
        print(f"wrote {out.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
