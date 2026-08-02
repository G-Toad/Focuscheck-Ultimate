param(
    [string]$OutputDir = "dist"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
$output = [IO.Path]::GetFullPath($OutputDir)
$outputParent = Split-Path -Parent $output
$outputName = Split-Path -Leaf $output
$work = Join-Path $outputParent (".{0}.pyinstaller-work" -f $outputName)
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "PyInstaller is required. Install pinned development dependencies: py -3 -m pip install -r requirements-dev.txt"
}
& pyinstaller --clean --noconfirm --distpath $output --workpath $work packaging\focuscheck.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Write-Output "Package output: $output"
