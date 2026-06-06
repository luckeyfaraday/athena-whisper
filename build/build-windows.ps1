# Build the Athena Dictate Windows app (.exe) with PyInstaller.
# Run from the project root:  pwsh -File build/build-windows.ps1
# Output: dist/Athena Dictate/Athena Dictate.exe
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

Write-Output ""
Write-Output "Built: dist\Athena Dictate\Athena Dictate.exe"
