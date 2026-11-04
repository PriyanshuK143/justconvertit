from __future__ import annotations

import sys
from pathlib import Path

import pytest

from omniconvert.core.errors import ConversionFailedError
from omniconvert.core.registry import ConversionRegistry
from omniconvert.services.resilience import (
    install_exception_hooks,
    safe_slot,
    set_ui_error_reporter,
)


def test_safe_slot_swallows_and_reports() -> None:
    seen: list[tuple[str, str]] = []
    set_ui_error_reporter(lambda msg, kind: seen.append((msg, kind)))

    @safe_slot(user_message="soft fail")
    def boom() -> None:
        raise RuntimeError("kaboom")

    assert boom() is None
    assert seen and seen[-1] == ("soft fail", "err")
    set_ui_error_reporter(None)


def test_sys_excepthook_does_not_raise() -> None:
    seen: list[str] = []
    set_ui_error_reporter(lambda msg, kind: seen.append(msg))
    install_exception_hooks()
    sys.excepthook(RuntimeError, RuntimeError("x"), None)
    assert seen
    set_ui_error_reporter(None)


def test_registry_maps_unexpected_to_conversion_failed(
    tmp_path: Path,
) -> None:
    from omniconvert.core.converter import ConversionOperation, Converter
    from omniconvert.core.formats import FormatId

    class Boom(Converter):
        @property
        def id(self) -> str:
            return "boom"

        def operations(self):
            return (
                ConversionOperation(
                    operation_id="test.boom",
                    label="Boom",
                    source_formats=frozenset({FormatId.TXT}),
                    target_format=FormatId.TXT,
                ),
            )

        def is_available(self) -> bool:
            return True

        def convert(self, **kwargs):  # noqa: ANN003
            raise ValueError("parser exploded")

    reg = ConversionRegistry()
    reg.register(Boom())
    src = tmp_path / "a.txt"
    src.write_text("hi", encoding="utf-8")
    with pytest.raises(ConversionFailedError) as exc:
        reg.convert(
            operation_id="test.boom",
            source=src,
            destination=tmp_path / "b.txt",
        )
    assert "Couldn't convert" in exc.value.user_message
