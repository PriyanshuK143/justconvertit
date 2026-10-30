# Linux packaging

End users should never need this folder. They download a release archive and run `./install.sh`.

## What a release archive contains

```
justconvertit/
  justconvertit          # app binary (PyInstaller)
  _internal/             # bundled runtime
  install.sh             # one-step user install
  uninstall.sh
  icons/justconvertit.png
  INSTALL.md
  PRIVACY.md
  LICENSE
```

## Build (maintainers)

```bash
bash scripts/build_linux.sh
# produces:
#   dist/justconvertit/                          # runnable tree
#   dist/justconvertit-0.1.0-linux-x86_64.tar.gz
#   dist/justconvertit-0.1.0-linux-x86_64.sha256
```

Smoke offline: `bash scripts/verify_offline.sh`

## End-user install

```bash
tar -xzf justconvertit-0.1.0-linux-x86_64.tar.gz
cd justconvertit
./install.sh
```

Default install path: `~/.local/opt/justconvertit`  
App menu entry + `~/.local/bin/justconvertit` symlink.

System-wide: `sudo ./install.sh --system` → `/opt/justconvertit`

## Optional wrappers

After the PyInstaller tree is verified:

- **AppImage** — wrap the folder with appimagetool
- **.deb** — package the same tree under `/opt/justconvertit`

Do not claim broad distro compatibility without testing each target. Do not add an in-app updater.
