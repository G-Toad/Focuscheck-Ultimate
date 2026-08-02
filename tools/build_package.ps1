param(
    [string]$OutputDir = "dist"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "PyInstaller is required. Install pinned development dependencies: py -3 -m pip install -r requirements-dev.txt"
}
& pyinstaller --clean --noconfirm --distpath $OutputDir --workpath (Join-Path $OutputDir "build") packaging\focuscheck.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Write-Output "Package output: $(Join-Path $root $OutputDir)"
