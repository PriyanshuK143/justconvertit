# Conversion Quality & Stability — Phase 2

**Date:** 2026-11-04  
**Status:** COMPLETE (audit + regression evidence; LO Snap path NEEDS VERIFICATION)

## Scope

Inspected converter families against existing tests and code behaviour. No invented quality claims.

## Category notes

### Image (`image_pillow.py`)
- Format matrix covered by integration tests (`test_image_conversion.py`).
- EXIF orientation applied on crop/resize via `ImageOps.exif_transpose`.
- Transparency flattened for JPEG with configurable background.
- **No BG:** corner-color heuristic — document to users; not ML cutout.
- **Crop:** visual UI + % settings; max 40% per side.
- **Resize (new):** LANCZOS, aspect preserved, max_edge clamp.
- Corrupt/unidentified images → `ValidationError` / soft job failure.

### PDF (`pdf_ops.py`)
- Text extract, render, compress, rotate, pages→ZIP covered by unit/integration tests.
- Password-protected / corrupt: pdfium open raises user-facing ValidationError.
- `merge_pdfs` helper exists for batch UI; not a wheel single-file op yet.

### Office
- Pure-Python paths: text-focused; layout not pixel-perfect (documented).
- LibreOffice: preferred when available; Snap-only hosts may fail convert (soft error) — quality tests skipped on this machine.

### Tables (`tabular.py`)
- CSV↔XLSX now openpyxl fast path; JSON paths still pandas.
- Round-trip tests pass (`test_data_pdf.py`).

### Media / SVG
- FFmpeg ops tested when present; Inkscape missing here → SVG skipped.

## Test evidence

```bash
bash scripts/test.sh
# 128+ passed (resize adds tests); skips: LO quality×2, Inkscape, optional-deps FFmpeg-present
```

## Residual quality limits

| Area | Limitation |
|------|------------|
| No BG | Flat backdrops only |
| Office without LO | Text PDF / limited layout |
| LO on Snap | May fail high-fidelity export |
| PDF compress | Best-effort rewrite |
| Video | Codec/host FFmpeg dependent |
