"""Optional SVG conversions via system Inkscape."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from omniconvert.core.converter import (
    CancelCheck,
    ConversionOperation,
    Converter,
    ProgressCallback,
    check_cancelled,
)
from omniconvert.core.errors import ConversionFailedError, DependencyMissingError
from omniconvert.core.formats import FormatId
from omniconvert.core.job import ConversionResult
from omniconvert.core.limits import SUBPROCESS_TIMEOUT_SECONDS
from omniconvert.core.output import AtomicWriter, verify_output, verify_output_magic
from omniconvert.platform.subprocess_util import run_capture

log = logging.getLogger("omniconvert.inkscape")


def find_inkscape() -> str | None:
    names = ("inkscape", "inkscape.exe")
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    if sys.platform.startswith("linux"):
        for cand in (
            Path("/usr/bin/inkscape"),
            Path("/snap/bin/inkscape"),
        ):
            if cand.is_file():
                return str(cand)
    if sys.platform.startswith("win"):
        import os

        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            root = os.environ.get(env)
            if not root:
                continue
            cand = Path(root) / "Inkscape" / "bin" / "inkscape.exe"
            if cand.is_file():
                return str(cand)
    return None


class InkscapeConverter(Converter):
    def is_available(self) -> bool:
        return find_inkscape() is not None

    def availability_message(self) -> str:
        if sys.platform.startswith("linux"):
            return (
                "Install Inkscape with: sudo apt install inkscape "
                "(enables SVG → PNG / PDF)."
            )
        return (
            "Install Inkscape from https://inkscape.org/ "
            "(enables SVG → PNG / PDF)."
        )

    def operations(self) -> list[ConversionOperation]:
        return [
            ConversionOperation(
                operation_id="svg.to_png",
                label="SVG → PNG",
                source_formats=frozenset({FormatId.SVG}),
                target_format=FormatId.PNG,
                description="Rasterize SVG to PNG via Inkscape.",
                requires_external=("inkscape",),
                tested=True,
            ),
            ConversionOperation(
                operation_id="svg.to_pdf",
                label="SVG → PDF",
                source_formats=frozenset({FormatId.SVG}),
                target_format=FormatId.PDF,
                description="Export SVG to PDF via Inkscape.",
                requires_external=("inkscape",),
                tested=True,
            ),
        ]

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
        _ = settings
        binary = find_inkscape()
        if not binary:
            raise DependencyMissingError(self.availability_message())

        if operation_id == "svg.to_png":
            export_type = "png"
            magic = ".png"
            msg = "SVG rasterized to PNG."
        elif operation_id == "svg.to_pdf":
            export_type = "pdf"
            magic = ".pdf"
            msg = "SVG exported to PDF."
        else:
            raise ConversionFailedError("Unknown SVG operation.")

        check_cancelled(is_cancelled)
        if progress:
            progress(0.2, "Running Inkscape…")

        with AtomicWriter(destination) as tmp:
            cmd = [
                binary,
                str(source),
                f"--export-type={export_type}",
                f"--export-filename={tmp}",
            ]
            try:
                proc = run_capture(cmd, timeout=SUBPROCESS_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as exc:
                raise ConversionFailedError("Inkscape timed out.") from exc
            except OSError as exc:
                raise ConversionFailedError(
                    "Could not start Inkscape.",
                    detail=str(exc),
                ) from exc
            check_cancelled(is_cancelled)
            if proc.returncode != 0:
                log.warning("Inkscape failed: %s", (proc.stderr or "")[:500])
                raise ConversionFailedError("Inkscape could not convert the SVG.")

        size = verify_output(destination)
        verify_output_magic(destination, expected_suffix=magic)
        if progress:
            progress(1.0, "Done")
        return ConversionResult(destination, size, msg)
