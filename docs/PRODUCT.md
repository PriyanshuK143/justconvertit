# justconvertit — product philosophy (one-time install, offline-first)

## Guarantees

1. Install once; keep using without accounts, subscriptions, or cloud APIs.
2. No in-app updater, background update checks, or update notifications.
3. No telemetry, remote analytics, licensing servers, or mandatory accounts.
4. Launch and run built-in conversions completely offline.
5. Standalone Windows and Ubuntu artifacts bundle the Python runtime, Qt, and pip-legal conversion libraries needed for core features.
6. Optional tools (FFmpeg, LibreOffice) are detected **locally** only.
7. All conversion processing is local by default.
8. Modular conversion registry, background jobs, safe file handling, and automated tests remain.
9. End users do not need Python, pip, or developer tools for the core app.
10. No unnecessary services, databases, cloud infrastructure, or networking code.

## Implementation anchors

| Concern | Location |
|---------|----------|
| Explicit product flags | `src/omniconvert/product.py` |
| Forbidden network import tests | `tests/unit/test_offline_policy.py` |
| Pinned release deps | `requirements-release.txt` |
| Privacy | `docs/PRIVACY.md` |
| Platforms / limits | `docs/PLATFORMS.md` |
| Rebuild / publish | `docs/RELEASE.md` |
| Install / uninstall | `docs/INSTALL.md` |

## Long-term reliability

- Rebuild installers manually from pins when dependencies or OS baselines change.
- Fail gracefully when optional engines are missing (hide ops / clear errors).
- Do not promise forever-compatibility with untested future OS versions.
