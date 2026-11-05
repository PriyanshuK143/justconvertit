"""Image conversions via Pillow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from omniconvert.core.converter import (
    CancelCheck,
    ConversionOperation,
    Converter,
    ProgressCallback,
    SettingSpec,
    check_cancelled,
)
from omniconvert.core.crop import crop_box_pixels, crop_setting_specs, parse_crop_percents
from omniconvert.core.errors import ConversionFailedError, ResourceLimitError, ValidationError
from omniconvert.core.formats import IMAGE_FORMATS, FormatId
from omniconvert.core.job import ConversionResult
from omniconvert.core.limits import MAX_IMAGE_PIXELS
from omniconvert.core.output import AtomicWriter, verify_output

_CROP_ID = "image.crop"

# Wheel / conversion targets — no BMP, TIFF, resize, or background-remove.
_IMAGE_TARGETS = (FormatId.PNG, FormatId.JPEG, FormatId.WEBP)

# Pillow can be DoS'd by decompression bombs — enforce a limit.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

_PIL_FORMAT = {
    FormatId.PNG: "PNG",
    FormatId.JPEG: "JPEG",
    FormatId.WEBP: "WEBP",
    FormatId.BMP: "BMP",
    FormatId.TIFF: "TIFF",
}


def _parse_color(value: str) -> tuple[int, int, int]:
    v = (value or "#FFFFFF").strip()
    if v.startswith("#") and len(v) == 7:
        return int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16)
    return 255, 255, 255


def _prepare_for_save(img: Image.Image, target: FormatId, bg: tuple[int, int, int]) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if target is FormatId.JPEG:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, bg)
            background.paste(rgba, mask=rgba.split()[-1])
            return background
        if img.mode != "RGB":
            return img.convert("RGB")
        return img
    if target is FormatId.PNG and img.mode == "CMYK":
        return img.convert("RGB")
    return img


class ImagePillowConverter(Converter):
    def operations(self) -> list[ConversionOperation]:
        ops: list[ConversionOperation] = []
        jpeg_settings = (
            SettingSpec(
                key="jpeg_quality",
                label="JPEG quality",
                kind="int",
                default=90,
                minimum=1,
                maximum=95,
                help_text="Higher is better quality and larger files.",
            ),
            SettingSpec(
                key="transparency_background",
                label="Transparency background",
                kind="color",
                default="#FFFFFF",
                help_text="Background used when flattening transparency for JPEG.",
            ),
        )
        # Open any common image (incl. BMP/TIFF); only offer PNG/JPEG/WEBP outs.
        for src in IMAGE_FORMATS:
            for dst in _IMAGE_TARGETS:
                if src == dst:
                    continue
                settings = jpeg_settings if dst is FormatId.JPEG else ()
                ops.append(
                    ConversionOperation(
                        operation_id=f"image.{src.value}_to_{dst.value}",
                        label=f"{src.label} → {dst.label}",
                        source_formats=frozenset({src}),
                        target_format=dst,
                        description=f"Convert {src.label} image to {dst.label}.",
                        settings=settings,
                        supports_batch=True,
                        tested=True,
                    )
                )

        ops.append(
            ConversionOperation(
                operation_id=_CROP_ID,
                label="Crop image → PNG",
                source_formats=IMAGE_FORMATS,
                target_format=FormatId.PNG,
                description=(
                    "Crop margins as a percent of width/height (max 40% per side)."
                ),
                settings=crop_setting_specs(),
                wheel_label="Crop",
                supports_batch=True,
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
        check_cancelled(is_cancelled)
        if progress:
            progress(0.1, "Opening image…")

        try:
            with Image.open(source) as img:
                img.load()
                check_cancelled(is_cancelled)

                if operation_id == _CROP_ID:
                    if progress:
                        progress(0.35, "Cropping…")
                    percents = parse_crop_percents(settings)
                    box = crop_box_pixels(img.width, img.height, percents)
                    cropped = ImageOps.exif_transpose(img).crop(box)
                    check_cancelled(is_cancelled)
                    with AtomicWriter(destination) as tmp:
                        cropped.save(tmp, format="PNG", optimize=True)
                    size = verify_output(destination)
                    if progress:
                        progress(1.0, "Done")
                    return ConversionResult(
                        output_path=destination,
                        bytes_written=size,
                        message=f"Cropped to {cropped.width}×{cropped.height} PNG.",
                    )

                target_token = operation_id.rsplit("_to_", 1)[-1]
                try:
                    target = FormatId(target_token)
                except ValueError as exc:
                    raise ValidationError(f"Unknown image conversion: {operation_id}") from exc
                if target not in _IMAGE_TARGETS:
                    raise ValidationError(f"Unsupported image target: {target.label}")

                quality = int(settings.get("jpeg_quality", 90))
                quality = max(1, min(95, quality))
                bg = _parse_color(str(settings.get("transparency_background", "#FFFFFF")))

                if progress:
                    progress(0.4, "Converting…")
                prepared = _prepare_for_save(img, target, bg)
                check_cancelled(is_cancelled)

                save_kwargs: dict[str, Any] = {}
                if target is FormatId.JPEG:
                    save_kwargs.update(quality=quality, optimize=True)
                elif target is FormatId.WEBP:
                    save_kwargs.update(quality=quality)

                with AtomicWriter(destination) as tmp:
                    prepared.save(tmp, format=_PIL_FORMAT[target], **save_kwargs)

                if progress:
                    progress(0.9, "Verifying output…")
                size = verify_output(destination)
                if progress:
                    progress(1.0, "Done")
                return ConversionResult(
                    output_path=destination,
                    bytes_written=size,
                    message=f"Saved {target.label} image.",
                )
        except Image.DecompressionBombError as exc:
            raise ResourceLimitError(
                "Image is too large to process safely.",
                detail=str(exc),
            ) from exc
        except UnidentifiedImageError as exc:
            raise ValidationError("File is not a readable image.", detail=str(exc)) from exc
        except OSError as exc:
            raise ConversionFailedError(
                "Could not convert the image.",
                detail=str(exc),
            ) from exc
