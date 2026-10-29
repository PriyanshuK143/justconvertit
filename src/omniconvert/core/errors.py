"""Typed application errors with user-facing messages."""

from __future__ import annotations


class AppError(Exception):
    """Base error with a short user-facing message."""

    def __init__(self, user_message: str, *, detail: str | None = None) -> None:
        self.user_message = user_message
        self.detail = detail
        super().__init__(user_message)

    def __str__(self) -> str:
        if self.detail:
            return f"{self.user_message} ({self.detail})"
        return self.user_message


# Back-compat alias (older tests / imports).
OmniConvertError = AppError
JustConvertItError = AppError


class DetectionError(AppError):
    """Could not determine or validate file type."""


class UnsupportedConversionError(AppError):
    """Requested conversion is not available."""


class ValidationError(AppError):
    """Input failed validation."""


class ConversionFailedError(AppError):
    """Conversion ran but failed."""


class CancelledError(AppError):
    """Job was cancelled by the user."""


class DependencyMissingError(AppError):
    """Optional external dependency is not available."""


class OutputError(AppError):
    """Could not write or verify output."""


class ResourceLimitError(AppError):
    """File exceeded size or resource limits."""
