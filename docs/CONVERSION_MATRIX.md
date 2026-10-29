# Supported conversion matrix

Only operations that are **implemented, tested, and available** appear on the radial wheel.
All listed **portable core** conversions run fully offline after a one-time install.

## Portable core (pip / PyInstaller — Windows & Linux)

These use free libraries that ship with the app. No LibreOffice or FFmpeg required.

### Images (Pillow)

| From ↓ / To → | PNG | JPEG | WEBP | BMP | TIFF | PDF | No BG (PNG) |
|---------------|-----|------|------|-----|------|-----|-------------|
| PNG | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| JPEG | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| WEBP | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| BMP | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| TIFF | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |

**No BG:** removes a flat backdrop (corner-sampled) into a transparent PNG. Offline; works best on solid backgrounds, not complex photo cutouts.

### Text & tables

| From | To |
|------|-----|
| TXT | PDF, DOCX |
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
| Image | PDF | Single-page PDF |

### Office — pure Python (always available)

| From | To | Notes |
|------|-----|-------|
| DOCX | TXT | Paragraphs + tables |
| DOCX | PDF (text) | Text layout via ReportLab |
| TXT | DOCX | Simple Word wrap |
| PPTX | TXT | Slide text |
| PPTX | PDF (text) | Text layout via ReportLab |

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
