"""Register all built-in conversion handlers."""

from __future__ import annotations

from omniconvert.core.registry import ConversionRegistry


def register_all(registry: ConversionRegistry) -> None:
    # Portable converters first (keep import surface tight for startup timing).
    from omniconvert.converters.image_pillow import ImagePillowConverter
    from omniconvert.converters.office_pure import OfficePureConverter
    from omniconvert.converters.pdf_ops import PdfOpsConverter
    from omniconvert.converters.tabular import TabularConverter
    from omniconvert.converters.text_ops import TextOpsConverter

    registry.register(ImagePillowConverter())
    registry.register(TabularConverter())
    registry.register(TextOpsConverter())
    registry.register(PdfOpsConverter())
    registry.register(OfficePureConverter())

    # Optional engines — import after portable so cold start prefers core path.
    from omniconvert.converters.media_ffmpeg import FFmpegConverter
    from omniconvert.converters.office_libreoffice import LibreOfficeConverter
    from omniconvert.converters.svg_inkscape import InkscapeConverter

    registry.register(LibreOfficeConverter())
    registry.register(FFmpegConverter())
    registry.register(InkscapeConverter())
