# Privacy statement

**Effective for justconvertit 0.1.x**

justconvertit is a one-time-install, offline-first desktop application.

## What we do with your files

- Conversions run **on your computer**.
- Source and output files stay in the folders you choose.
- The application does **not** upload documents to a remote server.
- There is **no** cloud conversion service.

## What we do not collect

justconvertit does **not**:

- Require an account, subscription, or license server
- Send telemetry, analytics, crash reports, or usage statistics
- Check for updates over the network
- Phone home at launch or during conversion
- Bundle advertising or tracking SDKs

## Optional engines (LibreOffice, FFmpeg)

- justconvertit **detects** these tools on your machine (PATH / known locations).
- It does **not** download engine binaries into the justconvertit install folder.
- On first launch (or from Settings), you may **optionally** confirm installing them
  via your **OS package manager** (`apt` on Ubuntu, `winget` on Windows). That step
  needs internet and OS admin approval. It is never silent.
- Uninstalling justconvertit does **not** remove those system packages.

## Local data the app may store

On your machine only (typical locations under your user profile):

- Application settings (e.g. default output folder, JPEG quality)
- Recent conversion history (paths you already used)
- Local log files for troubleshooting (errors; not document contents)

You can clear recent history from Settings. Uninstalling removes the application files; user settings/logs under your profile may remain until you delete them.

## Network use

| Situation | Network needed? |
|-----------|-----------------|
| Core image / PDF / text / table conversions | **No** |
| Detecting already-installed LibreOffice / FFmpeg | **No** |
| Optional first-run / Settings apt or winget install | **Yes** (once, if you choose Install) |
| Building installers from source (developers) | Yes, to fetch pinned Python deps once |

## Security limitations

justconvertit is **not** an antivirus product. Malformed or malicious documents may still
pose risks through third-party parsers (Pillow, PDFium, LibreOffice, FFmpeg, etc.).
Treat untrusted files carefully. See [SECURITY.md](SECURITY.md) and the conversion
matrix for fidelity limits.

## Contact

Questions about this statement can be raised in the project repository. This document is informational and not legal advice.
