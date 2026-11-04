# Visual image crop dialog

**Status:** Approved  
**Scope:** Image crop only (`image.crop`). Video crop keeps percent spinboxes.

## Behavior

- Choosing **Crop** on an image opens a modal dialog with the photo preview.
- User draws/moves/resizes a rectangular selection (dashed border, dimmed outside).
- **Crop** converts the selection to existing `left_pct` / `right_pct` / `top_pct` / `bottom_pct` settings and continues the normal save + convert flow.
- **Cancel** aborts without converting.
- Selection is clamped so each margin stays within `MAX_CROP_PERCENT` (40%), matching the converter.

## Non-goals

- Video visual crop
- Free-form / aspect-ratio locks (can add later)
