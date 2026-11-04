# Crop / PDF / SVG / HTML conversions

**Status:** Approved (Inkscape for SVG; portable for HTML/PDF/image crop; FFmpeg for video crop)

## Scope

| Op | Engine | Settings / checks |
|----|--------|-------------------|
| HTML → TXT | portable | `MAX_TEXT_BYTES`; strip script/style |
| PDF rotate | pypdf | 90 / 180 / 270; reject encrypted |
| PDF compress | pypdf | rewrite/compress; reject encrypted |
| Image crop | Pillow | left/right/top/bottom % 0–40; leftover region ≥ 1px |
| Video crop | FFmpeg | same %; even width/height |
| SVG → PNG / PDF | Inkscape (optional) | missing → ops hidden + hint |

## Out of scope

cairosvg, AI upscale, PDF↔HTML layout.
