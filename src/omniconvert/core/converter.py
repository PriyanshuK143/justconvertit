"""Converter protocol and operation descriptors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from omniconvert.core.formats import FormatId
from omniconvert.core.job import ConversionResult

ProgressCallback = Callable[[float | None, str], None]
CancelCheck = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class SettingSpec:
    key: str
    label: str
    kind: str  # "int" | "float" | "bool" | "choice" | "color"
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] = ()
    help_text: str = ""


@dataclass(frozen=True, slots=True)
class ConversionOperation:
    """One convertible edge exposed to the UI / router."""

    operation_id: str
    label: str
    source_formats: frozenset[FormatId]
    target_format: FormatId
    description: str = ""
    settings: tuple[SettingSpec, ...] = ()
    supports_batch: bool = True
    requires_external: tuple[str, ...] = ()  # e.g. ("libreoffice", "ffmpeg")
    tested: bool = True
    wheel_label: str | None = None  # short label for radial segment

    @property
    def segment_label(self) -> str:
        return self.wheel_label or self.target_format.label


class Converter(ABC):
    """Base class for conversion handlers."""

    @abstractmethod
    def operations(self) -> list[ConversionOperation]:
        """Declare supported operations."""

    @abstractmethod
    def convert(
        self,
        *,
        operation_id: str,
        source: Path,
        destination: Path,
        settings: dict[str, Any],
        progress: ProgressCallback | None = None,
        is_cancelled: CancelCheck | None = None,
    ) -> ConversionResult:
        """Perform conversion into *destination* (final path)."""

    def is_available(self) -> bool:
        return True

    def availability_message(self) -> str:
        return ""


def check_cancelled(is_cancelled: CancelCheck | None) -> None:
    from omniconvert.core.errors import CancelledError

    if is_cancelled and is_cancelled():
        raise CancelledError("Conversion cancelled.")
