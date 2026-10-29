# Security

justconvertit is a **local** desktop converter. It is **not** an antivirus product and
does not claim to make untrusted documents safe.

## What we harden

- Detect file type from contents (not extension alone) where practical
- Input size, image pixel, PDF page/render, and ZIP member/ratio limits
- Atomic output writes; refuse overwriting the source; unique output names
- Cancel/failure cleanup of incomplete destinations
- Subprocess calls use argument lists (no `shell=True`) with timeouts
- Optional LibreOffice / FFmpeg install only after explicit user confirmation
  (OS package manager — apt/winget), never a silent download into the app tree
- No telemetry, accounts, or cloud upload of your files

## Residual risk

Crafted or malicious files may still crash or exploit **third-party parsers**:

| Component | Used for |
|-----------|----------|
| Pillow | Images |
| pypdf / pypdfium2 | PDF text / render |
| ReportLab | Simple PDF write |
| python-docx / python-pptx / openpyxl / pandas | Office & tables |
| LibreOffice (system) | High-fidelity Office ↔ PDF |
| FFmpeg (system) | Audio / extract |

Conversions run in a **background thread inside the app process**, not a separate
OS sandbox. Treat unknown files carefully. Prefer opening untrusted PDFs/Office
files in an up-to-date viewer first.

## Dependency updates

Release pins live in `requirements-release.txt`. Run before a public build:

```bash
pip install pip-audit
pip-audit -r requirements-release.txt
```

Fix known vulnerabilities by bumping pins, then re-run `bash scripts/test.sh` and
a conversion smoke pass.

## Reporting issues

Open a repository issue with reproduction steps. Do not attach private documents
containing personal data.
