# Feature Roadmap — Phase 3

**Date:** 2026-11-04

## Already exists (do not duplicate)

| Feature | Evidence |
|---------|----------|
| Image format convert / crop / No BG | `image_pillow.py` |
| Image resize (max edge) | **Added this phase** `image.resize` |
| PDF extract/render/rotate/compress/pages ZIP | `pdf_ops.py` |
| PDF merge helper (code) | `merge_pdfs()` — needs multi-file UI |
| Tabular CSV/JSON/XLSX | `tabular.py` |
| Media GIF/video/audio (FFmpeg) | `media_ffmpeg.py` |
| SVG (Inkscape) | `svg_inkscape.py` |
| Visual crop dialog | `crop_dialog.py` |
| History / settings / Save As | settings + dialogs |

## Prioritised next features

| Priority | Feature | Complexity | Offline | Notes |
|----------|---------|------------|---------|-------|
| P0 done | Image resize | Low | Yes | Shipped with tests |
| P1 | Multi-file / batch queue | High | Yes | Needs UI + JobManager queue |
| P1 | PDF merge in UI | Medium | Yes | Wire `merge_pdfs` + multi select |
| P2 | PDF page-range extract | Medium | Yes | Settings on single PDF |
| P2 | Image compress preset | Low | Yes | Quality-only JPEG/WEBP |
| P3 | Video trim / compress presets | High | Yes | FFmpeg filter UX |
| P3 | Folder watch / batch folder | High | Yes | Scope carefully |

## Implemented this phase

- `image.resize` with `max_edge` (16–10000), aspect-preserving LANCZOS → PNG.
- Tests: `tests/unit/test_image_resize.py`.

## Acceptance

- New feature tested: PASS  
- Existing tests: PASS (full suite)  
- No network deps: PASS  
