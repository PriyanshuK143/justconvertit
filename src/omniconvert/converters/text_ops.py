"""Text and JSON utility conversions."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
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
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValidationError("Could not decode text file with a supported encoding.")
    # Normalize newlines so Windows CRLF inputs don't become \r\r\n on rewrite.
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _write_text(path: Path, text: str) -> None:
    """Write UTF-8 text with LF newlines (binary) — safe on Windows and Linux."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(normalized.encode("utf-8"))


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        raw = " ".join(self._chunks)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip() + ("\n" if raw.strip() else "")


class _HTMLMarkdownExtractor(HTMLParser):
    """Best-effort HTML → Markdown (headings, lists, links, emphasis)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._link_href: list[str | None] = []
        self._link_text: list[list[str]] = []
        self._emphasis: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        attr = {k: (v or "") for k, v in attrs}
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            self._parts.append(f"\n\n{'#' * level} ")
        elif tag in {"p", "div"}:
            self._parts.append("\n\n")
        elif tag == "br":
            self._parts.append("\n")
        elif tag == "li":
            self._parts.append("\n- ")
        elif tag in {"ul", "ol"}:
            self._parts.append("\n")
        elif tag == "a":
            self._link_href.append(attr.get("href") or "")
            self._link_text.append([])
        elif tag in {"strong", "b"}:
            self._emphasis.append("**")
            self._parts.append("**")
        elif tag in {"em", "i"}:
            self._emphasis.append("*")
            self._parts.append("*")
        elif tag == "code":
            self._emphasis.append("`")
            self._parts.append("`")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "li"}:
            self._parts.append("\n")
        elif tag == "a" and self._link_href:
            href = self._link_href.pop()
            text_bits = self._link_text.pop()
            label = " ".join(text_bits).strip() or href
            if href:
                self._parts.append(f"[{label}]({href})")
            else:
                self._parts.append(label)
        elif tag in {"strong", "b", "em", "i", "code"} and self._emphasis:
            self._parts.append(self._emphasis.pop())

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data)
        if not text.strip() and text != " ":
            return
        if self._link_text:
            self._link_text[-1].append(text.strip() if text.strip() else text)
            return
        if text:
            self._parts.append(text)

    def markdown(self) -> str:
        raw = "".join(self._parts)
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip() + ("\n" if raw.strip() else "")


def html_to_plain(html: str) -> str:
    parser = _HTMLTextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # noqa: BLE001 — html.parser can raise varied errors
        raise ValidationError("Could not parse HTML.", detail=str(exc)) from exc
    return parser.text()


def html_to_markdown(html: str) -> str:
    parser = _HTMLMarkdownExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # noqa: BLE001 — html.parser can raise varied errors
        raise ValidationError("Could not parse HTML.", detail=str(exc)) from exc
    return parser.markdown()


def _text_to_docx(text: str, destination: Path) -> None:
    from docx import Document

    doc = Document()
    for para in text.splitlines() or [""]:
        doc.add_paragraph(para)
    with AtomicWriter(destination) as tmp:
        doc.save(str(tmp))


def markdown_to_plain(text: str) -> str:
    """Best-effort Markdown → plain text (not a full CommonMark parser)."""
    # Fenced code blocks → inner text
    text = re.sub(
        r"```[^\n]*\n(.*?)```",
        lambda m: m.group(1).rstrip() + "\n",
        text,
        flags=re.DOTALL,
    )
    # Images / links keep visible label only
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Bold / italic markers
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    # Headings / blockquotes / list markers
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*[-*+]|\s*\d+\.)\s+", "", text, flags=re.MULTILINE)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


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
            ConversionOperation(
                operation_id="text.md_to_txt",
                label="MD → TXT",
                source_formats=frozenset({FormatId.MD}),
                target_format=FormatId.TXT,
                description="Strip common Markdown markup into plain text.",
                wheel_label="TXT",
                tested=True,
            ),
            ConversionOperation(
                operation_id="text.txt_to_md",
                label="TXT → MD",
                source_formats=frozenset({FormatId.TXT}),
                target_format=FormatId.MD,
                description="Save plain text as a Markdown (.md) file.",
                wheel_label="MD",
                tested=True,
            ),
            ConversionOperation(
                operation_id="text.html_to_txt",
                label="HTML → TXT",
                source_formats=frozenset({FormatId.HTML}),
                target_format=FormatId.TXT,
                description="Extract visible text from HTML (scripts/styles removed).",
                wheel_label="TXT",
                tested=True,
            ),
            ConversionOperation(
                operation_id="text.html_to_md",
                label="HTML → MD",
                source_formats=frozenset({FormatId.HTML}),
                target_format=FormatId.MD,
                description=(
                    "Convert HTML to Markdown (headings, lists, links, emphasis). "
                    "Scripts and styles are dropped."
                ),
                wheel_label="MD",
                tested=True,
            ),
            ConversionOperation(
                operation_id="text.html_to_pdf",
                label="HTML → PDF",
                source_formats=frozenset({FormatId.HTML}),
                target_format=FormatId.PDF,
                description="Extract text from HTML into a simple portable PDF.",
                wheel_label="PDF",
                tested=True,
            ),
            ConversionOperation(
                operation_id="text.html_to_docx",
                label="HTML → DOCX",
                source_formats=frozenset({FormatId.HTML}),
                target_format=FormatId.DOCX,
                description="Extract text from HTML into a simple Word document.",
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
                    _write_text(
                        Path(tmp),
                        json.dumps(data, indent=indent, ensure_ascii=False) + "\n",
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
            elif operation_id == "text.md_to_txt":
                text = markdown_to_plain(_read_text(source))
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    _write_text(Path(tmp), text)
                msg = "Markdown converted to plain text."
            elif operation_id == "text.txt_to_md":
                text = _read_text(source)
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    _write_text(Path(tmp), text)
                msg = "Plain text saved as Markdown."
            elif operation_id == "text.html_to_txt":
                text = html_to_plain(_read_text(source))
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    _write_text(Path(tmp), text)
                msg = "Extracted text from HTML."
            elif operation_id == "text.html_to_md":
                text = html_to_markdown(_read_text(source))
                check_cancelled(is_cancelled)
                with AtomicWriter(destination) as tmp:
                    _write_text(Path(tmp), text)
                msg = "HTML converted to Markdown."
            elif operation_id == "text.html_to_pdf":
                text = html_to_plain(_read_text(source))
                check_cancelled(is_cancelled)
                if progress:
                    progress(0.5, "Writing PDF…")
                _text_to_pdf(text, destination)
                msg = "PDF created from HTML text."
            elif operation_id == "text.html_to_docx":
                text = html_to_plain(_read_text(source))
                check_cancelled(is_cancelled)
                if progress:
                    progress(0.5, "Writing DOCX…")
                _text_to_docx(text, destination)
                msg = "DOCX created from HTML text."
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
