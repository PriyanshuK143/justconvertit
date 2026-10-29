"""Text and JSON utility conversions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omniconvert.core.converter import (
    CancelCheck,
    ConversionOperation,
    Converter,
    ProgressCallback,
    SettingSpec,
    check_cancelled,
)
from omniconvert.core.errors import ConversionFailedError, ValidationError
from omniconvert.core.formats import FormatId
from omniconvert.core.job import ConversionResult
from omniconvert.core.limits import MAX_TEXT_BYTES
from omniconvert.core.output import AtomicWriter, verify_output


def _read_text(path: Path) -> str:
    if path.stat().st_size > MAX_TEXT_BYTES:
        raise ValidationError(
            f"Text file exceeds {MAX_TEXT_BYTES // (1024 * 1024)} MiB limit."
        )
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValidationError("Could not decode text file with a supported encoding.")


def _text_to_pdf(text: str, destination: Path) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    with AtomicWriter(destination) as tmp:
        c = canvas.Canvas(str(tmp), pagesize=letter)
        width, height = letter
        left, top, bottom = 50, height - 50, 50
        y = top
        c.setFont("Helvetica", 10)
        for line in text.splitlines() or [""]:
            # Very long lines: wrap roughly by character count
            while line:
                chunk = line[:95]
                line = line[95:]
                if y < bottom:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = top
                # ReportLab needs escape of non-latin1 for default fonts — replace
                safe = chunk.encode("latin-1", errors="replace").decode("latin-1")
                c.drawString(left, y, safe)
                y -= 14
        c.save()


class TextOpsConverter(Converter):
    def operations(self) -> list[ConversionOperation]:
        return [
            ConversionOperation(
                operation_id="text.json_format",
                label="Format JSON",
                source_formats=frozenset({FormatId.JSON}),
                target_format=FormatId.JSON,
                description="Validate and pretty-print JSON.",
                wheel_label="Pretty JSON",
                settings=(
                    SettingSpec(
                        key="indent",
                        label="Indent",
                        kind="int",
                        default=2,
                        minimum=0,
                        maximum=8,
                    ),
                ),
                tested=True,
            ),
            ConversionOperation(
                operation_id="text.txt_to_pdf",
                label="TXT → PDF (portable)",
                source_formats=frozenset({FormatId.TXT}),
                target_format=FormatId.PDF,
                description=(
                    "Simple portable PDF from plain text. "
                    "Hidden when LibreOffice is installed (better Unicode/layout)."
                ),
                wheel_label="PDF (text)",
                tested=True,
            ),
            ConversionOperation(
                operation_id="text.json_to_pdf",
                label="JSON → PDF",
                source_formats=frozenset({FormatId.JSON}),
                target_format=FormatId.PDF,
                description="Render JSON text into a simple PDF.",
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
        check_cancelled(is_cancelled)
        if progress:
            progress(0.2, "Reading…")

        try:
            if operation_id == "text.json_format":
                text = _read_text(source)
                data = json.loads(text)
                check_cancelled(is_cancelled)
                indent = int(settings.get("indent", 2))
                indent = max(0, min(8, indent))
                with AtomicWriter(destination) as tmp:
                    Path(tmp).write_text(
                        json.dumps(data, indent=indent, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                msg = "JSON validated and formatted."
            elif operation_id in {"text.txt_to_pdf", "text.json_to_pdf"}:
                text = _read_text(source)
                if operation_id == "text.json_to_pdf":
                    # Validate JSON then pretty print into PDF
                    data = json.loads(text)
                    text = json.dumps(data, indent=2, ensure_ascii=False)
                check_cancelled(is_cancelled)
                if progress:
                    progress(0.5, "Writing PDF…")
                _text_to_pdf(text, destination)
                msg = "PDF created from text."
            else:
                raise ConversionFailedError("Unknown text operation.")

            size = verify_output(destination)
            if progress:
                progress(1.0, "Done")
            return ConversionResult(destination, size, msg)
        except json.JSONDecodeError as exc:
            raise ValidationError("Invalid JSON.", detail=str(exc)) from exc
        except OSError as exc:
            raise ConversionFailedError("Could not complete text conversion.", detail=str(exc)) from exc
