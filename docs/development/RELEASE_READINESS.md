# Release Readiness — Phase 6

**Date:** 2026-11-04  
**Status:** Linux artifacts **generated**; clean-machine install + Windows still NV

## Packaging inventory

| Artifact/script | Path | Notes |
|-----------------|------|-------|
| Linux PyInstaller | `scripts/build_linux.sh`, `justconvertit.spec` | Includes `svg_inkscape` hidden import |
| Linux `.deb` | `scripts/build_deb.sh` | Invoked by `build_linux.sh` |
| Windows PyInstaller | `packaging/windows/omniconvert.spec`, `scripts/build_windows.ps1` | Not rebuilt here |
| Windows Inno | `packaging/windows/installer.iss` | Version 0.1.0 |
| CI | `.github/workflows/ci.yml` | Folder artifacts; no `.deb` / Setup.exe |

## Fresh Linux artifacts (2026-11-04)

| Artifact | Path |
|----------|------|
| App binary | `dist/justconvertit/justconvertit` |
| Debian package | `dist/justconvertit_0.1.0_amd64.deb` |
| Checksum file | `dist/justconvertit_0.1.0_amd64.sha256` |

**SHA256:** `bd36cc30ec7e0e626e8f13ffc27bafd10aa6762cbbf9ed79336323682d4f7390  justconvertit_0.1.0_amd64.deb`

Install hint: `sudo apt install ./dist/justconvertit_0.1.0_amd64.deb`

## Stale leftovers

- `dist/OmniConvert/` still present — **do not ship**. Left in place under WIP-preserve policy.

## Branding gaps (non-blocking for Linux .deb)

- Internal package import `omniconvert` vs product `justconvertit`
- Resource icon filenames may still say `omniconvert.*`
- Windows packaging filenames still `omniconvert.*`

## Acceptance

| Criterion | Status |
|-----------|--------|
| Fresh Linux installers generated | **PASS** |
| Install without Python (clean machine) | NEEDS VERIFICATION |
| Uninstall works | NEEDS VERIFICATION |
| Branding consistent for publish | PARTIAL (OmniConvert leftover in dist/) |
| Checksums | **PASS** (sha256 file written) |
| Windows Setup.exe | NEEDS VERIFICATION |
| No stale OmniConvert published | PASS as policy |

**Phase 6 decision:** Linux package generation **COMPLETE**; clean install smoke + Windows remain **NEEDS VERIFICATION**.
