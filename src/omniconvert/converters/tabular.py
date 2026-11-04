"""CSV / JSON / XLSX structured-data conversions (stdlib + openpyxl only)."""

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


def _csv_to_xlsx_fast(source: Path, destination: Path) -> None:
    """Flat CSV → XLSX via openpyxl."""
    from openpyxl import Workbook

    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Sheet1")
    with source.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        any_row = False
        for row in reader:
            ws.append(list(row))
            any_row = True
        if not any_row:
            ws.append([])
    wb.save(destination)


def _xlsx_to_csv_fast(source: Path, destination: Path) -> None:
    """First sheet XLSX → CSV via openpyxl read_only."""
    from openpyxl import load_workbook

    wb = load_workbook(source, read_only=True, data_only=True)
    try:
        ws = wb.worksheets[0]
        with destination.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                writer.writerow(["" if c is None else c for c in row])
    finally:
        wb.close()


def _records_to_xlsx(records: list[dict[str, Any]], destination: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Sheet1")
    if not records:
        ws.append([])
        wb.save(destination)
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in records:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    ws.append(fieldnames)
    for row in records:
        ws.append([row.get(k, "") for k in fieldnames])
    wb.save(destination)


def _xlsx_to_records(source: Path) -> list[dict[str, Any]]:
    from openpyxl import load_workbook

    wb = load_workbook(source, read_only=True, data_only=True)
    try:
        ws = wb.worksheets[0]
        rows = ws.iter_rows(values_only=True)
        try:
            header_row = next(rows)
        except StopIteration:
            return []
        headers = [
            str(h) if h is not None and str(h).strip() != "" else f"column_{i + 1}"
            for i, h in enumerate(header_row or ())
        ]
        if not headers:
            return []
        out: list[dict[str, Any]] = []
        for row in rows:
            values = list(row or ())
            # Pad / trim to header length
            if len(values) < len(headers):
                values.extend([None] * (len(headers) - len(values)))
            record = {
                headers[i]: (None if values[i] is None else values[i])
                for i in range(len(headers))
            }
            # Skip totally empty rows
            if all(v is None or v == "" for v in record.values()):
                continue
            out.append(record)
        return out
    finally:
        wb.close()


def _write_csv_records(records: list[dict[str, Any]], destination: Path) -> None:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in records:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with destination.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames or ["value"], extrasaction="ignore")
        writer.writeheader()
        for row in records:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fieldnames})


def _csv_to_records(source: Path) -> list[dict[str, Any]]:
    with source.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


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
            keys = list(data.keys())
            lengths = {len(data[k]) for k in keys}
            if len(lengths) != 1:
                raise ValidationError("Columnar JSON columns must have equal length.")
            n = next(iter(lengths)) if lengths else 0
            return [{k: data[k][i] for k in keys} for i in range(n)]
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
        check_cancelled(is_cancelled)
        _ = settings
        if progress:
            progress(0.15, "Reading data…")

        try:
            if operation_id == "data.csv_to_json":
                _ensure_text_size(source)
                records = _csv_to_records(source)
                check_cancelled(is_cancelled)
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
                with AtomicWriter(destination) as tmp:
                    _write_csv_records(records, Path(tmp))
            elif operation_id == "data.csv_to_xlsx":
                _ensure_text_size(source)
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    _csv_to_xlsx_fast(source, Path(tmp))
            elif operation_id == "data.xlsx_to_csv":
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    _xlsx_to_csv_fast(source, Path(tmp))
            elif operation_id == "data.json_to_xlsx":
                _ensure_text_size(source)
                data = json.loads(source.read_text(encoding="utf-8-sig"))
                records = _json_to_records(data)
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    _records_to_xlsx(records, Path(tmp))
            elif operation_id == "data.xlsx_to_json":
                records = _xlsx_to_records(source)
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
        except (csv.Error, ValueError) as exc:
            raise ValidationError("Could not read tabular data.", detail=str(exc)) from exc
        except OSError as exc:
            raise ConversionFailedError("I/O error during data conversion.", detail=str(exc)) from exc
