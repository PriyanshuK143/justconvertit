from __future__ import annotations

from omniconvert.core.converter import ConversionOperation
from omniconvert.core.formats import FormatId
from omniconvert.ui.wheel_actions import MAX_WHEEL_ACTIONS, wheel_operations


def _op(oid: str, label: str, target: FormatId = FormatId.JPEG) -> ConversionOperation:
    return ConversionOperation(
        operation_id=oid,
        label=label,
        source_formats=frozenset({FormatId.PNG}),
        target_format=target,
        wheel_label=label,
    )


def test_wheel_keeps_small_lists_intact() -> None:
    ops = [_op("image.png_to_jpeg", "JPEG"), _op("image.crop", "Crop")]
    assert wheel_operations(ops) == ops


def test_wheel_prioritizes_common_formats() -> None:
    ops = [
        _op("image.crop", "Crop"),
        _op("image.png_to_webp", "WEBP", FormatId.WEBP),
        _op("image.png_to_jpeg", "JPEG"),
        _op("pdf.image_png_to_pdf", "PDF", FormatId.PDF),
        _op("text.txt_to_md", "MD", FormatId.MD),
    ]
    wheel = wheel_operations(ops, max_visible=MAX_WHEEL_ACTIONS)
    assert [o.segment_label for o in wheel[:3]] == ["JPEG", "WEBP", "MD"]
