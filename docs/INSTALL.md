# Installation & uninstallation

justconvertit is a **standalone** desktop app. End users do **not** need Python, pip, or developer tools.

After install, core conversions work **offline**. See [PRIVACY.md](PRIVACY.md) and [PLATFORMS.md](PLATFORMS.md).

## Ubuntu — install like a normal app

1. Download `justconvertit-<version>-linux-x86_64.tar.gz` from the release page.
2. Verify the SHA-256 checksum published with the release.
3. Extract and install:

```bash
tar -xzf justconvertit-0.1.0-linux-x86_64.tar.gz
cd justconvertit
./install.sh
```

That copies the app to `~/.local/opt/justconvertit`, adds an app-menu entry, and links `~/.local/bin/justconvertit`.

4. Open **justconvertit** from your application menu (or run `justconvertit` in a terminal).

System-wide (optional):

```bash
sudo ./install.sh --system
```

If the app fails to start with a Qt/xcb error:

```bash
sudo apt-get install -y libxcb-cursor0 libegl1 libxkbcommon0
```

### Uninstall (Ubuntu)

```bash
~/.local/opt/justconvertit/uninstall.sh
# system install:
# sudo /opt/justconvertit/uninstall.sh
```

## Windows — Setup.exe

Primary product target. Build notes: [WINDOWS.md](WINDOWS.md).

### Install

1. Download `justconvertit-<version>-Setup.exe` from the release page.
2. Verify the SHA-256 checksum.
3. Run the installer (per-user; no admin required by default).
4. Launch from the Start menu or desktop shortcut.

### Uninstall

- **Settings → Apps → justconvertit → Uninstall**, or  
- Start Menu → justconvertit → Uninstall

The uninstaller removes application files. It does not remove LibreOffice / FFmpeg installed separately.

## Optional local engines (recommended)

On first launch, if LibreOffice or FFmpeg is missing, justconvertit asks once whether
to install them via your **system package manager** (`apt` on Ubuntu, `winget` on
Windows). That step needs internet and admin approval. After that, the app stays
offline.

You can also install manually, or retry from **Settings → Install LibreOffice + FFmpeg…**:

```bash
# Ubuntu
sudo apt-get install -y libreoffice ffmpeg
```

```text
# Windows (winget)
winget install -e --id TheDocumentFoundation.LibreOffice
winget install -e --id Gyan.FFmpeg
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
| `qt.qpa.plugin: Could not load … "xcb"` | Install `libxcb-cursor0` (and related Qt deps) |
| LibreOffice pads missing | First-run Install, or Settings → Install / `apt`/`winget`; restart |
| FFmpeg pads missing | Same as LibreOffice; or put `ffmpeg` on PATH |
| Conversion refused large file | Soft limit ~500 MiB |
| “Need Python?” | No — use the release archive / Setup.exe, not the source tree |
