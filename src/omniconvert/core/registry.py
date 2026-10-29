"""Conversion operation registry and router."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omniconvert.core.converter import (
    CancelCheck,
    ConversionOperation,
    Converter,
    ProgressCallback,
)
from omniconvert.core.errors import DependencyMissingError, UnsupportedConversionError
from omniconvert.core.formats import FormatId
from omniconvert.core.job import ConversionResult


# When LibreOffice (or another preferred engine) is available, hide portable
# fallbacks so the wheel offers the best-quality path by default.
_PREFERRED_OVER_FALLBACK: dict[str, str] = {
    "office.docx_to_pdf": "office.docx_to_pdf_text",
    "office.pptx_to_pdf": "office.pptx_to_pdf_text",
    "office.txt_to_pdf_lo": "text.txt_to_pdf",
}


class ConversionRegistry:
    def __init__(self) -> None:
        self._converters: list[Converter] = []
        self._ops: dict[str, tuple[Converter, ConversionOperation]] = {}

    def register(self, converter: Converter) -> None:
        self._converters.append(converter)
        for op in converter.operations():
            if op.operation_id in self._ops:
                raise ValueError(f"Duplicate operation id: {op.operation_id}")
            self._ops[op.operation_id] = (converter, op)

    def all_operations(self) -> list[ConversionOperation]:
        return [op for _, op in self._ops.values()]

    def get_operation(self, operation_id: str) -> ConversionOperation:
        try:
            return self._ops[operation_id][1]
        except KeyError as exc:
            raise UnsupportedConversionError("Unknown conversion operation.") from exc

    def available_operations_for(
        self,
        source_format: FormatId,
        *,
        include_unavailable: bool = False,
    ) -> list[ConversionOperation]:
        """Return operations whose source set includes *source_format*."""
        result: list[ConversionOperation] = []
        for converter, op in self._ops.values():
            if source_format not in op.source_formats:
                continue
            if not op.tested:
                continue
            if not include_unavailable and not converter.is_available():
                continue
            # External deps listed on the operation must also be available via converter.
            if op.requires_external and not converter.is_available():
                continue
            result.append(op)

        available_ids = {o.operation_id for o in result}
        suppressed = {
            fallback
            for preferred, fallback in _PREFERRED_OVER_FALLBACK.items()
            if preferred in available_ids
        }
        if suppressed:
            result = [o for o in result if o.operation_id not in suppressed]

        # Stable order by target label then id
        result.sort(key=lambda o: (o.segment_label, o.operation_id))
        return result

    def resolve_for_target(
        self,
        source_format: FormatId,
        target_format: FormatId | str,
    ) -> ConversionOperation:
        target = (
            target_format
            if isinstance(target_format, FormatId)
            else FormatId(target_format)
        )
        matches = [
            op
            for op in self.available_operations_for(source_format)
            if op.target_format == target
        ]
        if not matches:
            raise UnsupportedConversionError(
                f"No available conversion from {source_format.label} to {target.label}."
            )
        return matches[0]

    def convert(
        self,
        *,
        operation_id: str,
        source: Path,
        destination: Path,
        settings: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
        is_cancelled: CancelCheck | None = None,
    ) -> ConversionResult:
        try:
            converter, op = self._ops[operation_id]
        except KeyError as exc:
            raise UnsupportedConversionError("Unknown conversion operation.") from exc

        if not converter.is_available():
            raise DependencyMissingError(
                converter.availability_message()
                or "Required dependency is not available."
            )

        return converter.convert(
            operation_id=op.operation_id,
            source=source,
            destination=destination,
            settings=settings or {},
            progress=progress,
            is_cancelled=is_cancelled,
        )


_REGISTRY: ConversionRegistry | None = None


def get_registry() -> ConversionRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = build_default_registry()
    return _REGISTRY


def reset_registry_for_tests() -> None:
    global _REGISTRY
    _REGISTRY = None


def build_default_registry() -> ConversionRegistry:
    from omniconvert.converters import register_all

    registry = ConversionRegistry()
    register_all(registry)
    return registry
