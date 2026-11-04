# Linux .deb packaging design

**Status:** Approved (2026-10-30)  
**Goal:** Ubuntu users install justconvertit like a normal app — download a `.deb`, install, open from the app menu. No zip + `./install.sh` end-user path.

## User experience

1. Download `justconvertit_<version>_amd64.deb` (+ `.sha256`) from the release page.
2. Double-click / open in Ubuntu Software, or run `sudo apt install ./justconvertit_<version>_amd64.deb`.
3. Launch **justconvertit** from the application menu.
4. Uninstall via Settings → Apps, or `sudo apt remove justconvertit`.

Windows remains `justconvertit-<version>-Setup.exe` (Inno Setup). Unchanged by this work.

## Package layout

| Path | Purpose |
|------|---------|
| `/opt/justconvertit/` | PyInstaller one-folder tree (`justconvertit` binary + `_internal/`) |
| `/usr/share/applications/justconvertit.desktop` | App menu entry (`Exec=/opt/justconvertit/justconvertit`) |
| `/usr/share/icons/hicolor/256x256/apps/justconvertit.png` | Icon |
| `/usr/bin/justconvertit` | Symlink to `/opt/justconvertit/justconvertit` |

Package metadata: name `justconvertit`, architecture `amd64`, section `utils`, priority `optional`, MIT license. Depends on common Qt/X11 runtime packages where practical (`libxcb-cursor0`, etc.) so fresh Ubuntu installs start cleanly.

Do **not** ship LibreOffice or FFmpeg inside the `.deb`. Optional engines stay first-run apt/winget.

## Build pipeline

1. `scripts/build_linux.sh` — produce `dist/justconvertit/` (PyInstaller). May still emit a maintainer tar.gz; not the end-user artifact.
2. `scripts/build_deb.sh` — stage a Debian control tree from that folder, run `dpkg-deb` (via `fakeroot`), write:
   - `dist/justconvertit_<version>_amd64.deb`
   - `dist/justconvertit_<version>_amd64.sha256`

## Docs / UX copy

- README + INSTALL + PLATFORMS + RELEASE: lead with `.deb` / Setup.exe.
- `install.sh` / `uninstall.sh`: keep for maintainers or remove from release staging; **not** documented as the end-user path.

## Out of scope

AppImage, Snap, Flatpak, in-app updater, multi-arch, signed repos.

## Self-review

- No placeholders left for required behavior.
- No contradiction with offline-first / no bundled LO+FFmpeg policy.
- Scope limited to Ubuntu `.deb` wrapping existing PyInstaller output.
