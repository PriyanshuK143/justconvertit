"""Register all built-in conversion handlers."""

from __future__ import annotations

from omniconvert.core.registry import ConversionRegistry


def register_all(registry: ConversionRegistry) -> None:
    from omniconvert.converters.image_pillow import ImagePillowConverter
    from omniconvert.converters.media_ffmpeg import FFmpegConverter
    from omniconvert.converters.office_libreoffice import LibreOfficeConverter
    from omniconvert.converters.office_pure import OfficePureConverter
    from omniconvert.converters.pdf_ops import PdfOpsConverter
    from omniconvert.converters.tabular import TabularConverter
    from omniconvert.converters.text_ops import TextOpsConverter

    # Pure / pip-bundled first (works on any device after install).
    registry.register(ImagePillowConverter())
    registry.register(TabularConverter())
    registry.register(TextOpsConverter())
    registry.register(PdfOpsConverter())
    registry.register(OfficePureConverter())
    # Optional system engines — only appear when installed.
    registry.register(LibreOfficeConverter())
    registry.register(FFmpegConverter())
