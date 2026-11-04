# Platform Compatibility — Phase 5

**Date:** 2026-11-04

## Linux (this host) — verified in development

| Check | Result |
|-------|--------|
| Run from venv `python -m omniconvert` | Supported (dev) |
| Paths via `platform/paths.py` (XDG) | Implemented |
| FFmpeg detection | PASS (`/usr/bin/ffmpeg`) |
| LibreOffice Snap | Detected; high-fidelity convert may fail |
| Inkscape | Missing on host |
| Wayland move/resize mitigations | Present in `main_window.py` WIP |
| Unit/UI/integration tests | 128+ passed |
| Fresh `.deb` install on clean Ubuntu | **NEEDS VERIFICATION** (not run this phase) |

## Windows

| Check | Result |
|-------|--------|
| Path/APPDATA helpers | Implemented in `paths.py` |
| PyInstaller spec / Inno script | Present |
| CI Windows PyInstaller + smoke | Workflow exists |
| Clean-machine Setup.exe without Python | **NEEDS VERIFICATION** (no Windows host here) |

## macOS

| Check | Result |
|-------|--------|
| Claimed as supported | **No — not claimed** |
| Bundle / signing | Not implemented |
| Testing | **BLOCKED** (no macOS environment) |

## Shared code path assumptions

- Prefer `pathlib` + `platform/paths.py` / `reveal.py` / `subprocess_util.py`.
- No hardcoded machine-specific paths found in core converters.

## Acceptance

| Criterion | Status |
|-----------|--------|
| Separate evidence per **claimed** OS | Linux PASS (dev); Windows NEEDS VERIFICATION; macOS not claimed |
| Shared path helpers | PASS |
| Installers on clean machines | NEEDS VERIFICATION |
| Optional engine failures graceful | PASS (ops hidden / soft errors) |
