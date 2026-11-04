# Linux packaging

End users install the **`.deb`**. They never need this folder or an install script.

## End-user artifact

```
dist/justconvertit_<version>_amd64.deb
dist/justconvertit_<version>_amd64.sha256
```

Install: double-click / App Center, or `sudo apt install ./justconvertit_0.1.0_amd64.deb`

## Build (maintainers)

```bash
bash scripts/build_linux.sh    # PyInstaller → dist/justconvertit/ → .deb
bash scripts/verify_offline.sh
```

Or, if the folder already exists:

```bash
bash scripts/build_deb.sh
```

Package layout: `/opt/justconvertit`, desktop entry, icon, `/usr/bin/justconvertit`.

## Maintainer helpers (not for end users)

`install.sh` / `uninstall.sh` remain for local smoke tests without `dpkg`. Do not publish them as the product install path.

Do not claim broad distro compatibility without testing. Do not add an in-app updater.
