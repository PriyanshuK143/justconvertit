$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
.\.venv\Scripts\Activate.ps1
if (Test-Path requirements-release.txt) {
  pip install -r requirements-release.txt
}
pip install -e .
pyinstaller --noconfirm --clean packaging/windows/omniconvert.spec

# Headless smoke (no GUI) — works without display
$in = Join-Path $env:TEMP "omniconvert-smoke.png"
$out = Join-Path $env:TEMP "omniconvert-smoke.jpg"
python -c "from PIL import Image; Image.new('RGB',(8,8),(1,2,3)).save(r'$in')"
& .\dist\justconvertit\justconvertit.exe --smoke-convert image.png_to_jpeg $in $out
if (-not (Test-Path $out)) { throw "Windows smoke conversion failed" }

Write-Host "Built dist/justconvertit — compile packaging/windows/installer.iss with Inno Setup"
Write-Host "No updater is bundled. Publish checksums with the release (see docs/RELEASE.md)."
Write-Host "Smoke convert OK. Still test the Setup.exe on a clean Windows PC without Python."
