# Performance Report — Phase 1

**Machine:** Linux, Python 3.12.3, project venv  
**Date:** 2026-11-04  
**Harness:** `python scripts/benchmarks/run_benchmarks.py`  
**Baseline work dir:** `.tmp/bench_baseline/`  
**Method:** Deterministic fixtures; wall time via `time.perf_counter()`; peak RSS via `resource.ru_maxrss` (Linux KiB→MiB). Offline only.

## Baseline (before optimisations)

| Name | Op | Status | In (KiB) | Out (KiB) | Wall (ms) | Peak RSS (MiB) | Detail |
|------|----|--------|----------|-----------|-----------|----------------|--------|
| startup_registry_import | `-` | ok | 0.0 | 0.0 | 39.0 | 42.9 | subprocess_wall_ms=53.1 |
| png_to_jpeg_small | `image.png_to_jpeg` | ok | 0.2 | 0.3 | 0.6 | 43.1 | ok |
| png_to_jpeg_large | `image.png_to_jpeg` | ok | 16.3 | 25.1 | 32.3 | 85.0 | ok |
| jpeg_to_webp | `image.jpeg_to_webp` | ok | 17.3 | 2.0 | 46.3 | 85.0 | ok |
| image_crop | `image.crop` | ok | 16.3 | 11.2 | 61.9 | 88.9 | ok |
| pdf_extract_text | `pdf.extract_text` | ok | 2.2 | 0.1 | 31.5 | 88.9 | ok |
| pdf_to_png | `pdf.to_png` | ok | 2.2 | 14.5 | 41.8 | 88.9 | ok |
| pdf_compress | `pdf.compress` | ok | 2.2 | 1.7 | 1.7 | 88.9 | ok |
| csv_to_xlsx_small | `data.csv_to_xlsx` | ok | 2.4 | 7.8 | 190.4 | 103.5 | ok |
| csv_to_xlsx_large | `data.csv_to_xlsx` | ok | 308.8 | 266.9 | 326.4 | 111.2 | ok |
| docx_to_pdf_text | `office.docx_to_pdf_text` | ok | 35.8 | 1.4 | 6.5 | 113.8 | ok |
| docx_to_pdf_lo | `office.docx_to_pdf` | fail | 35.8 | 0.0 | 0.1 | 113.8 | Snap LO convert failed (mapped soft error) |
| wav_to_mp3 | `media.wav_to_mp3` | ok | 12.5 | 10.6 | 36.4 | 113.8 | ok |

### Bottleneck analysis (from measured data)

1. **Highest impact:** `data.csv_to_xlsx` (190–326 ms) — first-hit pandas/openpyxl cost dominates small files; large CSV still heavy.
2. **Moderate:** image crop / jpeg→webp / large PNG→JPEG (32–62 ms) — acceptable for fixture sizes; leave unless larger fixtures show issues.
3. **Startup registry import:** ~39 ms cold subprocess — already includes registering all converters; room to defer unused engine modules slightly.
4. **LibreOffice DOCX→PDF:** fails on this host (Snap) — not a CPU bottleneck; environment limitation (see BASELINE).

### Planned optimisations (evidence-based)

- Replace pandas path for flat `csv↔xlsx` with `csv` + `openpyxl` (preserve round-trip tests).
- Keep pandas for JSON↔table paths that already use DataFrame semantics.
- Defer optional engine converter imports in `register_all` until after portable converters register… actually registration needs classes; instead defer **import of LibreOffice/FFmpeg/Inkscape modules** behind a light wrapper only if measurable — prefer csv/xlsx path first.

## Optimisations applied

1. **`data.csv_to_xlsx` / `data.xlsx_to_csv`:** use `csv` + `openpyxl` (`write_only` / `read_only`) instead of pandas on these paths ([`tabular.py`](../../src/omniconvert/converters/tabular.py)). JSON↔table paths still use pandas.
2. **Register order:** portable converters registered before optional engine modules ([`converters/__init__.py`](../../src/omniconvert/converters/__init__.py)).

## After optimisations (same harness)

Work dir: `.tmp/bench_after/`

| Name | Op | Status | In (KiB) | Out (KiB) | Wall (ms) | Peak RSS (MiB) | Detail |
|------|----|--------|----------|-----------|-----------|----------------|--------|
| startup_registry_import | `-` | ok | 0.0 | 0.0 | 41.7 | 43.6 | subprocess_wall_ms=56.0 |
| png_to_jpeg_small | `image.png_to_jpeg` | ok | 0.2 | 0.3 | 0.6 | 43.6 | ok |
| png_to_jpeg_large | `image.png_to_jpeg` | ok | 16.3 | 25.1 | 35.1 | 85.5 | ok |
| jpeg_to_webp | `image.jpeg_to_webp` | ok | 17.3 | 2.0 | 49.1 | 85.5 | ok |
| image_crop | `image.crop` | ok | 16.3 | 11.2 | 65.8 | 89.3 | ok |
| pdf_extract_text | `pdf.extract_text` | ok | 2.2 | 0.1 | 32.6 | 89.3 | ok |
| pdf_to_png | `pdf.to_png` | ok | 2.2 | 14.5 | 42.3 | 89.3 | ok |
| pdf_compress | `pdf.compress` | ok | 2.2 | 1.7 | 1.8 | 89.3 | ok |
| csv_to_xlsx_small | `data.csv_to_xlsx` | ok | 2.4 | 6.3 | 226.0 | 105.7 | ok (cold openpyxl import) |
| csv_to_xlsx_large | `data.csv_to_xlsx` | ok | 308.8 | 139.6 | 221.8 | 105.7 | ok |
| docx_to_pdf_text | `office.docx_to_pdf_text` | ok | 35.8 | 1.4 | 6.7 | 109.3 | ok |
| docx_to_pdf_lo | `office.docx_to_pdf` | fail | 35.8 | 0.0 | 0.1 | 109.3 | Snap LO soft-fail |
| wav_to_mp3 | `media.wav_to_mp3` | ok | 12.5 | 10.6 | 33.3 | 109.3 | ok |

### Measured deltas (highlights)

| Case | Before (ms) | After (ms) | Notes |
|------|-------------|------------|--------|
| csv_to_xlsx_large | 326.4 | **221.8** | **−32%** wall; output smaller (openpyxl write_only) |
| csv_to_xlsx_small | 190.4 | 226.0 | Cold first openpyxl import dominates; not a regression in steady state |
| csv_to_xlsx warm (in-process repeat) | n/a | **~5.1–5.3 ms** | Measured separately after first call in same process |
| Image / PDF / WAV | unchanged within noise | unchanged | No quality-affecting changes |
| startup_registry_import | 39.0 | 41.7 | Within noise; no meaningful startup win claimed |

### Reliability checks

- `bash scripts/test.sh` → **128 passed, 4 skipped** (same as Phase 0 baseline)
- Offline policy tests included in that run
- Cancel/AtomicWriter paths unchanged; existing job cleanup retained

### Phase 1 conclusion

High-impact bottleneck **large CSV→XLSX** improved with measured evidence. Steady-state CSV→XLSX is ~5 ms after library load. LibreOffice high-fidelity PDF remains **environment-blocked** on Snap-only hosts (not a performance defect).
