"""Portable DOCX helpers — structure + images with bundled libs only (no LibreOffice)."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any, Iterator

from omniconvert.core.errors import ValidationError
from omniconvert.core.output import AtomicWriter, verify_output


def _open_docx(source: Path) -> Any:
    from docx import Document

    try:
        return Document(str(source))
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("Could not read DOCX file.", detail=str(exc)) from exc


def iter_block_items(doc: Any) -> Iterator[Any]:
    """Yield paragraphs and tables in document order."""
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def _heading_level(paragraph: Any) -> int | None:
    style = getattr(paragraph, "style", None)
    name = (getattr(style, "name", None) or "").strip()
    if not name:
        return None
    lower = name.lower()
    if lower.startswith("heading"):
        parts = name.split()
        if len(parts) >= 2 and parts[-1].isdigit():
            level = int(parts[-1])
            if 1 <= level <= 6:
                return level
    if lower in {"title", "subtitle"}:
        return 1 if lower == "title" else 2
    return None


def _list_prefix(paragraph: Any) -> str | None:
    """Return markdown/plain list marker if paragraph looks like a list item."""
    try:
        ppr = paragraph._p.pPr  # noqa: SLF001 — python-docx private but stable enough
        if ppr is None or ppr.numPr is None:
            return None
    except Exception:  # noqa: BLE001
        return None
    style = (getattr(getattr(paragraph, "style", None), "name", None) or "").lower()
    if "number" in style:
        return "1. "
    return "- "


def _escape_md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _table_rows(table: Any) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
        rows.append(cells)
    return rows


def docx_to_plain(source: Path) -> str:
    """Ordered plain text: headings, paragraphs, tables (tab-separated)."""
    doc = _open_docx(source)
    parts: list[str] = []
    for block in iter_block_items(doc):
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            prefix = _list_prefix(block)
            if prefix:
                parts.append(f"{prefix}{text}")
            else:
                parts.append(text)
            parts.append("")
        elif isinstance(block, Table):
            for row in _table_rows(block):
                if any(row):
                    parts.append("\t".join(row))
            parts.append("")
    text = "\n".join(parts).rstrip() + ("\n" if parts else "")
    # Collapse excess blank lines
    return re.sub(r"\n{3,}", "\n\n", text)


def docx_to_markdown(source: Path) -> str:
    """Ordered Markdown with headings and pipe tables."""
    doc = _open_docx(source)
    parts: list[str] = []
    for block in iter_block_items(doc):
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            level = _heading_level(block)
            prefix = _list_prefix(block)
            if level:
                parts.append(f"{'#' * level} {text}")
            elif prefix:
                parts.append(f"{prefix}{text}")
            else:
                parts.append(text)
            parts.append("")
        elif isinstance(block, Table):
            rows = _table_rows(block)
            if not rows:
                continue
            width = max(len(r) for r in rows)
            normalized = [r + [""] * (width - len(r)) for r in rows]
            header = normalized[0]
            parts.append(
                "| " + " | ".join(_escape_md_cell(c) for c in header) + " |"
            )
            parts.append("| " + " | ".join("---" for _ in header) + " |")
            for row in normalized[1:]:
                parts.append(
                    "| " + " | ".join(_escape_md_cell(c) for c in row) + " |"
                )
            parts.append("")
    text = "\n".join(parts).rstrip() + ("\n" if parts else "")
    return re.sub(r"\n{3,}", "\n\n", text)


def _image_ext(content_type: str, blob: bytes) -> str:
    ct = (content_type or "").lower()
    if "png" in ct:
        return ".png"
    if "jpeg" in ct or "jpg" in ct:
        return ".jpg"
    if "gif" in ct:
        return ".gif"
    if "bmp" in ct:
        return ".bmp"
    if "tiff" in ct:
        return ".tiff"
    if "webp" in ct:
        return ".webp"
    # Sniff
    if blob.startswith(b"\x89PNG"):
        return ".png"
    if blob[:2] == b"\xff\xd8":
        return ".jpg"
    if blob.startswith(b"GIF8"):
        return ".gif"
    return ".bin"


def collect_docx_images(source: Path) -> list[tuple[str, bytes]]:
    """Return (filename, bytes) for embedded images (deduped by part)."""
    doc = _open_docx(source)
    seen: set[str] = set()
    out: list[tuple[str, bytes]] = []
    try:
        rels = doc.part.rels.values()
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("Could not read images from DOCX.", detail=str(exc)) from exc

    index = 1
    for rel in rels:
        reltype = (getattr(rel, "reltype", "") or "").lower()
        if "image" not in reltype:
            continue
        try:
            part = rel.target_part
            blob = part.blob
            r_id = getattr(rel, "rId", None) or str(id(rel))
        except Exception:  # noqa: BLE001
            continue
        if r_id in seen or not blob:
            continue
        seen.add(r_id)
        ct = getattr(part, "content_type", "") or ""
        ext = _image_ext(ct, blob)
        out.append((f"image_{index:03d}{ext}", blob))
        index += 1
    return out


def write_images_zip(destination: Path, images: list[tuple[str, bytes]]) -> int:
    if not images:
        raise ValidationError("No images found in this document.")
    with AtomicWriter(destination) as tmp:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name, blob in images:
                zf.writestr(name, blob)
    return verify_output(destination)


def docx_to_pdf(source: Path, destination: Path) -> None:
    """Portable PDF: headings, paragraphs, tables, and embedded images."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Image as RLImage,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table as RLTable,
        TableStyle,
    )

    doc = _open_docx(source)
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "BodyPortable",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )
    heading_styles = {
        1: ParagraphStyle(
            "H1Portable", parent=styles["Heading1"], fontSize=16, spaceAfter=10
        ),
        2: ParagraphStyle(
            "H2Portable", parent=styles["Heading2"], fontSize=14, spaceAfter=8
        ),
        3: ParagraphStyle(
            "H3Portable", parent=styles["Heading3"], fontSize=12, spaceAfter=6
        ),
    }

    def _safe_para(text: str, style: ParagraphStyle) -> Paragraph:
        # ReportLab XML-ish escaping
        safe = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        # Helvetica is latin-1 limited — replace unsupported glyphs
        safe = safe.encode("latin-1", errors="replace").decode("latin-1")
        return Paragraph(safe, style)

    story: list[Any] = []
    max_img_w = 6.0 * inch

    # Preload images by rId for inline placement when possible
    image_parts: dict[str, bytes] = {}
    try:
        for rel in doc.part.rels.values():
            if "image" in (getattr(rel, "reltype", "") or "").lower():
                try:
                    image_parts[rel.rId] = rel.target_part.blob
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        image_parts = {}

    used_images: set[str] = set()

    from docx.table import Table as DocxTable
    from docx.text.paragraph import Paragraph as DocxParagraph

    for block in iter_block_items(doc):
        if isinstance(block, DocxParagraph):
            text = block.text.strip()
            level = _heading_level(block)
            if text:
                if level:
                    style = heading_styles.get(min(level, 3), heading_styles[3])
                    story.append(_safe_para(text, style))
                else:
                    prefix = _list_prefix(block) or ""
                    story.append(_safe_para(f"{prefix}{text}", body))

            # Drawings / pictures referenced from this paragraph
            try:
                blips = block._p.xpath(  # noqa: SLF001
                    ".//*[local-name()='blip']"
                )
                for blip in blips:
                    embed = blip.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
                    )
                    if not embed or embed in used_images:
                        continue
                    blob = image_parts.get(embed)
                    if not blob:
                        continue
                    used_images.add(embed)
                    img = _rl_image_from_blob(blob, max_img_w)
                    if img is not None:
                        story.append(Spacer(1, 6))
                        story.append(img)
                        story.append(Spacer(1, 8))
            except Exception:  # noqa: BLE001
                pass

        elif isinstance(block, DocxTable):
            rows = _table_rows(block)
            if not rows:
                continue
            width = max(len(r) for r in rows)
            data = [r + [""] * (width - len(r)) for r in rows]
            # Escape for Paragraph cells
            rl_data = [[_safe_para(c or " ", body) for c in row] for row in data]
            tbl = RLTable(rl_data, hAlign="LEFT")
            tbl.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.92, 0.94, 0.98)),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(tbl)
            story.append(Spacer(1, 10))

    # Append any leftover images not referenced inline
    for r_id, blob in image_parts.items():
        if r_id in used_images:
            continue
        img = _rl_image_from_blob(blob, max_img_w)
        if img is not None:
            story.append(Spacer(1, 6))
            story.append(img)
            used_images.add(r_id)

    if not story:
        story.append(_safe_para("(Empty document)", body))

    with AtomicWriter(destination) as tmp:
        pdf = SimpleDocTemplate(
            str(tmp),
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )
        pdf.build(story)


def _rl_image_from_blob(blob: bytes, max_width: float) -> Any | None:
    from reportlab.platypus import Image as RLImage

    try:
        from PIL import Image as PILImage

        pil = PILImage.open(io.BytesIO(blob))
        pil.load()
        # Normalize to RGB/PNG buffer for ReportLab
        if pil.mode not in ("RGB", "L"):
            pil = pil.convert("RGB")
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        buf.seek(0)
        img = RLImage(buf)
        w, h = float(img.imageWidth), float(img.imageHeight)
        if w <= 0 or h <= 0:
            return None
        if w > max_width:
            scale = max_width / w
            img.drawWidth = max_width
            img.drawHeight = h * scale
        else:
            img.drawWidth = w
            img.drawHeight = h
        return img
    except Exception:  # noqa: BLE001
        return None
