"""CSV / JSON / XLSX structured-data conversions."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from omniconvert.core.converter import (
    CancelCheck,
    ConversionOperation,
    Converter,
    ProgressCallback,
    check_cancelled,
)
from omniconvert.core.errors import ConversionFailedError, ValidationError
from omniconvert.core.formats import FormatId
from omniconvert.core.job import ConversionResult
from omniconvert.core.limits import MAX_TEXT_BYTES
from omniconvert.core.output import AtomicWriter, verify_output


def _ensure_text_size(path: Path) -> None:
    if path.stat().st_size > MAX_TEXT_BYTES:
        raise ValidationError(
            f"Text/data file exceeds {MAX_TEXT_BYTES // (1024 * 1024)} MiB limit."
        )


def _is_flat_value(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _json_to_records(data: Any) -> list[dict[str, Any]]:
    """Supported shapes: array of flat objects, array of scalars, columnar dict, flat object.

    Nested objects/arrays inside cells are rejected — they would silently lose structure.
    """
    if isinstance(data, list):
        if not data:
            return []
        if all(isinstance(x, dict) for x in data):
            for row in data:
                for key, val in row.items():
                    if not _is_flat_value(val):
                        raise ValidationError(
                            "JSON objects with nested arrays/objects cannot convert "
                            "to CSV/XLSX without data loss. Flatten the JSON first.",
                            detail=f"key={key!r}",
                        )
            return data
        if all(_is_flat_value(x) for x in data):
            return [{"value": x} for x in data]
        raise ValidationError(
            "JSON arrays must contain only flat values or flat objects for CSV/XLSX."
        )
    if isinstance(data, dict):
        # dict of lists (columnar) or single object
        if data and all(isinstance(v, list) for v in data.values()):
            for key, col in data.items():
                if not all(_is_flat_value(x) for x in col):
                    raise ValidationError(
                        "Columnar JSON values must be flat (no nested objects/arrays).",
                        detail=f"key={key!r}",
                    )
            import pandas as pd

            return pd.DataFrame(data).to_dict(orient="records")
        for key, val in data.items():
            if not _is_flat_value(val):
                raise ValidationError(
                    "JSON objects with nested arrays/objects cannot convert "
                    "to CSV/XLSX without data loss. Flatten the JSON first.",
                    detail=f"key={key!r}",
                )
        return [data]
    raise ValidationError(
        "JSON must be an object, an array of objects, or an array of values "
        "to convert to CSV/XLSX."
    )


class TabularConverter(Converter):
    def operations(self) -> list[ConversionOperation]:
        return [
            ConversionOperation(
                operation_id="data.csv_to_json",
                label="CSV → JSON",
                source_formats=frozenset({FormatId.CSV}),
                target_format=FormatId.JSON,
                description="Convert CSV rows to a JSON array of objects.",
                tested=True,
            ),
            ConversionOperation(
                operation_id="data.json_to_csv",
                label="JSON → CSV",
                source_formats=frozenset({FormatId.JSON}),
                target_format=FormatId.CSV,
                description="Convert JSON array/object to CSV.",
                tested=True,
            ),
            ConversionOperation(
                operation_id="data.csv_to_xlsx",
                label="CSV → XLSX",
                source_formats=frozenset({FormatId.CSV}),
                target_format=FormatId.XLSX,
                description="Convert CSV to Excel workbook.",
                tested=True,
            ),
            ConversionOperation(
                operation_id="data.xlsx_to_csv",
                label="XLSX → CSV",
                source_formats=frozenset({FormatId.XLSX}),
                target_format=FormatId.CSV,
                description="Convert first sheet of Excel workbook to CSV.",
                tested=True,
            ),
            ConversionOperation(
                operation_id="data.json_to_xlsx",
                label="JSON → XLSX",
                source_formats=frozenset({FormatId.JSON}),
                target_format=FormatId.XLSX,
                description="Convert JSON to Excel workbook.",
                tested=True,
            ),
            ConversionOperation(
                operation_id="data.xlsx_to_json",
                label="XLSX → JSON",
                source_formats=frozenset({FormatId.XLSX}),
                target_format=FormatId.JSON,
                description="Convert first Excel sheet to JSON array.",
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
        import pandas as pd

        check_cancelled(is_cancelled)
        _ = settings
        if progress:
            progress(0.15, "Reading data…")

        try:
            if operation_id == "data.csv_to_json":
                _ensure_text_size(source)
                df = pd.read_csv(source)
                check_cancelled(is_cancelled)
                records = df.where(pd.notnull(df), None).to_dict(orient="records")
                with AtomicWriter(destination) as tmp:
                    Path(tmp).write_text(
                        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
            elif operation_id == "data.json_to_csv":
                _ensure_text_size(source)
                data = json.loads(source.read_text(encoding="utf-8-sig"))
                records = _json_to_records(data)
                check_cancelled(is_cancelled)
                df = pd.DataFrame(records)
                with AtomicWriter(destination) as tmp:
                    df.to_csv(tmp, index=False)
            elif operation_id == "data.csv_to_xlsx":
                _ensure_text_size(source)
                df = pd.read_csv(source)
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    df.to_excel(tmp, index=False)
            elif operation_id == "data.xlsx_to_csv":
                df = pd.read_excel(source, sheet_name=0)
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    df.to_csv(tmp, index=False)
            elif operation_id == "data.json_to_xlsx":
                _ensure_text_size(source)
                data = json.loads(source.read_text(encoding="utf-8-sig"))
                records = _json_to_records(data)
                df = pd.DataFrame(records)
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    df.to_excel(tmp, index=False)
            elif operation_id == "data.xlsx_to_json":
                df = pd.read_excel(source, sheet_name=0)
                records = df.where(pd.notnull(df), None).to_dict(orient="records")
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    Path(tmp).write_text(
                        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
            else:
                raise ConversionFailedError("Unknown tabular operation.")

            if progress:
                progress(0.9, "Verifying…")
            size = verify_output(destination, min_bytes=0)
            if progress:
                progress(1.0, "Done")
            return ConversionResult(destination, size, "Data conversion completed.")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValidationError("Could not parse the input file.", detail=str(exc)) from exc
        except (pd.errors.ParserError, csv.Error, ValueError) as exc:
            raise ValidationError("Could not read tabular data.", detail=str(exc)) from exc
        except OSError as exc:
            raise ConversionFailedError("I/O error during data conversion.", detail=str(exc)) from exc
