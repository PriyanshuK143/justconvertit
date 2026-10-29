"""LibreOffice-based high-fidelity document conversions.

Uses the system LibreOffice install (apt/snap on Ubuntu, or a custom path).
Preferred over pure-Python text PDF when available — better layout, fonts, and Unicode.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
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
from omniconvert.platform.paths import user_engine_work_dir
from omniconvert.platform.subprocess_util import run_capture
from omniconvert.services.dependencies import get_dependency_service

log = logging.getLogger("omniconvert.libreoffice")

# operation_id → (convert-to filter, expected suffix, optional --infilter)
_CONVERT_TO: dict[str, tuple[str, str, str | None]] = {
    "office.docx_to_pdf": ("pdf:writer_pdf_Export", ".pdf", None),
    "office.pptx_to_pdf": ("pdf:impress_pdf_Export", ".pdf", None),
    "office.xlsx_to_pdf": ("pdf:calc_pdf_Export", ".pdf", None),
    "office.txt_to_pdf_lo": ("pdf:writer_pdf_Export", ".pdf", None),
    # Import PDF as Writer (not Draw) so DOCX export works.
    "office.pdf_to_docx": ("docx", ".docx", "writer_pdf_import"),
}


def find_libreoffice() -> str | None:
    return get_dependency_service().libreoffice_binary()


def _user_installation_uri(profile_dir: Path) -> str:
    """file:// URI for an isolated LO user profile (avoids lock conflicts)."""
    return profile_dir.resolve().as_uri()


class LibreOfficeConverter(Converter):
    """High-fidelity Office/PDF via system LibreOffice when installed."""

    def is_available(self) -> bool:
        return get_dependency_service().libreoffice.available

    def availability_message(self) -> str:
        return get_dependency_service().libreoffice.hint

    def operations(self) -> list[ConversionOperation]:
        return [
            ConversionOperation(
                operation_id="office.docx_to_pdf",
                label="DOCX → PDF",
                source_formats=frozenset({FormatId.DOCX}),
                target_format=FormatId.PDF,
                description=(
                    "Best layout fidelity Word → PDF using system LibreOffice "
                    "(fonts, images, and page structure preserved)."
                ),
                requires_external=("libreoffice",),
                wheel_label="PDF",
                tested=True,
            ),
            ConversionOperation(
                operation_id="office.pptx_to_pdf",
                label="PPTX → PDF",
                source_formats=frozenset({FormatId.PPTX}),
                target_format=FormatId.PDF,
                description="Best layout fidelity PowerPoint → PDF via LibreOffice.",
                requires_external=("libreoffice",),
                wheel_label="PDF",
                tested=True,
            ),
            ConversionOperation(
                operation_id="office.xlsx_to_pdf",
                label="XLSX → PDF",
                source_formats=frozenset({FormatId.XLSX}),
                target_format=FormatId.PDF,
                description="Spreadsheet → PDF via LibreOffice Calc export.",
                requires_external=("libreoffice",),
                wheel_label="PDF",
                tested=True,
            ),
            ConversionOperation(
                operation_id="office.txt_to_pdf_lo",
                label="TXT → PDF",
                source_formats=frozenset({FormatId.TXT}),
                target_format=FormatId.PDF,
                description=(
                    "Plain text → PDF via LibreOffice Writer "
                    "(better Unicode than the portable text PDF)."
                ),
                requires_external=("libreoffice",),
                wheel_label="PDF",
                tested=True,
            ),
            ConversionOperation(
                operation_id="office.pdf_to_docx",
                label="PDF → DOCX",
                source_formats=frozenset({FormatId.PDF}),
                target_format=FormatId.DOCX,
                description=(
                    "Best-effort PDF → Word via LibreOffice (not pixel-perfect). "
                    "Works best on text PDFs; scanned pages stay as images."
                ),
                requires_external=("libreoffice",),
                wheel_label="DOCX",
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
        binary = find_libreoffice()
        if not binary:
            raise DependencyMissingError(self.availability_message())

        spec = _CONVERT_TO.get(operation_id)
        if spec is None:
            raise ConversionFailedError("Unknown LibreOffice operation.")
        convert_to, suffix, infilter = spec

        check_cancelled(is_cancelled)
        if progress:
            progress(None, "Running LibreOffice (may take a while)…")

        env = {**os.environ, "SAL_USE_VCLPLUGIN": "svp"}
        try:
            produced_data = self._run_lo(
                binary=binary,
                source=source,
                convert_to=convert_to,
                infilter=infilter,
                env=env,
                is_cancelled=is_cancelled,
            )
        except ConversionFailedError:
            if ":" in convert_to:
                bare = convert_to.split(":", 1)[0]
                log.info("Retrying LibreOffice with bare filter %s", bare)
                produced_data = self._run_lo(
                    binary=binary,
                    source=source,
                    convert_to=bare,
                    infilter=infilter,
                    env=env,
                    is_cancelled=is_cancelled,
                )
            else:
                raise

        check_cancelled(is_cancelled)
        with AtomicWriter(destination) as tmp:
            Path(tmp).write_bytes(produced_data)
        size = verify_output(destination)
        verify_output_magic(destination, expected_suffix=suffix)
        if progress:
            progress(1.0, "Done")
        return ConversionResult(
            destination,
            size,
            "Converted with LibreOffice (best available layout).",
        )

    def _run_lo(
        self,
        *,
        binary: str,
        source: Path,
        convert_to: str,
        infilter: str | None,
        env: dict[str, str],
        is_cancelled: CancelCheck | None,
    ) -> bytes:
        # Snap LibreOffice cannot use ~/.cache or host /tmp; use ~/justconvertit/work.
        work_root = user_engine_work_dir() / "lo"
        work_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="omniconvert-lo-", dir=str(work_root)) as tmp:
            outdir = Path(tmp) / "out"
            profile = Path(tmp) / "profile"
            indir = Path(tmp) / "in"
            outdir.mkdir()
            profile.mkdir()
            indir.mkdir()
            local_source = indir / source.name
            local_source.write_bytes(source.read_bytes())
            is_snap = "snap" in Path(binary).parts

            cmd = [
                binary,
                "--headless",
                "--nologo",
                "--norestore",
                "--nofirststartwizard",
                "--nolockcheck",
            ]
            if not is_snap:
                cmd.append(f"-env:UserInstallation={_user_installation_uri(profile)}")
            if infilter:
                # Single argv form required by Snap LibreOffice ("--infilter x" is rejected).
                cmd.append(f"--infilter={infilter}")
            cmd.extend(
                [
                    "--convert-to",
                    convert_to,
                    "--outdir",
                    str(outdir),
                    str(local_source),
                ]
            )
            try:
                proc = run_capture(
                    cmd,
                    timeout=SUBPROCESS_TIMEOUT_SECONDS,
                    env=env,
                )
            except subprocess.TimeoutExpired as exc:
                raise ConversionFailedError(
                    "LibreOffice timed out. Try again, or open the file in LibreOffice directly."
                ) from exc
            except OSError as exc:
                raise ConversionFailedError(
                    "Could not start LibreOffice.",
                    detail=str(exc),
                ) from exc

            check_cancelled(is_cancelled)
            # convert_to like "pdf:writer_pdf_Export" → look for .pdf
            ext = convert_to.split(":", 1)[0]
            if not ext.startswith("."):
                ext = f".{ext}"
            produced = self._find_output(outdir, ext)
            if produced is None:
                log.warning(
                    "LibreOffice produced no %s (rc=%s): %s",
                    ext,
                    proc.returncode,
                    (proc.stderr or proc.stdout or "")[:500],
                )
                raise ConversionFailedError("LibreOffice did not produce an output file.")
            if proc.returncode != 0:
                log.warning("LibreOffice rc=%s: %s", proc.returncode, (proc.stderr or "")[:500])
            return produced.read_bytes()

    @staticmethod
    def _find_output(outdir: Path, suffix: str) -> Path | None:
        matches = sorted(outdir.glob(f"*{suffix}"))
        return matches[0] if matches else None
