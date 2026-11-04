from __future__ import annotations

import pytest

from omniconvert.core.crop import (
    crop_box_pixels,
    min_crop_size,
    percents_from_pixel_box,
)
from omniconvert.core.errors import ValidationError


def test_percents_from_pixel_box_roundtrip() -> None:
    box = crop_box_pixels(200, 100, (10, 10, 10, 10))
    left, right, top, bottom = percents_from_pixel_box(200, 100, box)
    assert (left, right, top, bottom) == (10, 10, 10, 10)


def test_percents_from_pixel_box_rejects_full_frame() -> None:
    with pytest.raises(ValidationError):
        percents_from_pixel_box(100, 80, (0, 0, 100, 80))


def test_min_crop_size_respects_max_margin() -> None:
    w, h = min_crop_size(100, 100)
    assert w == 20
    assert h == 20
