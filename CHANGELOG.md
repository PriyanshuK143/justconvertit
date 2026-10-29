# Changelog

## 0.1.0 — 2026-10-29

### Added
- PySide6 desktop UI with custom radial conversion wheel
- Content-based file detection and conversion registry
- Image conversions via Pillow (PNG, JPEG, WEBP, BMP, TIFF)
- CSV/JSON/XLSX conversions via pandas and openpyxl
- Text/JSON utilities and PDF create/extract via ReportLab, pypdf, pypdfium2
- Pure-Python DOCX/PPTX text conversions
- Optional LibreOffice (Office → PDF) and FFmpeg (audio/video) when installed locally
- Background jobs, settings, recent history, batch queue
- pytest unit and integration tests, including offline-policy checks
- Packaging scaffolds for Windows (PyInstaller + Inno Setup) and Linux (PyInstaller)
- One-time-install / offline-first product docs (privacy, platforms, release rebuild)
- Pinned `requirements-release.txt` and `--smoke-convert` packaging hook

### Product
- No in-app updater, telemetry, accounts, or cloud conversion
- Core conversions usable fully offline after install
- Windows-first hardening: high-DPI, AppUserModelID, icon, custom LO/FFmpeg paths, theme preference, path edge-case tests
