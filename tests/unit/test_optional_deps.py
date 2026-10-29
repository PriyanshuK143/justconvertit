from __future__ import annotations

from pathlib import Path

import pytest

from omniconvert.converters.media_ffmpeg import FFmpegConverter
from omniconvert.converters.office_libreoffice import LibreOfficeConverter
from omniconvert.core.errors import DependencyMissingError
from omniconvert.core.formats import FormatId


def test_libreoffice_hidden_when_missing(registry) -> None:
    ops = registry.available_operations_for(FormatId.DOCX)
    ids = {o.operation_id for o in ops}
    # Pure-Python extract always available offline.
    assert "office.docx_to_txt" in ids
    lo = LibreOfficeConverter()
    if not lo.is_available():
        assert "office.docx_to_pdf" not in ids
        assert "office.docx_to_pdf_text" in ids
    else:
        # Prefer high-fidelity LibreOffice PDF; hide portable text fallback.
        assert "office.docx_to_pdf" in ids
        assert "office.docx_to_pdf_text" not in ids
        pdf_ops = {o.operation_id for o in registry.available_operations_for(FormatId.PDF)}
        assert "office.pdf_to_docx" in pdf_ops


def test_ffmpeg_convert_raises_when_missing(tmp_path: Path) -> None:
    conv = FFmpegConverter()
    if conv.is_available():
        pytest.skip("FFmpeg installed on this machine")
    src = tmp_path / "a.wav"
    # minimal invalid — availability checked first
    src.write_bytes(b"RIFF....WAVE")
    with pytest.raises(DependencyMissingError):
        conv.convert(
            operation_id="media.wav_to_mp3",
            source=src,
            destination=tmp_path / "o.mp3",
            settings={},
        )
