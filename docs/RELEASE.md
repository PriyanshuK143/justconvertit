# Release process (manual rebuild — no in-app updater)

justconvertit ships as a **one-time install**. There is no automatic update checker. New versions are published as new downloadable artifacts on a stable release page (GitHub Releases or equivalent).

## Artifacts per version

| Artifact | Platform | Contents |
|----------|----------|----------|
| `justconvertit_<ver>_amd64.deb` | Ubuntu | Debian package (`/opt/justconvertit`, desktop entry, icon) |
| `justconvertit-<ver>-Setup.exe` | Windows | Inno Setup installer wrapping the PyInstaller tree |
| `justconvertit_<ver>_amd64.sha256` / `justconvertit-<ver>-*.sha256` | both | SHA-256 checksums of the published files |
| Release notes | both | From `CHANGELOG.md` for that tag |

Also link from the release page:

- [Installation & uninstall](INSTALL.md)
- [Privacy](PRIVACY.md)
- [Platforms & limitations](PLATFORMS.md)
- [Conversion matrix](CONVERSION_MATRIX.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Build from pinned dependencies

```bash
git checkout v0.1.0   # or the release tag
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements-release.txt
pip install -e .

bash scripts/test.sh
pip install pip-audit && pip-audit -r requirements-release.txt
bash scripts/build_linux.sh
bash scripts/verify_offline.sh
```


Windows (on a Windows host):

```powershell
.\scripts\build_windows.ps1
# Then compile packaging\windows\installer.iss with Inno Setup
```

## Linux package (produced by build script)

`bash scripts/build_linux.sh` writes:

- `dist/justconvertit/` — PyInstaller folder (intermediate)
- `dist/justconvertit_<ver>_amd64.deb` — end-user installer
- `dist/justconvertit_<ver>_amd64.sha256` — checksum

(`scripts/build_deb.sh` can be run alone if the folder already exists.)

Publish the `.deb` and `.sha256` on the release page. Users install with App Center or `sudo apt install ./….deb`.

## Dependency inventory

| Source | Purpose |
|--------|---------|
| `requirements-release.txt` | Exact pins used for the release build |
| `pyproject.toml` | Package metadata + compatible ranges for development |
| `docs/THIRD_PARTY_NOTICES.md` | License notes for redistributed components |

When bumping a dependency: update the pin, run the full test suite, rebuild both platform artifacts, and document the change in `CHANGELOG.md`.

## What must never ship

- In-app update checkers or silent background downloaders
- Telemetry / analytics SDKs
- Account or licensing network clients
- Bundled LibreOffice or FFmpeg (unless a separate legal review approves a specific build)

## Known limitations (publish with each release)

See `docs/PLATFORMS.md` and the “Not claimed yet” section of `docs/CONVERSION_MATRIX.md`.
