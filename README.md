# justconvertit

One-time-install, **offline-first** desktop file converter with a circular radial-wheel interface.

Files are processed on your machine. justconvertit does not upload documents, require accounts, phone home for updates, or send telemetry.

See [docs/PRODUCT.md](docs/PRODUCT.md), [docs/PRIVACY.md](docs/PRIVACY.md), and [docs/PLATFORMS.md](docs/PLATFORMS.md).

## Features (v0.1)

- **Desktop orb widget** — frameless, always-on-top floating wheel
- Click the **center** (or drop a file) to open
- After a file loads, **drag from the center** toward a format pad, or click a pad
- Background conversion with progress and cancellation
- Safe output naming (never overwrites the original by default)
- Optional LibreOffice / FFmpeg for best Office↔PDF and audio (`sudo apt install libreoffice ffmpeg` on Ubuntu)
- **No in-app updater** — new versions ship as new installers on the release page
- Security posture and limits: [docs/SECURITY.md](docs/SECURITY.md)

Conversion list: [docs/CONVERSION_MATRIX.md](docs/CONVERSION_MATRIX.md). Status: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

## End users (no Python required)

Download the Windows installer or Ubuntu archive from the **stable release page**, verify checksums, and follow [docs/INSTALL.md](docs/INSTALL.md).

After installation, core conversions work without internet.

## Development setup (Ubuntu)

```bash
cd Justconvertit
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements-release.txt
pip install -e ".[dev]"
```

### Run

```bash
python -m omniconvert
```

### Test

```bash
bash scripts/test.sh
```

> On some Ubuntu machines with ROS installed, plain `pytest` fails because system plugins break collection. Use `scripts/test.sh`.

## Development setup (Windows)

Windows is the **primary** product target. Full guide: [docs/WINDOWS.md](docs/WINDOWS.md).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements-release.txt
pip install -e ".[dev]"
python -m omniconvert
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; $env:QT_QPA_PLATFORM="offscreen"; pytest -p pytestqt
```

## Packaging (reproducible)

Release builds **must** use `requirements-release.txt`. Process: [docs/RELEASE.md](docs/RELEASE.md).

```bash
bash scripts/build_linux.sh
bash scripts/verify_offline.sh
```

Windows: `.\scripts\build_windows.ps1`, then compile `packaging/windows/installer.iss` with Inno Setup.

## License

MIT — see [LICENSE](LICENSE). Third-party notices: [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md).
