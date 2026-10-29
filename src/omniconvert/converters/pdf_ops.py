"""PDF operations via pypdf, ReportLab, and pypdfium2 (bundled PDFium)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

from omniconvert.core.converter import (
    CancelCheck,
    ConversionOperation,
    Converter,
    ProgressCallback,
    check_cancelled,
)
from omniconvert.core.errors import ConversionFailedError, ResourceLimitError, ValidationError
from omniconvert.core.formats import IMAGE_FORMATS, FormatId
from omniconvert.core.job import ConversionResult
from omniconvert.core.limits import (
    MAX_PDF_PAGES,
    MAX_PDF_RENDER_PAGES,
    MAX_PDF_RENDER_SCALE,
    MAX_PDF_RENDER_TOTAL_PIXELS,
)
from omniconvert.core.output import AtomicWriter, verify_output


def _open_pdfium(source: Path) -> Any:
    import pypdfium2 as pdfium

    try:
        return pdfium.PdfDocument(str(source))
    except Exception as exc:  # noqa: BLE001 — pdfium raises varied errors
        raise ValidationError(
            "Could not open PDF for rendering. It may be corrupt or password-protected.",
            detail=str(exc),
        ) from exc


class PdfOpsConverter(Converter):
    def operations(self) -> list[ConversionOperation]:
        ops = [
            ConversionOperation(
                operation_id="pdf.extract_text",
                label="PDF → TXT",
                source_formats=frozenset({FormatId.PDF}),
                target_format=FormatId.TXT,
                description="Extract embedded text from a PDF (not OCR).",
                tested=True,
            ),
            ConversionOperation(
                operation_id="pdf.to_png",
                label="PDF → PNG",
                source_formats=frozenset({FormatId.PDF}),
                target_format=FormatId.PNG,
                description="Render page 1 to a PNG image (bundled PDFium).",
                tested=True,
            ),
            ConversionOperation(
                operation_id="pdf.to_jpeg",
                label="PDF → JPEG",
                source_formats=frozenset({FormatId.PDF}),
                target_format=FormatId.JPEG,
                description="Render page 1 to a JPEG image (bundled PDFium).",
                tested=True,
            ),
            ConversionOperation(
                operation_id="pdf.pages_to_zip",
                label="PDF pages → ZIP",
                source_formats=frozenset({FormatId.PDF}),
                target_format=FormatId.ZIP,
                description=(
                    f"Render each page to PNG and pack into a ZIP "
                    f"(max {MAX_PDF_RENDER_PAGES} pages; portable)."
                ),
                wheel_label="Pages ZIP",
                supports_batch=False,
                tested=True,
            ),
        ]
        for src in IMAGE_FORMATS:
            ops.append(
                ConversionOperation(
                    operation_id=f"pdf.image_{src.value}_to_pdf",
                    label=f"{src.label} → PDF",
                    source_formats=frozenset({src}),
                    target_format=FormatId.PDF,
                    description=f"Embed {src.label} image into a PDF page.",
                    tested=True,
                )
            )
        return ops

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
        from pypdf.errors import PdfReadError

        check_cancelled(is_cancelled)
        _ = settings
        try:
            if operation_id == "pdf.extract_text":
                return self._extract_text(source, destination, progress, is_cancelled)
            if operation_id == "pdf.to_png":
                return self._render_page(source, destination, "PNG", progress, is_cancelled)
            if operation_id == "pdf.to_jpeg":
                return self._render_page(source, destination, "JPEG", progress, is_cancelled)
            if operation_id == "pdf.pages_to_zip":
                return self._pages_to_zip(source, destination, progress, is_cancelled)
            if operation_id.startswith("pdf.image_"):
                return self._image_to_pdf(source, destination, progress, is_cancelled)
            raise ConversionFailedError("Unknown PDF operation.")
        except PdfReadError as exc:
            raise ValidationError(
                "Could not read PDF. It may be corrupt or password-protected.",
                detail=str(exc),
            ) from exc

    def _extract_text(
        self,
        source: Path,
        destination: Path,
        progress: ProgressCallback | None,
        is_cancelled: CancelCheck | None,
    ) -> ConversionResult:
        from pypdf import PdfReader

        if progress:
            progress(0.1, "Opening PDF…")
        reader = PdfReader(str(source))
        if reader.is_encrypted:
            raise ValidationError("Password-protected PDFs are not supported.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValidationError(f"PDF exceeds {MAX_PDF_PAGES} pages.")

        parts: list[str] = []
        total = max(len(reader.pages), 1)
        for i, page in enumerate(reader.pages):
            check_cancelled(is_cancelled)
            parts.append(page.extract_text() or "")
            if progress:
                progress((i + 1) / total * 0.85, f"Extracting page {i + 1}/{total}…")

        text = "\n\n".join(parts)
        with AtomicWriter(destination) as tmp:
            Path(tmp).write_text(text, encoding="utf-8")
        size = verify_output(destination, min_bytes=0)
        if progress:
            progress(1.0, "Done")
        return ConversionResult(destination, size, "Extracted text from PDF (not OCR).")

    def _render_page(
        self,
        source: Path,
        destination: Path,
        pil_format: str,
        progress: ProgressCallback | None,
        is_cancelled: CancelCheck | None,
    ) -> ConversionResult:
        if progress:
            progress(0.15, "Rendering PDF page…")
        doc = _open_pdfium(source)
        try:
            if len(doc) < 1:
                raise ValidationError("PDF has no pages.")
            check_cancelled(is_cancelled)
            page = doc[0]
            # scale=2 ≈ 144 DPI equivalent for sharper output
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()
            if pil_format == "JPEG" and pil_image.mode in ("RGBA", "LA", "P"):
                pil_image = pil_image.convert("RGB")
            with AtomicWriter(destination) as tmp:
                save_kwargs: dict[str, Any] = {}
                if pil_format == "JPEG":
                    save_kwargs["quality"] = 90
                pil_image.save(tmp, format=pil_format, **save_kwargs)
        finally:
            doc.close()
        size = verify_output(destination)
        if progress:
            progress(1.0, "Done")
        return ConversionResult(destination, size, f"Rendered PDF page 1 to {pil_format}.")

    def _pages_to_zip(
        self,
        source: Path,
        destination: Path,
        progress: ProgressCallback | None,
        is_cancelled: CancelCheck | None,
    ) -> ConversionResult:
        if progress:
            progress(0.05, "Opening PDF…")
        doc = _open_pdfium(source)
        try:
            n = len(doc)
            if n < 1:
                raise ValidationError("PDF has no pages.")
            if n > MAX_PDF_RENDER_PAGES:
                raise ResourceLimitError(
                    f"PDF has too many pages to render into a ZIP "
                    f"(max {MAX_PDF_RENDER_PAGES}).",
                )
            if n > MAX_PDF_PAGES:
                raise ResourceLimitError(f"PDF exceeds {MAX_PDF_PAGES} pages.")
            total_pixels = 0
            with AtomicWriter(destination) as tmp:
                with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for i in range(n):
                        check_cancelled(is_cancelled)
                        page = doc[i]
                        bitmap = page.render(scale=MAX_PDF_RENDER_SCALE)
                        pil_image = bitmap.to_pil()
                        w, h = pil_image.size
                        total_pixels += w * h
                        if total_pixels > MAX_PDF_RENDER_TOTAL_PIXELS:
                            raise ResourceLimitError(
                                "PDF pages are too large to render safely.",
                            )
                        buf = io.BytesIO()
                        pil_image.save(buf, format="PNG")
                        zf.writestr(f"page_{i + 1:04d}.png", buf.getvalue())
                        if progress:
                            progress((i + 1) / n * 0.95, f"Page {i + 1}/{n}…")
        finally:
            doc.close()
        size = verify_output(destination)
        if progress:
            progress(1.0, "Done")
        return ConversionResult(destination, size, f"Packed {n} PNG pages into a ZIP.")

    def _image_to_pdf(
        self,
        source: Path,
        destination: Path,
        progress: ProgressCallback | None,
        is_cancelled: CancelCheck | None,
    ) -> ConversionResult:
        from PIL import Image, ImageOps
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas

        if progress:
            progress(0.2, "Opening image…")
        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            check_cancelled(is_cancelled)
            if progress:
                progress(0.5, "Writing PDF…")
            with AtomicWriter(destination) as tmp:
                c = canvas.Canvas(str(tmp), pagesize=letter)
                page_w, page_h = letter
                iw, ih = img.size
                scale = min(page_w / iw, page_h / ih) * 0.95
                w, h = iw * scale, ih * scale
                x, y = (page_w - w) / 2, (page_h - h) / 2
                c.drawImage(ImageReader(img), x, y, width=w, height=h, preserveAspectRatio=True)
                c.showPage()
                c.save()
        size = verify_output(destination)
        if progress:
            progress(1.0, "Done")
        return ConversionResult(destination, size, "Created PDF from image.")


def merge_pdfs(sources: list[Path], destination: Path) -> ConversionResult:
    """Merge multiple PDFs — used by batch UI."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for src in sources:
        reader = PdfReader(str(src))
        if reader.is_encrypted:
            raise ValidationError(f"Password-protected PDF skipped: {src.name}")
        for page in reader.pages:
            writer.add_page(page)
    with AtomicWriter(destination) as tmp:
        with open(tmp, "wb") as fh:
            writer.write(fh)
    size = verify_output(destination)
    return ConversionResult(destination, size, f"Merged {len(sources)} PDFs.")
