param(
    [Parameter(Mandatory = $true)][string]$PackageDir,
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [string]$Version = "dev"
)

$ErrorActionPreference = "Stop"
$sha256 = [Security.Cryptography.SHA256]::Create()
function Get-Sha256Hex([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    return ([BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
}
$source = (Resolve-Path -LiteralPath $PackageDir).Path
$install = [IO.Path]::GetFullPath($InstallDir)
$parent = Split-Path -Parent $install
$sourceItem = Get-Item -LiteralPath $source -Force
if (($sourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "PackageDir cannot be a reparse point: $source"
}
$sourceReparsePoints = Get-ChildItem -LiteralPath $source -Recurse -Force -ErrorAction Stop |
    Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }
if ($sourceReparsePoints) {
    throw "PackageDir contains reparse points: $($sourceReparsePoints.FullName -join ', ')"
}
if (-not (Test-Path -LiteralPath (Join-Path $source "FocusCheck.exe") -PathType Leaf)) {
    throw "PackageDir must contain FocusCheck.exe"
}
if ($source.TrimEnd('\') -ieq $install.TrimEnd('\')) {
    throw "PackageDir and InstallDir must be different"
}
New-Item -ItemType Directory -Force -Path $parent | Out-Null

$token = [Guid]::NewGuid().ToString("N")
$staging = Join-Path $parent ".FocusCheck.staging.$token"
$backup = Join-Path $parent (".FocusCheck.backup.{0}.{1}" -f (Get-Date -Format "yyyyMMddHHmmss"), $token)
try {
    New-Item -ItemType Directory -Force -Path $staging | Out-Null
    Copy-Item -Path (Join-Path $source "*") -Destination $staging -Recurse -Force
    if (-not (Test-Path -LiteralPath (Join-Path $staging "FocusCheck.exe") -PathType Leaf)) {
        throw "Staged package failed executable verification"
    }
    if (Test-Path -LiteralPath $install) {
        Move-Item -LiteralPath $install -Destination $backup
    }
    try {
        Move-Item -LiteralPath $staging -Destination $install
    } catch {
        if ((Test-Path -LiteralPath $backup) -and -not (Test-Path -LiteralPath $install)) {
            Move-Item -LiteralPath $backup -Destination $install
        }
        throw
    }
    $files = @(
        Get-ChildItem -LiteralPath $install -Recurse -File |
            Where-Object { $_.Name -ne "package-manifest.json" } |
            ForEach-Object {
                $relative = ($_.FullName.Substring($install.Length).TrimStart('\', '/')).Replace('\', '/')
                [ordered]@{
                    path = $relative
                    sha256 = Get-Sha256Hex $_.FullName
                }
            }
    )
    [ordered]@{
        version = $Version
        install_dir = $install
        backup_dir = if (Test-Path $backup) { $backup } else { $null }
        files = $files
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $install "package-manifest.json") -Encoding UTF8
    Write-Output "Promoted package to $install"
    if (Test-Path $backup) { Write-Output "Previous package retained at $backup" }
} catch {
    if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
    throw
}
