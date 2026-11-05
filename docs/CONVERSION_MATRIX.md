# Supported conversion matrix

Only operations that are **implemented, tested, and available** appear on the radial wheel.
All listed **portable core** conversions run fully offline after a one-time install.

## Portable core (pip / PyInstaller — Windows & Linux)

These use free libraries that ship with the app. No LibreOffice or FFmpeg required.

### Images (Pillow)

| From ↓ / To → | PNG | JPEG | WEBP | PDF | Crop → PNG |
|---------------|-----|------|------|-----|------------|
| PNG | — | ✓ | ✓ | ✓ | ✓ |
| JPEG | ✓ | — | ✓ | ✓ | ✓ |
| WEBP | ✓ | ✓ | — | ✓ | ✓ |
| BMP | ✓ | ✓ | ✓ | ✓ | ✓ |
| TIFF | ✓ | ✓ | ✓ | ✓ | ✓ |

BMP/TIFF can be **opened** and converted to PNG/JPEG/WEBP; there is no export to BMP or TIFF, and no resize / remove-background actions.

### Text & tables

| From | To |
|------|-----|
| TXT | MD, PDF, DOCX |
| MD | TXT |
| HTML | TXT, MD, PDF, DOCX |
| JSON | CSV, XLSX, PDF, Pretty JSON |
| CSV | JSON, XLSX |
| XLSX | CSV, JSON |

**JSON → CSV/XLSX supported shapes:** array of flat objects, array of scalars,
columnar object of flat arrays, or a single flat object. Nested objects/arrays are
**rejected** (would lose structure).

### PDF (pypdf + pypdfium2 + ReportLab)

| From | To / action | Notes |
|------|-------------|-------|
| PDF | TXT | Embedded text extract (not OCR) |
| PDF | PNG | Render page 1 |
| PDF | JPEG | Render page 1 |
| PDF | Pages ZIP | Every page as PNG inside a ZIP (capped page/pixel budget) |
| PDF | Images ZIP | Embedded XObject images (not OCR; scans → use Pages ZIP) |
| PDF | PDF (Rotate) | 90 / 180 / 270° all pages |
| PDF | PDF (Compress) | Best-effort content-stream rewrite |
| Image | PDF | Single-page PDF |
| Image | Crop → PNG | Margins as % (max 40% per side) |

### Office — pure Python (always available)

| From | To | Notes |
|------|-----|-------|
| DOCX | TXT | Document order: headings, paragraphs, tables |
| DOCX | MD | Headings + Markdown tables (portable) |
| DOCX | PDF | Headings, tables, embedded images via ReportLab |
| DOCX | Images ZIP | Extract embedded pictures |
| TXT | DOCX | Simple Word wrap |
| PPTX | TXT | Slide text |
| PPTX | PDF (text) | Text layout via ReportLab |

PDF **Images ZIP** extracts embedded pictures (not full-page screenshots). For scans or drawn pages, use **Pages ZIP** / page PNG.

## Optional system engines (not bundled)

Shown on the wheel **only if installed** on the user’s machine. On Ubuntu:

```bash
sudo apt install -y libreoffice ffmpeg
```

When LibreOffice is available, these replace portable “PDF (text)” / ReportLab
TXT→PDF on the wheel so users get the best layout by default.

| From | To | Requires | Notes |
|------|-----|----------|-------|
| DOCX / PPTX / XLSX / TXT | PDF | LibreOffice | Best layout (Writer/Impress/Calc export) |
| PDF | DOCX | LibreOffice | Best-effort (not pixel-perfect); text PDFs best; scans stay as images |
| WAV | MP3 | FFmpeg | |
| MP3 | WAV | FFmpeg | |
| MP4 / MKV | MP3 | FFmpeg | Audio extract |
| GIF | MP4 | FFmpeg | H.264 encode |
| MP4 / MKV | GIF | FFmpeg | Short clip (max 10s); fps/duration checked |
| MP4 / MKV / GIF | Frames ZIP | FFmpeg | PNG sequence in ZIP (max 300 frames); fps checked |
| Frames ZIP | MP4 | FFmpeg | ZIP must contain only images |
| MP4 / MKV | Crop → MP4 | FFmpeg | Margins as % (max 40% per side) |
| SVG | PNG / PDF | Inkscape | Optional; `sudo apt install inkscape` |

## Redistribution notes (future public release)

| Component | Typical license | Bundle with installer? |
|-----------|-----------------|------------------------|
| Pillow, pypdf, ReportLab, pandas, openpyxl, python-docx, python-pptx | BSD / MIT / HPND | Yes |
| pypdfium2 / PDFium | Apache-2.0 / BSD | Yes (include notices) |
| PySide6 / Qt | LGPL | Yes if LGPL obligations met |
| LibreOffice | MPL/LGPL | **No** by default — detect system install |
| FFmpeg | LGPL/GPL (build-dependent) | **No** by default — detect system install |

## Not claimed yet

- OCR / scanned-PDF text
- Password-protected PDF unlock
- Pixel-perfect DOCX/PPTX layout without LibreOffice
- Video re-encode without FFmpeg
- AI image upscaling
- High-fidelity PDF ↔ HTML
