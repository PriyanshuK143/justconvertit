# Linux .deb packaging Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox syntax.

**Goal:** Ship Ubuntu installs as `justconvertit_<ver>_amd64.deb` so users install like a normal app.

**Architecture:** Wrap existing PyInstaller `dist/justconvertit/` into a Debian package under `/opt/justconvertit` with desktop entry, icon, and `/usr/bin` symlink via `scripts/build_deb.sh`.

**Tech Stack:** PyInstaller, `dpkg-deb`, `fakeroot`, bash.

## Global Constraints

- No zip + install.sh as end-user path
- No bundled LibreOffice/FFmpeg
- No in-app updater
- Package name `justconvertit`, arch `amd64`
- Version from `pyproject.toml`

---

### Task 1: `scripts/build_deb.sh`

- [x] Create staging tree under `build/deb/justconvertit/`
- [x] Copy PyInstaller tree → `opt/justconvertit/`
- [x] Install desktop + icon + `/usr/bin/justconvertit` symlink
- [x] Write `DEBIAN/control` (+ optional `postinst` for icon cache)
- [x] `fakeroot dpkg-deb --build` → `dist/justconvertit_<ver>_amd64.deb` + sha256
- [x] Verify with `dpkg-deb -I` / `dpkg-deb -c`

### Task 2: Wire build + docs

- [x] Update `build_linux.sh` or docs so release flow calls `build_deb.sh`
- [x] Update README, INSTALL, RELEASE, PLATFORMS, packaging/linux/README
- [x] Stop staging install.sh as the primary end-user story
