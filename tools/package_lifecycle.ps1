param(
    [Parameter(Mandatory = $true)][ValidateSet("Install", "Upgrade", "Uninstall")][string]$Action,
    [string]$PackageDir,
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [Parameter(Mandatory = $true)][string]$DataDir,
    [string]$Version = "dev"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$install = [IO.Path]::GetFullPath($InstallDir)
$data = [IO.Path]::GetFullPath($DataDir)

if ($Action -ne "Uninstall" -and [string]::IsNullOrWhiteSpace($PackageDir)) {
    throw "$Action requires -PackageDir"
}

if ($Action -eq "Install" -or $Action -eq "Upgrade") {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "tools\promote_package.ps1") `
        -PackageDir $PackageDir -InstallDir $install -Version $Version
    if ($LASTEXITCODE -ne 0) { throw "Package promotion failed with exit code $LASTEXITCODE" }
    Write-Output "$Action completed; data root preserved at $data"
    exit 0
}

# Uninstall is intentionally reversible for release verification. The binary
# is archived beside the install directory; user data and its root are never
# removed by this script.
if (Test-Path -LiteralPath $install) {
    $parent = Split-Path -Parent $install
    $archive = Join-Path $parent (".FocusCheck.uninstalled.{0}.{1}" -f (Get-Date -Format "yyyyMMddHHmmss"), [Guid]::NewGuid().ToString("N"))
    Move-Item -LiteralPath $install -Destination $archive
    Write-Output "Uninstall archived package at $archive"
} else {
    Write-Output "Install directory was already absent: $install"
}
if (Test-Path -LiteralPath $data) {
    Write-Output "Data root retained: $data"
} else {
    Write-Output "Data root not present; nothing removed: $data"
}
