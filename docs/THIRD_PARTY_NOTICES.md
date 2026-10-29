# Third-party notices

justconvertit depends on third-party libraries. Review their licenses before redistribution.
Exact versions for each public release are listed in `requirements-release.txt`.

| Component | Typical license | Bundled in installer? | Notes |
|-----------|-----------------|----------------------|-------|
| Python runtime (via PyInstaller) | PSF | Yes | Embedded in standalone builds |
| PySide6 / Qt | LGPL / commercial | Yes | Comply with LGPL when shipping |
| Pillow | HPND | Yes | |
| pypdf | BSD-3-Clause | Yes | |
| ReportLab | BSD | Yes | |
| pandas | BSD-3-Clause | Yes | |
| openpyxl | MIT | Yes | |
| pypdfium2 / PDFium | Apache-2.0 / BSD | Yes | Keep notices in releases |
| python-docx | MIT | Yes | |
| python-pptx | MIT | Yes | |
| LibreOffice | MPL/LGPL | **No** | Optional local install |
| FFmpeg | LGPL/GPL depending on build | **No** | Optional local install; license-review before any future bundling |

This file is informational and not legal advice.
