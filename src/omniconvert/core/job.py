"""Conversion job models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ConversionProgress:
    fraction: float | None = None  # None = indeterminate
    message: str = ""


@dataclass(slots=True)
class ConversionJob:
    source_path: Path
    target_format: str
    output_dir: Path
    output_name: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    operation_id: str | None = None
    job_id: str = field(default_factory=lambda: uuid4().hex)
    status: JobStatus = JobStatus.PENDING
    progress: ConversionProgress = field(default_factory=ConversionProgress)
    result_path: Path | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ConversionResult:
    output_path: Path
    bytes_written: int
    message: str = "Conversion completed."
