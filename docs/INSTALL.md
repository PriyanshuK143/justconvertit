# Installation & uninstallation

justconvertit is a **standalone** desktop app. End users do **not** need Python, pip, or developer tools for the core application.

After install, core conversions work **offline**. See [PRIVACY.md](PRIVACY.md) and [PLATFORMS.md](PLATFORMS.md).

## Ubuntu (standalone folder)

### Install

1. Download `justconvertit-<version>-linux-x86_64.tar.gz` from the release page.
2. Verify the SHA-256 checksum published with the release.
3. Extract somewhere permanent, e.g. `/opt/justconvertit` or `~/Applications/justconvertit`.

```bash
tar -xzf justconvertit-0.1.0-linux-x86_64.tar.gz
# optional system-wide:
sudo mkdir -p /opt/justconvertit
sudo cp -a justconvertit/. /opt/justconvertit/
sudo ln -sf /opt/justconvertit/justconvertit /usr/local/bin/justconvertit
```

4. Install Qt/xcb runtime libraries if the app fails to start:

```bash
sudo apt-get install -y libxcb-cursor0 libegl1 libxkbcommon0
```

5. Optional desktop entry: copy `justconvertit.desktop` from the folder, set `Exec=` to the binary path, and place it in `~/.local/share/applications/`.

6. Run `justconvertit` (or the symlink you created).

### Uninstall

```bash
sudo rm -f /usr/local/bin/justconvertit
sudo rm -rf /opt/justconvertit
rm -f ~/.local/share/applications/justconvertit.desktop
# Optional: remove local settings/logs under ~/.config / ~/.local/share if present
```

If you only extracted to a user folder, delete that folder.

## Windows (Inno Setup installer)

Primary product target. Build instructions: [WINDOWS.md](WINDOWS.md).

### Install

1. Download `justconvertit-<version>-Setup.exe` from the release page.
2. Verify the SHA-256 checksum.
3. Run the installer (per-user install; no admin required by default).
4. Launch from the Start menu or desktop shortcut.
5. Optional: Settings → set LibreOffice / FFmpeg paths if not on PATH.

### Uninstall

- **Settings → Apps → justconvertit → Uninstall**, or
- Start Menu → justconvertit → Uninstall

The uninstaller removes application files under the install directory. It does not remove optional system tools (LibreOffice, FFmpeg) you installed separately.

## Optional local engines (recommended)

On first launch, if LibreOffice or FFmpeg is missing, justconvertit asks once whether
to install them via your **system package manager** (`apt` on Ubuntu, `winget` on
Windows). That step needs internet and admin approval. After that, the app stays
offline and only detects local binaries.

You can also install manually, or retry anytime from **Settings → Install LibreOffice + FFmpeg…**:

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
does **not** remove LibreOffice or FFmpeg. When LibreOffice is present, portable
“PDF (text)” fallbacks are hidden so the wheel offers the high-fidelity path by default.

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
| “Need Python?” | No — use the release installer/folder, not the source tree |
