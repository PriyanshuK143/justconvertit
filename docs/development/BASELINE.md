# JustConvertIt — Phase 0 Baseline

**Status:** COMPLETE (inspection + documentation only; no feature work)  
**Baseline date:** 2026-11-04  
**Machine:** Linux (Ubuntu-class), Python 3.12.3 venv  
**Repository:** `/home/swanand/Desktop/backup/Priyanshu/Justconvertit`  
**HEAD commit:** `f4043beea888c4a7156dd6851a91b871eb8c41de` (`made installable app`)  
**Branch:** `main` (tracks `origin/main`)

> This document records a **verified** snapshot of the working tree as of Phase 0.  
> It does **not** discard or reset any uncommitted work.

---

## 1. Product identity

| Item | Value |
|------|--------|
| Public name | justconvertit / JustConvertIt |
| Python package / import path | `omniconvert` |
| Version | `0.1.0` (`pyproject.toml`, `src/omniconvert/version.py`) |
| License | MIT |
| Entry points | `justconvertit` / `omniconvert` → `omniconvert.main:main` |
| Remote | `https://github.com/PriyanshuK143/justconvertit.git` (not used during Phase 0) |

### Product guarantees (code-verified)

From `src/omniconvert/product.py`:

| Flag | Value |
|------|--------|
| `OFFLINE_FIRST` | `True` |
| `REQUIRES_ACCOUNT` | `False` |
| `REQUIRES_INTERNET` | `False` |
| `IN_APP_UPDATE_CHECKER` | `False` |
| `AUTOMATIC_UPDATES` | `False` |
| `TELEMETRY_ENABLED` | `False` |
| `REMOTE_ANALYTICS` | `False` |
| `CLOUD_CONVERSION` | `False` |
| `OPTIONAL_ENGINES_LOCAL_ONLY` | `True` |
| `FORBIDDEN_NETWORK_MODULES` | urllib/http/requests/httpx/aiohttp/websocket/… |

Enforced by `tests/unit/test_offline_policy.py`.

---

## 2. Architecture (verified)

```
UI (PySide6)
  MainWindow / RadialWheel / dialogs / crop_dialog / icons
    → JobManager (QThread)
         → ConversionRegistry
              → Converter handlers
```

Key modules:

| Area | Path |
|------|------|
| Entry | `src/omniconvert/main.py`, `__main__.py` |
| Core | `core/detection.py`, `registry.py`, `limits.py`, `output.py`, `safe_zip.py`, `crop.py`, `errors.py`, `formats.py`, `job.py`, `converter.py` |
| Converters | `converters/*.py` + `register_all()` |
| Services | `jobs.py`, `settings.py`, `dependencies.py`, `engine_setup.py`, `logging_setup.py`, `resilience.py` |
| Platform | `paths.py`, `reveal.py`, `subprocess_util.py` |
| UI | `main_window.py`, `radial_wheel.py`, `dialogs.py`, `save_dialog.py`, `crop_dialog.py`, `icons.py`, `theme.py` |

---

## 3. Dependency versions (installed venv)

| Package | Installed |
|---------|-----------|
| Python | 3.12.3 |
| PySide6 | 6.12.0 |
| Pillow | 13.0.0 |
| pypdf | 6.21.4 |
| reportlab | 4.5.1 |
| pandas | 2.3.3 |
| openpyxl | 3.1.5 |
| pypdfium2 | 5.14.0 |
| python-docx | 1.2.0 |
| python-pptx | 1.0.2 |

Pins in `requirements-release.txt` match the above for the primary stack.

---

## 4. Optional engines on this machine

| Engine | Detected | Path / notes |
|--------|----------|--------------|
| LibreOffice | Yes (Snap) | `/snap/bin/libreoffice` — quality integration tests **skip** apt/deb-only path |
| FFmpeg | Yes | `/usr/bin/ffmpeg` |
| Inkscape | **No** | SVG ops registered but unavailable; related tests skip |

---

## 5. Registered conversion operations (65)

All `tested=True` in registry. Counted via `build_default_registry().all_operations()`.

### data (6) — portable

- `data.csv_to_json`, `data.csv_to_xlsx`
- `data.json_to_csv`, `data.json_to_xlsx`
- `data.xlsx_to_csv`, `data.xlsx_to_json`

### image (22) — portable

- Cross format: png/jpeg/webp/bmp/tiff pairwise (except same→same)
- `image.crop` → PNG (settings: margin %; UI: visual crop dialog when wired)
- `image.remove_background` → PNG (corner-color / tolerance — **not AI**)

### pdf (11) — portable

- `pdf.extract_text`, `pdf.to_png`, `pdf.to_jpeg`, `pdf.pages_to_zip`
- `pdf.rotate`, `pdf.compress`
- `pdf.image_{png,jpeg,webp,bmp,tiff}_to_pdf`

### text (6) — portable

- `text.json_format`, `text.txt_to_pdf`, `text.json_to_pdf`
- `text.md_to_txt`, `text.txt_to_md`, `text.html_to_txt`

### office (10)

- Portable: `office.docx_to_txt`, `office.txt_to_docx`, `office.docx_to_pdf_text`, `office.pptx_to_txt`, `office.pptx_to_pdf_text`
- LibreOffice: `office.docx_to_pdf`, `office.pptx_to_pdf`, `office.xlsx_to_pdf`, `office.txt_to_pdf_lo`, `office.pdf_to_docx`

Registry suppresses portable PDF-text fallbacks when preferred LO ops are available (`_PREFERRED_OVER_FALLBACK` in `registry.py`).

### media (8) — requires FFmpeg

- `media.wav_to_mp3`, `media.mp3_to_wav`, `media.extract_audio_mp3`
- `media.gif_to_mp4`, `media.video_to_gif`
- `media.video_to_frames_zip`, `media.frames_zip_to_mp4`
- `media.video_crop`

### svg (2) — requires Inkscape

- `svg.to_png`, `svg.to_pdf`

**On this host:** ~63 ops available through converters that report `is_available()` (SVG converter unavailable without Inkscape).

---

## 6. Security / safety limits (code)

From `core/limits.py` and related:

| Limit | Value |
|-------|--------|
| Max input | 500 MiB |
| Max image pixels | 80 MP |
| Max text | 50 MiB |
| Max PDF pages | 500 |
| Max PDF render pages | 100 |
| Max PDF render scale | 2.0 |
| ZIP members / uncompressed / ratio | 5000 / 512 MiB / 100× |
| Max video frames | 300 |
| Max GIF seconds | 10 |
| Max crop % per side | 40 |
| Subprocess timeout | 600 s |

Also: `AtomicWriter`, refuse overwrite source, unique suffix names, safe ZIP open, argv-only subprocesses (`subprocess_util.py`), soft UI/job exception containment (`resilience.py`, `jobs.py`, `registry.py`).

---

## 7. Git / working-tree state (CRITICAL — do not discard)

### Committed history

1. `e73b6d4` — Initial commit: justconvertit local file converter  
2. `f4043be` — made installable app  

### Modified tracked files (22) — uncommitted WIP

Includes packaging docs + substantial product code:

- Converters: `image_pillow.py`, `media_ffmpeg.py`, `pdf_ops.py`, `text_ops.py`, `__init__.py`
- Core: `detection.py`, `formats.py`, `limits.py`, `registry.py`
- UI: `main_window.py`, `radial_wheel.py`
- Services/main: `main.py`, `jobs.py`
- Docs/scripts: README, INSTALL, PLATFORMS, RELEASE, CONVERSION_MATRIX, `build_linux.sh`, packaging README, `.gitignore`
- Tests: `tests/ui/test_radial_hub.py`

Approx diff vs HEAD: **+1521 / −325** lines across those files.

### Untracked files (19+) — uncommitted WIP

| Path | Role |
|------|------|
| `scripts/build_deb.sh` | Ubuntu `.deb` packager |
| `src/omniconvert/converters/svg_inkscape.py` | SVG converter |
| `src/omniconvert/core/crop.py` | Shared crop % helpers |
| `src/omniconvert/services/resilience.py` | Soft crash containment |
| `src/omniconvert/ui/crop_dialog.py` | Visual image crop UI |
| `src/omniconvert/ui/icons.py` | Format icons / hub marks |
| `docs/superpowers/**` | Design specs / plans |
| New tests under `tests/unit`, `tests/ui`, `tests/integration` | Crop, SVG, media, icons, resilience, md/txt, etc. |

**Policy:** Phase 0 and later phases must treat this WIP as valuable. Do **not** `git reset --hard`, clean, or overwrite without explicit owner approval.

---

## 8. Packaging / artifacts on disk

| Artifact | State |
|----------|--------|
| `scripts/build_linux.sh` | Present (modified) |
| `scripts/build_deb.sh` | Present (**untracked**) |
| `scripts/build_windows.ps1` | Present |
| `packaging/windows/installer.iss` | Present |
| `packaging/windows/omniconvert.spec` | Present |
| `dist/` | Contains stale **`OmniConvert/`** tree — **not** a fresh `justconvertit` binary |
| `dist/justconvertit/justconvertit` | **Missing** on this machine |
| CI (`.github/workflows/ci.yml`) | Tests + pip-audit + PyInstaller folder artifacts; **does not** build `.deb` or Inno Setup.exe |

---

## 9. Documentation vs code

| Doc | Note |
|-----|------|
| `docs/PROJECT_STATUS.md` | Dated **2026-10-29** — **stale** (claims `.deb` automation incomplete; script now exists untracked) |
| `docs/CONVERSION_MATRIX.md` | Modified in WIP; should be re-synced after freeze |
| `docs/INSTALL.md` / `RELEASE.md` / `PLATFORMS.md` | Modified; describe `.deb` / Setup.exe release path not yet verified as published artifacts |
| `docs/SECURITY.md` / `PRIVACY.md` / `PRODUCT.md` | Align with product flags; still accurate on privacy posture |

---

## 10. Baseline test results (Phase 0)

**Command:**

```bash
bash scripts/test.sh
```

**Result (2026-11-04):**

```
128 passed, 4 skipped, 1 warning in ~1.6s
```

### Skipped (environment)

1. `tests/integration/test_libreoffice_quality.py` (2) — LibreOffice apt/deb binary not available (Snap-only)
2. `tests/integration/test_svg_video_crop.py` — Inkscape missing
3. `tests/unit/test_optional_deps.py` — FFmpeg **is** installed (skip path for missing-engine assertion)

### Warning

- PytestConfigWarning: unknown config option `qt_api` in `pyproject.toml`

### Failures

- **None** in this run.

### Not verified in Phase 0

- Full GUI manual smoke on display
- Fresh PyInstaller / `.deb` / Windows Setup builds
- Clean-machine install without Python
- macOS anything
- Public GitHub Releases contents (intentionally out of Phase 0 scope; no remote release ops performed)

---

## 11. Known issues / risks (baseline)

| ID | Severity | Issue |
|----|----------|--------|
| B1 | High (release) | Uncommitted WIP not frozen; cannot tag a clean release from HEAD alone |
| B2 | High (release) | Stale `dist/OmniConvert` branding; no current `justconvertit` binary in `dist/` |
| B3 | High (release) | CI does not produce `.deb` or Setup.exe |
| B4 | Medium | `docs/PROJECT_STATUS.md` outdated vs code |
| B5 | Medium | Inkscape not installed here — SVG path untested on this host |
| B6 | Medium | LO quality tests skipped for Snap-only LO |
| B7 | Medium | Mixed branding (`omniconvert` package vs `justconvertit` product; icon filenames) |
| B8 | Low | Wayland window move/resize historically fragile (mitigations in WIP `main_window.py`) |
| B9 | Low | Remove-BG is heuristic, not AI; user expectations may mismatch |
| B10 | Info | No performance benchmark suite yet (Phase 1) |

---

## 12. Phase 0 acceptance checklist

| Criterion | Result |
|-----------|--------|
| Every registered conversion operation inventoried | **PASS** (65 listed) |
| Existing test results recorded | **PASS** (128 passed, 4 skipped) |
| Uncommitted work identified | **PASS** (22 modified + 19 untracked paths) |
| Existing architecture documented | **PASS** |
| Known issues documented | **PASS** |
| No existing work accidentally discarded | **PASS** (no reset/clean; docs only) |

**Phase 0 decision:** **COMPLETE**

---

## 13. Recommended next step

Proceed to **Phase 1 — Performance and Reliability** only after product-owner approval.

Before Phase 1 coding, optionally freeze WIP into a local commit (owner must explicitly request commit — Phase 0 did not create commits).
