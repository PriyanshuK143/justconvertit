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
    if oid.endswith("_to_md") or label == "md":
        return (3, label, oid)
    if oid.endswith("_to_txt") or label == "txt":
        return (4, label, oid)
    if "to_pdf" in oid or label == "pdf":
        return (5, label, oid)
    if oid.endswith("_to_docx") or label == "docx":
        return (6, label, oid)
    if "images" in oid or label == "images":
        return (7, label, oid)
    if "crop" in oid or label == "crop":
        return (8, label, oid)
    if oid.endswith("_to_mp3") or "extract" in oid:
        return (9, label, oid)
    if "compress" in oid or label == "compress":
        return (10, label, oid)
    if "pages" in oid or label == "pages zip":
        return (11, label, oid)
    return (20, label, oid)


def wheel_operations(
    operations: list[ConversionOperation],
    *,
    max_visible: int = MAX_WHEEL_ACTIONS,
) -> list[ConversionOperation]:
    """Return up to *max_visible* ops in a sensible order — all shown on the wheel."""
    ordered = sorted(operations, key=_rank)
    return ordered[:max_visible]
