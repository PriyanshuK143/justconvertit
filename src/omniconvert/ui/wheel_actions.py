"""Order conversion actions for the radial wheel (no More… overflow)."""

from __future__ import annotations

from omniconvert.core.converter import ConversionOperation

# Physical limit of readable pads on the orb.
MAX_WHEEL_ACTIONS = 8


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
    if "compress" in oid or label == "compress":
        return (7, label, oid)
    if "remove_bg" in oid or label in {"no bg", "nobg"}:
        return (40, label, oid)
    if oid.endswith("_to_bmp") or label == "bmp":
        return (30, label, oid)
    if oid.endswith("_to_tiff") or label == "tiff":
        return (31, label, oid)
    return (20, label, oid)


def wheel_operations(
    operations: list[ConversionOperation],
    *,
    max_visible: int = MAX_WHEEL_ACTIONS,
) -> list[ConversionOperation]:
    """Return up to *max_visible* ops in a sensible order — all shown on the wheel."""
    ordered = sorted(operations, key=_rank)
    return ordered[:max_visible]
