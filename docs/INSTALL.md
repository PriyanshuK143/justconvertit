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
| `qt.qpa.plugin: Could not load … "xcb"` | `sudo apt-get install -y libxcb-cursor0` (usually pulled in by the `.deb`) |
| LibreOffice pads missing | First-run Install, or Settings → Install / `apt`/`winget`; restart |
| FFmpeg pads missing | Same as LibreOffice; or put `ffmpeg` on PATH |
| Conversion refused large file | Soft limit ~500 MiB |
| “Need Python?” | No — use the `.deb` / Setup.exe, not the source tree |
