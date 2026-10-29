from __future__ import annotations

from omniconvert.core.formats import FormatId
from omniconvert.core.registry import ConversionRegistry


def test_image_ops_registered(registry: ConversionRegistry) -> None:
    ops = registry.available_operations_for(FormatId.PNG)
    targets = {op.target_format for op in ops}
    assert FormatId.JPEG in targets
    assert FormatId.WEBP in targets
    assert FormatId.PDF in targets


def test_no_ops_for_unknown(registry: ConversionRegistry) -> None:
    assert registry.available_operations_for(FormatId.UNKNOWN) == []


def test_csv_ops(registry: ConversionRegistry) -> None:
    ops = registry.available_operations_for(FormatId.CSV)
    ids = {op.operation_id for op in ops}
    assert "data.csv_to_json" in ids
