# Project status

Last updated: 2026-10-29

## Product posture

| Guarantee | Status |
|-----------|--------|
| One-time install / offline-first | Done — see `docs/PRODUCT.md`, `src/omniconvert/product.py` |
| No in-app updater / telemetry / accounts | Done — enforced by policy tests |
| Standalone Windows + Ubuntu artifacts | Scaffold + Linux binary build path; Windows needs Windows host/CI |
| Pinned release dependencies | Done — `requirements-release.txt` |
| Privacy / platforms / rebuild docs | Done |

## Implemented

| Area | Status | Notes |
|------|--------|-------|
| Project skeleton / packaging metadata | Done | `pyproject.toml`, MIT license |
| Content detection | Done | Magic bytes + text/JSON/CSV heuristics |
| Conversion registry | Done | UI reads operations from registry only |
| Image conversions (Pillow) | Done | PNG/JPEG/WEBP/BMP/TIFF + PDF |
| Tabular (CSV/JSON/XLSX) | Done | pandas + openpyxl |
| Text ops | Done | Pretty JSON; TXT/JSON → PDF |
| PDF ops | Done | Extract text, page→PNG/JPEG, pages→ZIP (no split UI) |
| Office pure Python | Done | DOCX↔TXT, DOCX/PPTX→PDF text, PPTX→TXT |
| Background jobs | Done | QThread worker; cancel flag |
| Radial wheel UI | Done | Hit-test, hover, click, keyboard, DnD |
| Desktop orb widget | Done | Frameless always-on-top |
| Settings / history | Done | Per-user local JSON only |
| LibreOffice / FFmpeg adapters | Done | Local detection + optional first-run apt/winget |
| Security limits (zip/PDF/atomic LO) | Done | Safe ZIP open, PDF render caps, atomic LO writes |
| Dependency CVE pins (pypdf/Pillow) | Done | pypdf 6.21.4, Pillow 13.0.0; CI pip-audit |
| SECURITY.md | Done | Honest residual risk + audit steps |
| Offline policy tests | Done | Forbidden imports + portable ops |
| Linux PyInstaller | Done | `scripts/build_linux.sh` + `verify_offline.sh` |
| Windows paths / DPI / deps service | Done | Custom exe paths; high-DPI; icon |
| Windows PyInstaller + Inno | Scaffold | Scripts + Inno ready; **not executed on this Linux host** |
| pyside6-deploy evaluation | Documented | PyInstaller remains primary; example spec provided |
| GitHub Actions | Scaffold | test + artifact upload (no auto-update channel) |

## Not implemented / limitations

- OCR / scanned-PDF text
- Pixel-perfect Office layout without LibreOffice
- Bundled FFmpeg/LibreOffice binaries
- Verified Windows installer on Linux host
- AppImage/.deb fully automated packaging
- Forever-compatibility with untested future OS releases

## Distinguishing claims

Only conversions registered with `tested=True` and whose converter `is_available()` are shown on the wheel.
