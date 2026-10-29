# Architecture

```
UI (PySide6)
  └─ MainWindow / RadialWheel
       └─ JobManager (QThread)
            └─ ConversionRegistry
                 └─ Converter handlers (Pillow, pandas, pypdf, ReportLab, LibreOffice, FFmpeg)
```

- **Detection** (`core/detection.py`) sniffs content; extensions are hints.
- **Registry** is the single source of truth for wheel segments.
- **Handlers** are Qt-free and unit-testable.
- **Output** uses unique names + atomic replace; never overwrites the source by default.
- **Platform** helpers isolate Windows vs Linux path/reveal/which behavior.
