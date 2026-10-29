"""Format identifiers and metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FormatId(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    BMP = "bmp"
    TIFF = "tiff"
    TXT = "txt"
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    XLSX = "xlsx"
    DOCX = "docx"
    PPTX = "pptx"
    MP3 = "mp3"
    WAV = "wav"
    MP4 = "mp4"
    MKV = "mkv"
    ZIP = "zip"
    UNKNOWN = "unknown"

    @property
    def extension(self) -> str:
        if self is FormatId.JPEG:
            return ".jpg"
        return f".{self.value}"

    @property
    def label(self) -> str:
        labels = {
            FormatId.JPEG: "JPEG",
            FormatId.PNG: "PNG",
            FormatId.WEBP: "WEBP",
            FormatId.BMP: "BMP",
            FormatId.TIFF: "TIFF",
            FormatId.TXT: "TXT",
            FormatId.JSON: "JSON",
            FormatId.CSV: "CSV",
            FormatId.PDF: "PDF",
            FormatId.XLSX: "XLSX",
            FormatId.DOCX: "DOCX",
            FormatId.PPTX: "PPTX",
            FormatId.MP3: "MP3",
            FormatId.WAV: "WAV",
            FormatId.MP4: "MP4",
            FormatId.MKV: "MKV",
            FormatId.ZIP: "ZIP",
            FormatId.UNKNOWN: "Unknown",
        }
        return labels.get(self, self.value.upper())


IMAGE_FORMATS = frozenset(
    {FormatId.PNG, FormatId.JPEG, FormatId.WEBP, FormatId.BMP, FormatId.TIFF}
)
TEXT_FORMATS = frozenset({FormatId.TXT, FormatId.JSON, FormatId.CSV})


@dataclass(frozen=True, slots=True)
class DetectedFile:
    path: str
    format_id: FormatId
    mime: str
    size_bytes: int
    display_name: str
