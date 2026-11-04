# Installation & uninstallation

justconvertit is a **standalone** desktop app. End users do **not** need Python, pip, or developer tools.

After install, core conversions work **offline**. See [PRIVACY.md](PRIVACY.md) and [PLATFORMS.md](PLATFORMS.md).

## Ubuntu — `.deb` package

1. Download `justconvertit_<version>_amd64.deb` from the release page.
2. Verify the SHA-256 checksum published with the release.
3. Install either way:
   - Double-click the `.deb` and open it in Ubuntu Software / App Center, or
   - Terminal:

```bash
sudo apt install ./justconvertit_0.1.0_amd64.deb
```

If apt prints a notice like:

```text
N: Download is performed unsandboxed as root as file '…/justconvertit_….deb'
couldn't be accessed by user '_apt'. - pkgAcquire::Run (13: Permission denied)
```

that is **normal for a local `.deb` in `~/Downloads`**. The `N:` line is a notice, not a failure. Your friend’s log already shows `Setting up justconvertit (0.1.0)…` and desktop-menu triggers — the app is installed. To avoid the notice next time, copy the file somewhere world-readable first:

```bash
cp ~/Downloads/justconvertit_0.1.0_amd64.deb /tmp/
sudo apt install /tmp/justconvertit_0.1.0_amd64.deb
```

4. Open **justconvertit** from your application menu.

### Uninstall (Ubuntu)

- **Settings → Apps → justconvertit → Uninstall**, or

```bash
sudo apt remove justconvertit
```

## Windows — Setup.exe

Primary product target. Build notes: [WINDOWS.md](WINDOWS.md).

### Install

1. Download `JustConvertIt-<version>-Setup.exe` from the release page (or a trusted share).
2. Verify the SHA-256 checksum when available.
3. Run the installer (per-user; no admin required by default).
4. Open **JustConvertIt** from the Start menu or desktop shortcut (Setup does not auto-launch).

### If Windows blocks the app

Message like **CreateProcess failed; code 4551** / **Application Control policy has blocked this file**:

| PC type | What to do |
|---------|------------|
| Personal home PC | SmartScreen / Smart App Control: **More info → Run anyway**. Or Windows Security → App & browser control → check Smart App Control. |
| School / work laptop | IT policy (AppLocker / WDAC). Install alone cannot bypass it — ask IT to allow JustConvertIt, or use a personal PC. |

This is a Windows trust policy on **unsigned** apps. A paid code-signing certificate is required to avoid it for everyone.

### Uninstall

- **Settings → Apps → justconvertit → Uninstall**, or
- Start Menu → justconvertit → Uninstall

The uninstaller removes application files. It does not remove LibreOffice / FFmpeg installed separately.

## Optional local engines (recommended)

Most conversions work with **no** extra installs.

| Tool | Needed for | How it installs |
|------|------------|-----------------|
| FFmpeg | Audio/video | Windows: offered when you pick a media conversion, or **Settings → Install FFmpeg…** (winget). Linux: apt / first-run prompt. |
| LibreOffice | High-fidelity Office ↔ PDF | Same pattern — only when needed, or Settings. |

Windows does **not** nag at startup for these. Install happens with your consent via **winget** (needs internet once). After that, the app stays offline.

```bash
# Ubuntu (manual)
sudo apt-get install -y libreoffice ffmpeg
```

```text
# Windows (manual winget)
winget install -e --id Gyan.FFmpeg
winget install -e --id TheDocumentFoundation.LibreOffice
```

| Engine | Enables | How justconvertit finds it |
|--------|---------|---------------------------|
| LibreOffice | DOCX/PPTX/XLSX/TXT → PDF, PDF → DOCX (best layout) | Prefers `/usr/bin/soffice`, then PATH / Snap |
| FFmpeg | WAV↔MP3, extract MP3 from video | Prefers `/usr/bin/ffmpeg`, then PATH |

justconvertit never downloads these tools into its own folder. Uninstalling justconvertit
does **not** remove LibreOffice or FFmpeg.

## Run from source (developers)

See the README. Requires Python 3.11+, a venv, and `pip install -e ".[dev]"`.

## Offline verification (packagers)

```bash
bash scripts/build_linux.sh
bash scripts/verify_offline.sh
```

## Common issues

| Symptom | Fix |
|---------|-----|
| `qt.qpa.plugin: Could not load … "xcb"` | `sudo apt-get install -y libxcb-cursor0` (usually pulled in by the `.deb`) |
| LibreOffice pads missing | First-run Install, or Settings → Install / `apt`/`winget`; restart |
| FFmpeg pads missing | Same as LibreOffice; or put `ffmpeg` on PATH |
| Conversion refused large file | Soft limit ~500 MiB |
| “Need Python?” | No — use the `.deb` / Setup.exe, not the source tree |
