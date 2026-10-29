"""Image conversions via Pillow."""

from __future__ import annotations

from collections import deque
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
from omniconvert.core.errors import ConversionFailedError, ResourceLimitError, ValidationError
from omniconvert.core.formats import IMAGE_FORMATS, FormatId
from omniconvert.core.job import ConversionResult
from omniconvert.core.limits import MAX_IMAGE_PIXELS
from omniconvert.core.output import AtomicWriter, verify_output

# Pillow can be DoS'd by decompression bombs — enforce a limit.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

_REMOVE_BG_ID = "image.remove_background"

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
    if target is FormatId.BMP and img.mode in ("RGBA", "LA", "P"):
        return img.convert("RGB")
    if target is FormatId.PNG and img.mode == "CMYK":
        return img.convert("RGB")
    return img


def _color_close(a: tuple[int, ...], b: tuple[int, int, int], tol: int) -> bool:
    return (
        abs(a[0] - b[0]) <= tol
        and abs(a[1] - b[1]) <= tol
        and abs(a[2] - b[2]) <= tol
    )


def _sample_corner_background(pixels: Any, width: int, height: int) -> tuple[int, int, int]:
    corners = (
        pixels[0, 0][:3],
        pixels[width - 1, 0][:3],
        pixels[0, height - 1][:3],
        pixels[width - 1, height - 1][:3],
    )
    r = sum(c[0] for c in corners) // 4
    g = sum(c[1] for c in corners) // 4
    b = sum(c[2] for c in corners) // 4
    return r, g, b


def remove_background(
    img: Image.Image,
    *,
    tolerance: int = 32,
    background: str = "auto",
) -> Image.Image:
    """Make near-background pixels transparent via edge flood-fill (offline, no AI).

    Best on photos/screenshots with a fairly flat backdrop. Not ML cutout quality.
    """
    rgba = ImageOps.exif_transpose(img).convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    assert pixels is not None

    tol = max(0, min(120, int(tolerance)))
    if (background or "auto").strip().lower() in {"", "auto"}:
        bg = _sample_corner_background(pixels, width, height)
    else:
        bg = _parse_color(background)

    visited = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def enqueue(x: int, y: int) -> None:
        idx = y * width + x
        if visited[idx]:
            return
        pix = pixels[x, y]
        if pix[3] == 0:
            visited[idx] = 1
            return
        if not _color_close(pix, bg, tol):
            return
        visited[idx] = 1
        queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        pixels[x, y] = (0, 0, 0, 0)
        if x > 0:
            enqueue(x - 1, y)
        if x + 1 < width:
            enqueue(x + 1, y)
        if y > 0:
            enqueue(x, y - 1)
        if y + 1 < height:
            enqueue(x, y + 1)

    return rgba


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
        for src in IMAGE_FORMATS:
            for dst in IMAGE_FORMATS:
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

        remove_bg_settings = (
            SettingSpec(
                key="bg_tolerance",
                label="Tolerance",
                kind="int",
                default=32,
                minimum=0,
                maximum=120,
                help_text="How similar to the corner background a pixel can be and still be removed.",
            ),
        )
        # Any common image → transparent PNG (flat/solid backdrops work best).
        ops.append(
            ConversionOperation(
                operation_id=_REMOVE_BG_ID,
                label="Remove background → PNG",
                source_formats=IMAGE_FORMATS,
                target_format=FormatId.PNG,
                description=(
                    "Remove a flat backdrop (sampled from image corners) and save a "
                    "transparent PNG. Offline; not AI cutout."
                ),
                settings=remove_bg_settings,
                wheel_label="No BG",
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

                if operation_id == _REMOVE_BG_ID:
                    if progress:
                        progress(0.35, "Removing background…")
                    tol = int(settings.get("bg_tolerance", 32))
                    cutout = remove_background(img, tolerance=tol, background="auto")
                    check_cancelled(is_cancelled)
                    with AtomicWriter(destination) as tmp:
                        cutout.save(tmp, format="PNG", optimize=True)
                    size = verify_output(destination)
                    if progress:
                        progress(1.0, "Done")
                    return ConversionResult(
                        output_path=destination,
                        bytes_written=size,
                        message="Saved transparent PNG (background removed).",
                    )

                target_token = operation_id.rsplit("_to_", 1)[-1]
                target = FormatId(target_token)
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
