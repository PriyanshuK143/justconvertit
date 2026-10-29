# Windows development & packaging

Windows 10/11 **64-bit** is the primary supported desktop target. Ubuntu remains fully supported from the same codebase.

## Development setup (Windows)

```powershell
# Python 3.12 from python.org or winget
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements-release.txt
pip install -e ".[dev]"
python -m omniconvert
bash scripts/test.sh   # or: $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; pytest -p pytestqt
```

Do **not** hardcode paths under `C:\Users\...`. Use `pathlib` and the helpers in `omniconvert.platform.paths`.

## High-DPI / display

The app enables Qt high-DPI scaling (`PassThrough` rounding) for 100% / 125% / 150% / 200%. The orb is a fixed logical size; Qt scales it with the display factor.

## Optional engines

Settings → LibreOffice / FFmpeg executable fields. Detection order:

1. User-configured path (supports spaces)
2. Common Windows install locations (`Program Files\LibreOffice\program\soffice.exe`, etc.)
3. `PATH`

justconvertit never downloads these tools.

## Packaging choice: PyInstaller (primary)

| Tool | Decision |
|------|----------|
| **PyInstaller** | **Selected** — already used for Linux; Inno Setup wraps the folder; reproducible with `requirements-release.txt` |
| **pyside6-deploy** (Nuitka) | Evaluated ([Qt docs](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html)); optional alternative. Heavier compile times; needs MSVC `dumpbin` on Windows. Spec scaffold: `packaging/windows/pysidedeploy.spec.example` |

### Build installer (on a Windows machine)

```powershell
.\scripts\build_windows.ps1
# Install Inno Setup 6, then compile:
#   packaging\windows\installer.iss
```

Outputs:

- `dist\justconvertit\justconvertit.exe` — runnable folder build
- `packaging\windows\Output\justconvertit-0.1.0-Setup.exe` — installer with Start Menu + uninstaller

Publish SHA-256 checksums with the release (see `docs/RELEASE.md`).

### Clean-machine test checklist

On a Windows 10/11 PC **without** Python installed:

1. Install via Setup.exe
2. Launch from Start Menu
3. Convert a PNG → JPEG offline (disable network if desired)
4. Confirm Settings shows LibreOffice/FFmpeg status
5. Uninstall from Apps & Features

**This Linux development host cannot execute or verify the Windows `.exe`/Inno installer.** Those steps must be run on Windows or `windows-latest` CI.

## App identity

- Product name: justconvertit
- Icon: `packaging/windows/omniconvert.ico`
- AppUserModelID: `justconvertit.Desktop.1`
