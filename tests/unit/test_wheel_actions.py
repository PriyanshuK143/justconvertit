from __future__ import annotations

from omniconvert.core.converter import ConversionOperation
from omniconvert.core.formats import FormatId
from omniconvert.ui.wheel_actions import MAX_WHEEL_ACTIONS, wheel_operations


def _op(oid: str, label: str) -> ConversionOperation:
    return ConversionOperation(
        operation_id=oid,
        label=label,
        source_formats=frozenset({FormatId.PNG}),
        target_format=FormatId.JPEG,
        wheel_label=label,
    )


def test_wheel_keeps_small_lists_intact() -> None:
    ops = [_op("image.png_to_jpeg", "JPEG"), _op("image.crop", "Crop")]
    assert wheel_operations(ops) == ops


def test_wheel_prioritizes_and_caps_without_more() -> None:
    ops = [
        _op("image.png_to_bmp", "BMP"),
        _op("image.png_to_tiff", "TIFF"),
        _op("image.remove_bg", "No BG"),
        _op("image.png_to_jpeg", "JPEG"),
        _op("image.png_to_webp", "WEBP"),
        _op("image.crop", "Crop"),
        _op("image.resize", "Resize"),
        _op("pdf.image_png_to_pdf", "PDF"),
        _op("image.png_to_png", "PNG"),
    ]
    wheel = wheel_operations(ops, max_visible=MAX_WHEEL_ACTIONS)
    assert len(wheel) == MAX_WHEEL_ACTIONS
    assert all(o.operation_id != "ui.more_actions" for o in wheel)
    assert wheel[0].segment_label == "JPEG"
    assert {o.segment_label for o in wheel} >= {"JPEG", "WEBP", "Crop", "Resize", "PDF"}
