"""Resource limits for safe local processing."""

from __future__ import annotations

# Soft defaults; settings may override later.
MAX_INPUT_BYTES = 500 * 1024 * 1024  # 500 MiB
MAX_IMAGE_PIXELS = 80_000_000  # ~80 MP
MAX_TEXT_BYTES = 50 * 1024 * 1024
MAX_PDF_PAGES = 500  # Hard cap for render/extract loops
MAX_PDF_RENDER_PAGES = 100  # Pages → ZIP (memory-heavy)
MAX_PDF_RENDER_SCALE = 2.0
MAX_PDF_RENDER_TOTAL_PIXELS = 200_000_000  # Across all rendered pages
MAX_ZIP_MEMBERS = 5_000
MAX_ZIP_UNCOMPRESSED_BYTES = 512 * 1024 * 1024  # Declared uncompressed total
MAX_ZIP_COMPRESSION_RATIO = 100.0  # Declared uncompressed / compressed per member
SUBPROCESS_TIMEOUT_SECONDS = 600

# Media (FFmpeg) — keep frame dumps and GIF encodes bounded.
MAX_VIDEO_FRAMES = 300
ALLOWED_MEDIA_FPS = frozenset({1, 2, 5, 10, 12, 15, 24})
DEFAULT_MEDIA_FPS = 5
MAX_GIF_SECONDS = 10
ALLOWED_GIF_SECONDS = frozenset({1, 2, 3, 5, 8, 10})
MAX_CROP_PERCENT = 40  # per side; left+right and top+bottom must stay < 100
