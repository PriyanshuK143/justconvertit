# Build JustConvertIt for Windows: PyInstaller folder + Inno Setup.exe
# Run on Windows 10/11 x64 with Python 3.12. Friends install the Setup.exe (no Python needed).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  throw "Missing .venv — create it first: py -3.12 -m venv .venv"
}
.\.venv\Scripts\Activate.ps1

if (Test-Path requirements-release.txt) {
  pip install -r requirements-release.txt
}
pip install -e .
pip install pyinstaller

Write-Host "==> PyInstaller (folder build)"
pyinstaller --noconfirm --clean packaging/windows/omniconvert.spec

$exe = ".\dist\justconvertit\justconvertit.exe"
if (-not (Test-Path $exe)) {
  throw "PyInstaller did not produce $exe"
}

Write-Host "==> Headless smoke convert (wait for GUI subsystem EXE)"
$in = Join-Path $env:TEMP "justconvertit-smoke.png"
$out = Join-Path $env:TEMP "justconvertit-smoke.jpg"
if (Test-Path $out) { Remove-Item -Force $out }
python -c "from PIL import Image; Image.new('RGB',(8,8),(1,2,3)).save(r'$in')"
# Windowed EXEs return early under `&` — always Start-Process -Wait.
$p = Start-Process -FilePath $exe `
  -ArgumentList @("--smoke-convert", "image.png_to_jpeg", $in, $out) `
  -Wait -PassThru -NoNewWindow
if ($null -ne $p.ExitCode -and $p.ExitCode -ne 0) {
  throw "smoke-convert exit code $($p.ExitCode)"
}
$deadline = (Get-Date).AddSeconds(45)
while (-not (Test-Path $out) -and (Get-Date) -lt $deadline) {
  Start-Sleep -Milliseconds 250
}
if (-not (Test-Path $out)) {
  throw "Windows smoke conversion failed — refusing to build installer"
}
Write-Host "Smoke convert OK: $out"

function Find-ISCC {
  $candidates = @(
    "${env:LocalAppData}\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
  )
  foreach ($c in $candidates) {
    if ($c -and (Test-Path $c)) { return $c }
  }
  $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
}

$iscc = Find-ISCC
if (-not $iscc) {
  Write-Host "Inno Setup 6 not found. Installing via winget (may prompt)…"
  try {
    winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
  } catch {
    Write-Warning "winget install failed: $_"
  }
  $iscc = Find-ISCC
}

if (-not $iscc) {
  Write-Warning "ISCC.exe still missing. Folder build is in dist\justconvertit\"
  Write-Warning "Install Inno Setup 6, then: & `$iscc packaging\windows\installer.iss"
  exit 2
}

Write-Host "==> Compiling installer with $iscc"
& $iscc "packaging\windows\installer.iss"
if ($LASTEXITCODE -ne 0) {
  throw "Inno Setup compile failed (exit $LASTEXITCODE)"
}

$setup = ".\packaging\windows\Output\JustConvertIt-0.1.0-Setup.exe"
if (-not (Test-Path $setup)) {
  # Older filename fallback
  $setup = Get-ChildItem ".\packaging\windows\Output\*Setup.exe" | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $setup -or -not (Test-Path $setup)) {
  throw "Setup.exe not found under packaging\windows\Output\"
}

New-Item -ItemType Directory -Force -Path ".\dist" | Out-Null
Copy-Item -Force $setup ".\dist\JustConvertIt-0.1.0-Setup.exe"
Get-FileHash ".\dist\JustConvertIt-0.1.0-Setup.exe" -Algorithm SHA256 |
  ForEach-Object { "$($_.Hash.ToLower())  JustConvertIt-0.1.0-Setup.exe" } |
  Set-Content -Encoding ascii ".\dist\JustConvertIt-0.1.0-Setup.sha256"

Write-Host ""
Write-Host "Share this with Windows friends (no Python needed):"
Write-Host "  dist\JustConvertIt-0.1.0-Setup.exe"
Write-Host "Checksum:"
Get-Content ".\dist\JustConvertIt-0.1.0-Setup.sha256"
Write-Host ""
Write-Host "Still test once on a clean Windows PC without Python before wide sharing."
