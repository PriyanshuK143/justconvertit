"""Optional FFmpeg-based audio/video conversions."""

from __future__ import annotations

import logging
import subprocess
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
from omniconvert.core.errors import ConversionFailedError, DependencyMissingError
from omniconvert.core.formats import FormatId
from omniconvert.core.job import ConversionResult
from omniconvert.core.limits import SUBPROCESS_TIMEOUT_SECONDS
from omniconvert.core.output import AtomicWriter, verify_output
from omniconvert.platform.subprocess_util import run_capture
from omniconvert.services.dependencies import get_dependency_service

log = logging.getLogger("omniconvert.ffmpeg")


def find_ffmpeg() -> str | None:
    return get_dependency_service().ffmpeg_binary()


class FFmpegConverter(Converter):
    def is_available(self) -> bool:
        return get_dependency_service().ffmpeg.available

    def availability_message(self) -> str:
        return get_dependency_service().ffmpeg.hint

    def operations(self) -> list[ConversionOperation]:
        quality = (
            SettingSpec(
                key="audio_bitrate",
                label="Audio bitrate",
                kind="choice",
                default="192k",
                choices=("128k", "192k", "256k", "320k"),
            ),
        )
        return [
            ConversionOperation(
                operation_id="media.wav_to_mp3",
                label="WAV → MP3",
                source_formats=frozenset({FormatId.WAV}),
                target_format=FormatId.MP3,
                requires_external=("ffmpeg",),
                settings=quality,
                tested=True,
            ),
            ConversionOperation(
                operation_id="media.mp3_to_wav",
                label="MP3 → WAV",
                source_formats=frozenset({FormatId.MP3}),
                target_format=FormatId.WAV,
                requires_external=("ffmpeg",),
                tested=True,
            ),
            ConversionOperation(
                operation_id="media.extract_audio_mp3",
                label="MP4 → MP3",
                source_formats=frozenset({FormatId.MP4, FormatId.MKV}),
                target_format=FormatId.MP3,
                description="Extract audio track to MP3.",
                requires_external=("ffmpeg",),
                settings=quality,
                wheel_label="Extract MP3",
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
        binary = find_ffmpeg()
        if not binary:
            raise DependencyMissingError(self.availability_message())

        check_cancelled(is_cancelled)
        bitrate = str(settings.get("audio_bitrate", "192k"))
        if bitrate not in {"128k", "192k", "256k", "320k"}:
            bitrate = "192k"

        if progress:
            progress(None, "Running FFmpeg…")

        with AtomicWriter(destination) as tmp:
            if operation_id == "media.wav_to_mp3":
                cmd = [
                    binary,
                    "-y",
                    "-i",
                    str(source),
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    bitrate,
                    str(tmp),
                ]
            elif operation_id == "media.mp3_to_wav":
                cmd = [binary, "-y", "-i", str(source), str(tmp)]
            elif operation_id == "media.extract_audio_mp3":
                cmd = [
                    binary,
                    "-y",
                    "-i",
                    str(source),
                    "-vn",
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    bitrate,
                    str(tmp),
                ]
            else:
                raise ConversionFailedError("Unknown media operation.")

            try:
                proc = run_capture(cmd, timeout=SUBPROCESS_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as exc:
                raise ConversionFailedError("FFmpeg timed out.") from exc
            except OSError as exc:
                raise ConversionFailedError(
                    "Could not start FFmpeg.",
                    detail=str(exc),
                ) from exc

            check_cancelled(is_cancelled)
            if proc.returncode != 0:
                log.warning("FFmpeg failed: %s", (proc.stderr or "")[:500])
                raise ConversionFailedError("FFmpeg could not convert the media file.")

        size = verify_output(destination)
        if progress:
            progress(1.0, "Done")
        return ConversionResult(destination, size, "Media conversion completed.")
