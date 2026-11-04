# Phase 6 Report — Packaging and release engineering

**Status:** COMPLETE (Linux artifacts); Windows/macOS NV  
**Date:** 2026-11-04  

## Objective
Produce installable JustConvertIt packages and verify builds on available platforms.

## Linux build (this session)
```bash
bash scripts/build_linux.sh
```

### Artifacts
| Artifact | Path |
|----------|------|
| Standalone app | `dist/justconvertit/justconvertit` |
| Debian package | `dist/justconvertit_0.1.0_amd64.deb` (~90 MB) |
| Checksum | `dist/justconvertit_0.1.0_amd64.sha256` |

**SHA256:** `bd36cc30ec7e0e626e8f13ffc27bafd10aa6762cbbf9ed79336323682d4f7390  justconvertit_0.1.0_amd64.deb`

### Script updates
- `scripts/build_linux.sh` — added `--hidden-import omniconvert.converters.svg_inkscape`

### Smoke notes
- Binary is ELF x86-64 stripped; launches as GUI (offscreen timeout not a full functional GUI proof).
- Clean-machine `apt install` + uninstall not run in this session (needs sudo / spare machine).

## Stale tree note
- `dist/OmniConvert/` remains from older branding — **not** deleted (preserve policy). Do not ship it. Prefer `dist/justconvertit*`.

## Windows / macOS
- Inno / bundle scripts exist; not rebuilt in this Linux-only environment.

## Final status
**COMPLETE** for Linux package generation; install/uninstall on clean host and Windows builds remain **NEEDS VERIFICATION**
