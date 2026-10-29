# Supported platforms

justconvertit does **not** promise indefinite compatibility with every future OS release. Support is defined per published version.

## Release target: 0.1.x

| Platform | Build form | Status | Notes |
|----------|------------|--------|-------|
| Ubuntu 22.04 / 24.04 (x86_64) | PyInstaller one-folder (`justconvertit`) | Primary Linux target | Needs basic X11/Wayland Qt deps (e.g. `libxcb-cursor0`) |
| Windows 10 / 11 (x64) | PyInstaller + Inno Setup | **Primary** product target | See `docs/WINDOWS.md`. Build/test on Windows or `windows-latest` CI — not claimed verified from Linux hosts |
| Other Linux distros | Same folder tree | Best-effort | Test before claiming support |
| macOS | — | Not a 0.1 target | |

## Runtime requirements (end user)

| Need | Core app | Optional engines |
|------|----------|------------------|
| Python / pip / developer tools | **Not required** (bundled in installer) | — |
| Internet after install | **Not required** for conversions | Only for optional first-run apt/winget install |
| LibreOffice | — | First-run prompt or `apt` / `winget` — Office↔PDF, PDF→DOCX |
| FFmpeg | — | First-run prompt or `apt` / `winget` — WAV/MP3/MP4 audio |
| Display / GUI | Required for the orb UI | — |

## Graceful degradation

| Situation | Behavior |
|-----------|----------|
| LibreOffice missing | LO pads hidden; pure-Python Office→TXT/PDF(text) remain; first-run may offer apt/winget install |
| LibreOffice present | High-fidelity PDF/DOCX pads shown; PDF(text) fallbacks hidden |
| FFmpeg missing | Media pads hidden; no crash; first-run may offer install |
| Future OS breaks Qt plugins | App may fail to start; rebuild against a newer Qt pin |
| Future OS breaks optional binary CLI | That engine’s ops disappear or fail with a clear error |

## Compatibility policy

- Each release documents the OS versions it was tested on.
- Security/dependency updates are delivered as **new installers**, not an in-app updater.
- When an OS major version is no longer tested, it moves to “best-effort / unsupported.”
