"""Optional FFmpeg-based audio/video conversions."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import zipfile
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
from omniconvert.core.crop import crop_setting_specs, parse_crop_percents
from omniconvert.core.errors import ConversionFailedError, DependencyMissingError, ValidationError
from omniconvert.core.formats import FRAME_IMAGE_EXTENSIONS, FormatId
from omniconvert.core.job import ConversionResult
from omniconvert.core.limits import (
    ALLOWED_GIF_SECONDS,
    ALLOWED_MEDIA_FPS,
    DEFAULT_MEDIA_FPS,
    MAX_GIF_SECONDS,
    MAX_VIDEO_FRAMES,
    SUBPROCESS_TIMEOUT_SECONDS,
)
from omniconvert.core.output import AtomicWriter, verify_output
from omniconvert.core.safe_zip import open_zip_safely
from omniconvert.platform.subprocess_util import run_capture
from omniconvert.services.dependencies import get_dependency_service

log = logging.getLogger("omniconvert.ffmpeg")


def find_ffmpeg() -> str | None:
    return get_dependency_service().ffmpeg_binary()


def _parse_fps(settings: dict[str, Any]) -> int:
    raw = settings.get("fps", DEFAULT_MEDIA_FPS)
    try:
        fps = int(str(raw))
    except (TypeError, ValueError) as exc:
        raise ValidationError("FPS must be a whole number.") from exc
    if fps not in ALLOWED_MEDIA_FPS:
        allowed = ", ".join(str(x) for x in sorted(ALLOWED_MEDIA_FPS))
        raise ValidationError(f"FPS must be one of: {allowed}.")
    return fps


def _parse_gif_seconds(settings: dict[str, Any]) -> int:
    raw = settings.get("max_seconds", 3)
    try:
        seconds = int(str(raw))
    except (TypeError, ValueError) as exc:
        raise ValidationError("GIF duration must be a whole number of seconds.") from exc
    if seconds not in ALLOWED_GIF_SECONDS:
        allowed = ", ".join(str(x) for x in sorted(ALLOWED_GIF_SECONDS))
        raise ValidationError(f"GIF duration must be one of: {allowed} seconds.")
    return min(seconds, MAX_GIF_SECONDS)


def _run_ffmpeg(binary: str, cmd: list[str], is_cancelled: CancelCheck | None) -> None:
    check_cancelled(is_cancelled)
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
        fps_setting = (
            SettingSpec(
                key="fps",
                label="Frames per second",
                kind="choice",
                default=str(DEFAULT_MEDIA_FPS),
                choices=tuple(str(x) for x in sorted(ALLOWED_MEDIA_FPS)),
            ),
        )
        gif_settings = fps_setting + (
            SettingSpec(
                key="max_seconds",
                label="Max seconds",
                kind="choice",
                default="3",
                choices=tuple(str(x) for x in sorted(ALLOWED_GIF_SECONDS)),
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
            ConversionOperation(
                operation_id="media.gif_to_mp4",
                label="GIF → MP4",
                source_formats=frozenset({FormatId.GIF}),
                target_format=FormatId.MP4,
                description="Encode an animated GIF as MP4 (H.264).",
                requires_external=("ffmpeg",),
                tested=True,
            ),
            ConversionOperation(
                operation_id="media.video_to_gif",
                label="Video → GIF",
                source_formats=frozenset({FormatId.MP4, FormatId.MKV}),
                target_format=FormatId.GIF,
                description=(
                    f"Encode a short GIF clip (max {MAX_GIF_SECONDS}s, capped resolution)."
                ),
                requires_external=("ffmpeg",),
                settings=gif_settings,
                wheel_label="GIF",
                tested=True,
            ),
            ConversionOperation(
                operation_id="media.video_to_frames_zip",
                label="Video → frames ZIP",
                source_formats=frozenset({FormatId.MP4, FormatId.MKV, FormatId.GIF}),
                target_format=FormatId.ZIP,
                description=(
                    f"Extract PNG frames into a ZIP (max {MAX_VIDEO_FRAMES} frames)."
                ),
                requires_external=("ffmpeg",),
                settings=fps_setting,
                wheel_label="Frames ZIP",
                supports_batch=False,
                tested=True,
            ),
            ConversionOperation(
                operation_id="media.frames_zip_to_mp4",
                label="Frames ZIP → MP4",
                source_formats=frozenset({FormatId.ZIP}),
                target_format=FormatId.MP4,
                description="Build an MP4 from a ZIP of PNG/JPEG frames.",
                requires_external=("ffmpeg",),
                settings=fps_setting,
                wheel_label="MP4",
                supports_batch=False,
                tested=True,
            ),
            ConversionOperation(
                operation_id="media.video_crop",
                label="Crop video",
                source_formats=frozenset({FormatId.MP4, FormatId.MKV}),
                target_format=FormatId.MP4,
                description="Crop margins as a percent of frame size (max 40% per side).",
                requires_external=("ffmpeg",),
                settings=crop_setting_specs(),
                wheel_label="Crop",
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
        if progress:
            progress(None, "Running FFmpeg…")

        if operation_id == "media.wav_to_mp3":
            bitrate = str(settings.get("audio_bitrate", "192k"))
            if bitrate not in {"128k", "192k", "256k", "320k"}:
                bitrate = "192k"
            with AtomicWriter(destination) as tmp:
                _run_ffmpeg(
                    binary,
                    [
                        binary,
                        "-y",
                        "-i",
                        str(source),
                        "-codec:a",
                        "libmp3lame",
                        "-b:a",
                        bitrate,
                        str(tmp),
                    ],
                    is_cancelled,
                )
            msg = "Media conversion completed."
        elif operation_id == "media.mp3_to_wav":
            with AtomicWriter(destination) as tmp:
                _run_ffmpeg(
                    binary,
                    [binary, "-y", "-i", str(source), str(tmp)],
                    is_cancelled,
                )
            msg = "Media conversion completed."
        elif operation_id == "media.extract_audio_mp3":
            bitrate = str(settings.get("audio_bitrate", "192k"))
            if bitrate not in {"128k", "192k", "256k", "320k"}:
                bitrate = "192k"
            with AtomicWriter(destination) as tmp:
                _run_ffmpeg(
                    binary,
                    [
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
                    ],
                    is_cancelled,
                )
            msg = "Media conversion completed."
        elif operation_id == "media.gif_to_mp4":
            with AtomicWriter(destination) as tmp:
                _run_ffmpeg(
                    binary,
                    [
                        binary,
                        "-y",
                        "-i",
                        str(source),
                        "-movflags",
                        "+faststart",
                        "-pix_fmt",
                        "yuv420p",
                        "-vf",
                        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        str(tmp),
                    ],
                    is_cancelled,
                )
            msg = "GIF encoded to MP4."
        elif operation_id == "media.video_to_gif":
            fps = _parse_fps(settings)
            seconds = _parse_gif_seconds(settings)
            with AtomicWriter(destination) as tmp:
                _run_ffmpeg(
                    binary,
                    [
                        binary,
                        "-y",
                        "-i",
                        str(source),
                        "-t",
                        str(seconds),
                        "-vf",
                        f"fps={fps},scale=480:-1:flags=lanczos",
                        "-loop",
                        "0",
                        str(tmp),
                    ],
                    is_cancelled,
                )
            msg = f"Video clipped to GIF ({seconds}s @ {fps} fps)."
        elif operation_id == "media.video_to_frames_zip":
            msg = self._video_to_frames_zip(
                binary, source, destination, settings, progress, is_cancelled
            )
        elif operation_id == "media.frames_zip_to_mp4":
            msg = self._frames_zip_to_mp4(
                binary, source, destination, settings, progress, is_cancelled
            )
        elif operation_id == "media.video_crop":
            left, right, top, bottom = parse_crop_percents(settings)
            # Even dimensions help H.264; express crop in ffmpeg expressions.
            crop_filter = (
                f"crop="
                f"floor(iw*(1-{left}/100-{right}/100)/2)*2:"
                f"floor(ih*(1-{top}/100-{bottom}/100)/2)*2:"
                f"floor(iw*{left}/100/2)*2:"
                f"floor(ih*{top}/100/2)*2"
            )
            with AtomicWriter(destination) as tmp:
                _run_ffmpeg(
                    binary,
                    [
                        binary,
                        "-y",
                        "-i",
                        str(source),
                        "-vf",
                        crop_filter,
                        "-map",
                        "0:v:0",
                        "-an",
                        "-movflags",
                        "+faststart",
                        "-pix_fmt",
                        "yuv420p",
                        str(tmp),
                    ],
                    is_cancelled,
                )
            msg = "Cropped video (video track; audio omitted)."
        else:
            raise ConversionFailedError("Unknown media operation.")

        size = verify_output(destination)
        if progress:
            progress(1.0, "Done")
        return ConversionResult(destination, size, msg)

    def _video_to_frames_zip(
        self,
        binary: str,
        source: Path,
        destination: Path,
        settings: dict[str, Any],
        progress: ProgressCallback | None,
        is_cancelled: CancelCheck | None,
    ) -> str:
        fps = _parse_fps(settings)
        work = Path(tempfile.mkdtemp(prefix="justconvertit-frames-"))
        try:
            pattern = work / "frame_%04d.png"
            if progress:
                progress(0.2, "Extracting frames…")
            _run_ffmpeg(
                binary,
                [
                    binary,
                    "-y",
                    "-i",
                    str(source),
                    "-vf",
                    f"fps={fps}",
                    str(pattern),
                ],
                is_cancelled,
            )
            frames = sorted(work.glob("frame_*.png"))
            if not frames:
                raise ConversionFailedError("No frames were extracted from the video.")
            if len(frames) > MAX_VIDEO_FRAMES:
                raise ValidationError(
                    f"Too many frames ({len(frames)}). "
                    f"Lower FPS or use a shorter clip (max {MAX_VIDEO_FRAMES}).",
                )
            if progress:
                progress(0.7, f"Packing {len(frames)} frames…")
            with AtomicWriter(destination) as tmp:
                with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for frame in frames:
                        check_cancelled(is_cancelled)
                        zf.write(frame, arcname=frame.name)
            return f"Packed {len(frames)} PNG frames into a ZIP."
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _frames_zip_to_mp4(
        self,
        binary: str,
        source: Path,
        destination: Path,
        settings: dict[str, Any],
        progress: ProgressCallback | None,
        is_cancelled: CancelCheck | None,
    ) -> str:
        fps = _parse_fps(settings)
        work = Path(tempfile.mkdtemp(prefix="justconvertit-seq-"))
        try:
            if progress:
                progress(0.2, "Reading frame ZIP…")
            with open_zip_safely(source) as zf:
                members = [
                    info
                    for info in zf.infolist()
                    if not info.is_dir()
                ]
                if not members:
                    raise ValidationError("Frame ZIP is empty.")
                if len(members) > MAX_VIDEO_FRAMES:
                    raise ValidationError(
                        f"Frame ZIP has too many images (max {MAX_VIDEO_FRAMES}).",
                    )
                extracted: list[Path] = []
                for info in members:
                    check_cancelled(is_cancelled)
                    name = info.filename.replace("\\", "/")
                    suffix = Path(name).suffix.lower()
                    if suffix not in FRAME_IMAGE_EXTENSIONS:
                        raise ValidationError(
                            "Frame ZIP may only contain image files "
                            "(PNG/JPEG/WEBP/BMP).",
                        )
                    # Flatten to a safe sequential name later; extract with basename only.
                    dest = work / Path(name).name
                    if dest.exists():
                        raise ValidationError(
                            "Frame ZIP has duplicate file names after flattening.",
                        )
                    with zf.open(info) as src_fh, dest.open("wb") as out_fh:
                        shutil.copyfileobj(src_fh, out_fh)
                    extracted.append(dest)

            extracted.sort(key=lambda p: p.name.lower())
            # Normalize to frame_0001.png … so ffmpeg pattern input works.
            seq_dir = work / "seq"
            seq_dir.mkdir()
            from PIL import Image

            for i, src_img in enumerate(extracted, start=1):
                check_cancelled(is_cancelled)
                png_path = seq_dir / f"frame_{i:04d}.png"
                if src_img.suffix.lower() == ".png":
                    shutil.copy2(src_img, png_path)
                else:
                    with Image.open(src_img) as img:
                        img.convert("RGB").save(png_path, format="PNG")

            pattern = seq_dir / "frame_%04d.png"
            if not list(seq_dir.glob("frame_*.png")):
                raise ConversionFailedError("No usable frames found in the ZIP.")

            if progress:
                progress(0.6, "Encoding MP4…")
            with AtomicWriter(destination) as tmp:
                _run_ffmpeg(
                    binary,
                    [
                        binary,
                        "-y",
                        "-framerate",
                        str(fps),
                        "-i",
                        str(pattern),
                        "-pix_fmt",
                        "yuv420p",
                        "-vf",
                        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        str(tmp),
                    ],
                    is_cancelled,
                )
            return f"Built MP4 from {len(extracted)} frames."
        finally:
            shutil.rmtree(work, ignore_errors=True)
