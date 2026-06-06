# Build the Athena Dictate Windows installer with PyInstaller + Inno Setup.
# Run from the project root:  pwsh -File build/build-windows.ps1
# Output: dist/Athena Dictate Setup.exe  (and dist/Athena Dictate/ folder app)
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
$py = Join-Path $root ".venv\Scripts\python.exe"

& $py -m pip install --upgrade pip
& $py -m pip install -e ".[gui]"
& $py -m pip install pyinstaller pillow

& $py build/generate_icons.py
& $py -m PyInstaller build/athena-dictate.spec --noconfirm --clean --distpath dist --workpath build/work

# Wrap the folder app in a single-file installer with Inno Setup.
$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($iscc) {
    & $iscc "build\windows-installer.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compile failed (ISCC exit code $LASTEXITCODE)."
    }
    Write-Output ""
    Write-Output "Built: dist\Athena Dictate Setup.exe"
} else {
    Write-Warning "Inno Setup (ISCC.exe) not found - skipping installer."
    Write-Warning "Install it from https://jrsoftware.org/isdl.php (or 'choco install innosetup'),"
    Write-Warning "then re-run. The folder app is in dist\Athena Dictate."
    Write-Output ""
    Write-Output "Built: dist\Athena Dictate\Athena Dictate.exe"
}
