"""Guarantees for one-time-install / offline-first posture."""

from __future__ import annotations

import ast
from pathlib import Path

from omniconvert import product
from omniconvert.core.formats import FormatId
from omniconvert.core.registry import ConversionRegistry


SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "omniconvert"


def test_product_flags_disable_remote_features() -> None:
    assert product.OFFLINE_FIRST is True
    assert product.REQUIRES_ACCOUNT is False
    assert product.REQUIRES_INTERNET is False
    assert product.IN_APP_UPDATE_CHECKER is False
    assert product.AUTOMATIC_UPDATES is False
    assert product.TELEMETRY_ENABLED is False
    assert product.REMOTE_ANALYTICS is False
    assert product.CLOUD_CONVERSION is False
    assert product.OPTIONAL_ENGINES_LOCAL_ONLY is True


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
            names.add(node.module)
    return names


def test_no_forbidden_network_imports_in_package() -> None:
    offenders: list[str] = []
    for path in SRC_ROOT.rglob("*.py"):
        imported = _imported_modules(path)
        bad = imported & product.FORBIDDEN_NETWORK_MODULES
        # Also catch bare top-level names like "requests"
        top = {n.split(".")[0] for n in imported}
        bad |= top & {m.split(".")[0] for m in product.FORBIDDEN_NETWORK_MODULES}
        if bad:
            offenders.append(f"{path.relative_to(SRC_ROOT)}: {sorted(bad)}")
    assert offenders == [], "Network/client libraries must not be imported:\n" + "\n".join(
        offenders
    )


def test_core_ops_available_without_optional_engines(registry: ConversionRegistry) -> None:
    """Portable conversions must register regardless of LibreOffice/FFmpeg."""
    png_ops = {op.operation_id for op in registry.available_operations_for(FormatId.PNG)}
    assert any(oid.startswith("image.png_to_") for oid in png_ops)
    assert any(oid.endswith("_to_pdf") or "image_" in oid for oid in png_ops)

    pdf_ops = {op.operation_id for op in registry.available_operations_for(FormatId.PDF)}
    assert "pdf.extract_text" in pdf_ops
    assert "pdf.to_png" in pdf_ops
    assert "pdf.to_jpeg" in pdf_ops
    assert "pdf.pages_to_zip" in pdf_ops

    csv_ops = {op.operation_id for op in registry.available_operations_for(FormatId.CSV)}
    assert "data.csv_to_json" in csv_ops

    docx_ops = {op.operation_id for op in registry.available_operations_for(FormatId.DOCX)}
    assert "office.docx_to_txt" in docx_ops
    # Always a DOCX→PDF path: LibreOffice when installed, else portable text PDF.
    assert "office.docx_to_pdf_text" in docx_ops or "office.docx_to_pdf" in docx_ops


def test_offline_png_to_jpeg_conversion(
    registry: ConversionRegistry, sample_png: Path, tmp_path: Path
) -> None:
    dest = tmp_path / "out.jpg"
    result = registry.convert(
        operation_id="image.png_to_jpeg",
        source=sample_png,
        destination=dest,
        settings={"jpeg_quality": 85, "transparency_background": "#FFFFFF"},
    )
    assert result.output_path.exists()
    assert result.bytes_written > 0
