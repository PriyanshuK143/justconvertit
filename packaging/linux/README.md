# Linux packaging

## Standalone folder (primary)

1. Pin deps: `pip install -r requirements-release.txt && pip install -e .`
2. Build: `bash scripts/build_linux.sh`
3. Smoke offline: `bash scripts/verify_offline.sh`
4. Test `dist/justconvertit/justconvertit` on a clean Ubuntu VM **without** Python/pip installed for the user.
5. Archive + checksum (see `docs/RELEASE.md`).

Install/uninstall steps for end users: `docs/INSTALL.md`.

## Optional wrappers

After the PyInstaller tree is verified:

- **AppImage** — wrap the folder with [appimagetool](https://appimage.github.io/)
- **.deb** — install under `/opt/justconvertit`, ship `justconvertit.desktop`, and a symlink in `/usr/local/bin`

Do not claim broad distro compatibility without testing each target. Do not add an in-app updater.
