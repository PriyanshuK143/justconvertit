# Phase 3 Report — New features and capabilities

**Status:** COMPLETE (value slice)  
**Date:** 2026-11-04  

## Objective
Ship high-value offline features without cloud APIs or architecture rewrites.

## Features implemented
| Feature | Notes |
|---------|--------|
| `image.resize` | Earlier roadmap slice |
| `image.crop` + visual crop dialog | Earlier WIP |
| JobManager FIFO batch queue | `start_batch()` sequential jobs |
| Multi-file open / drop | Same-type batch → one output folder |
| `pdf.extract_pages` | Contiguous page range → PDF |
| `pdf.merge` + Merge PDFs… menu | Multi-select merge via settings `merge_paths` |
| Options popup `choice` widgets | e.g. PDF rotate angle |

## Files changed (this continuation)
- `src/omniconvert/services/jobs.py`
- `src/omniconvert/converters/pdf_ops.py`
- `src/omniconvert/ui/main_window.py`
- `src/omniconvert/ui/radial_wheel.py`
- `tests/unit/test_job_batch.py`
- `tests/integration/test_data_pdf.py`

## Tests
- `tests/unit/test_job_batch.py` — sequential PNG→JPEG batch
- `test_pdf_extract_pages`, `test_pdf_merge_operation`
- Full `bash scripts/test.sh` PASS

## Remaining backlog (non-blocking)
- Per-file retry UI, video trim/crop, richer office transforms — see `FEATURE_ROADMAP.md`

## Final status
**COMPLETE** for prioritized slice; backlog documented
