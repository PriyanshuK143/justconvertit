"""Shared crop margin parsing (percent of width/height)."""

from __future__ import annotations

from typing import Any

from omniconvert.core.converter import SettingSpec
from omniconvert.core.errors import ValidationError
from omniconvert.core.limits import MAX_CROP_PERCENT

CropPercents = tuple[int, int, int, int]  # left, right, top, bottom


def crop_setting_specs() -> tuple[SettingSpec, ...]:
    return (
        SettingSpec(
            key="left_pct",
            label="Left %",
            kind="int",
            default=0,
            minimum=0,
            maximum=MAX_CROP_PERCENT,
            help_text=f"Crop from the left edge (0–{MAX_CROP_PERCENT}%).",
        ),
        SettingSpec(
            key="right_pct",
            label="Right %",
            kind="int",
            default=0,
            minimum=0,
            maximum=MAX_CROP_PERCENT,
            help_text=f"Crop from the right edge (0–{MAX_CROP_PERCENT}%).",
        ),
        SettingSpec(
            key="top_pct",
            label="Top %",
            kind="int",
            default=0,
            minimum=0,
            maximum=MAX_CROP_PERCENT,
            help_text=f"Crop from the top edge (0–{MAX_CROP_PERCENT}%).",
        ),
        SettingSpec(
            key="bottom_pct",
            label="Bottom %",
            kind="int",
            default=0,
            minimum=0,
            maximum=MAX_CROP_PERCENT,
            help_text=f"Crop from the bottom edge (0–{MAX_CROP_PERCENT}%).",
        ),
    )


def parse_crop_percents(settings: dict[str, Any]) -> CropPercents:
    def one(key: str) -> int:
        raw = settings.get(key, 0)
        try:
            value = int(str(raw))
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{key} must be a whole number.") from exc
        if value < 0 or value > MAX_CROP_PERCENT:
            raise ValidationError(
                f"Crop {key} must be between 0 and {MAX_CROP_PERCENT}."
            )
        return value

    left = one("left_pct")
    right = one("right_pct")
    top = one("top_pct")
    bottom = one("bottom_pct")
    if left + right >= 100:
        raise ValidationError("Left + right crop must leave some width.")
    if top + bottom >= 100:
        raise ValidationError("Top + bottom crop must leave some height.")
    if left == right == top == bottom == 0:
        raise ValidationError("Set at least one crop margin above 0%.")
    return left, right, top, bottom


def crop_box_pixels(
    width: int,
    height: int,
    percents: CropPercents,
) -> tuple[int, int, int, int]:
    """Return Pillow-style box (left, upper, right, lower)."""
    left_p, right_p, top_p, bottom_p = percents
    left = int(width * left_p / 100)
    right = width - int(width * right_p / 100)
    top = int(height * top_p / 100)
    bottom = height - int(height * bottom_p / 100)
    if right - left < 1 or bottom - top < 1:
        raise ValidationError("Crop region is empty — reduce the margins.")
    return left, top, right, bottom


def percents_from_pixel_box(
    width: int,
    height: int,
    box: tuple[int, int, int, int],
) -> CropPercents:
    """Convert a Pillow-style pixel box to clamped margin percents."""
    if width < 1 or height < 1:
        raise ValidationError("Image size is invalid.")
    left, top, right, bottom = box
    if right <= left or bottom <= top:
        raise ValidationError("Crop region is empty — enlarge the selection.")

    def margin_pct(pixels: float, total: int) -> int:
        pct = int(round(pixels * 100.0 / total))
        return max(0, min(MAX_CROP_PERCENT, pct))

    left_pct = margin_pct(left, width)
    right_pct = margin_pct(width - right, width)
    top_pct = margin_pct(top, height)
    bottom_pct = margin_pct(height - bottom, height)
    if left_pct == right_pct == top_pct == bottom_pct == 0:
        raise ValidationError("Drag the rectangle to choose what to keep.")
    if left_pct + right_pct >= 100 or top_pct + bottom_pct >= 100:
        raise ValidationError("Crop region is empty — enlarge the selection.")
    return left_pct, right_pct, top_pct, bottom_pct


def min_crop_size(width: int, height: int) -> tuple[int, int]:
    """Minimum selection size that still fits MAX_CROP_PERCENT per side."""
    min_w = max(1, int((100 - 2 * MAX_CROP_PERCENT) / 100.0 * width))
    min_h = max(1, int((100 - 2 * MAX_CROP_PERCENT) / 100.0 * height))
    # Keep at least 1px if the image is tiny.
    return min(min_w, width), min(min_h, height)
