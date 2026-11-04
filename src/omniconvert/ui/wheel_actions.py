"""Pick a clean, small set of wheel actions — rest go under More…"""

from __future__ import annotations

from omniconvert.core.converter import ConversionOperation
from omniconvert.core.formats import FormatId

# Keep the orb readable on Windows HiDPI / small screens.
MAX_WHEEL_ACTIONS = 6

_MORE_OP = ConversionOperation(
    operation_id="ui.more_actions",
    label="More actions…",
    source_formats=frozenset(),
    target_format=FormatId.TXT,
    description="Open the full list of conversions for this file.",
    wheel_label="More",
    supports_batch=False,
    tested=True,
)


def more_operation() -> ConversionOperation:
    return _MORE_OP


def _rank(op: ConversionOperation) -> tuple[int, str, str]:
    """Lower rank = shown first on the wheel."""
    oid = op.operation_id
    label = (op.segment_label or "").lower()

    if oid.endswith("_to_jpeg") or label == "jpeg":
        return (0, label, oid)
    if oid.endswith("_to_png") or label == "png":
        return (1, label, oid)
    if oid.endswith("_to_webp") or label == "webp":
        return (2, label, oid)
    if "to_pdf" in oid or label == "pdf":
        return (3, label, oid)
    if "crop" in oid or label == "crop":
        return (4, label, oid)
    if "resize" in oid or label == "resize":
        return (5, label, oid)
    if oid.endswith("_to_mp3") or "extract" in oid:
        return (6, label, oid)
    if "remove_bg" in oid or label in {"no bg", "nobg"}:
        return (40, label, oid)
    if oid.endswith("_to_bmp") or label == "bmp":
        return (30, label, oid)
    if oid.endswith("_to_tiff") or label == "tiff":
        return (31, label, oid)
    return (20, label, oid)


def split_wheel_actions(
    operations: list[ConversionOperation],
    *,
    max_visible: int = MAX_WHEEL_ACTIONS,
) -> tuple[list[ConversionOperation], list[ConversionOperation]]:
    """Return (wheel_ops, overflow_ops).

    If there is overflow, the last wheel slot is reserved for More….
    """
    ordered = sorted(operations, key=_rank)
    if len(ordered) <= max_visible:
        return ordered, []
    primary = ordered[: max_visible - 1]
    overflow = ordered[max_visible - 1 :]
    return [*primary, more_operation()], overflow
