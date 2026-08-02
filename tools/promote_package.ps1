param(
    [Parameter(Mandatory = $true)][string]$PackageDir,
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [string]$Version = "dev"
)

$ErrorActionPreference = "Stop"
$source = (Resolve-Path -LiteralPath $PackageDir).Path
$install = [IO.Path]::GetFullPath($InstallDir)
$parent = Split-Path -Parent $install
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
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [IO.File]::ReadAllBytes((Join-Path $install "FocusCheck.exe"))
        $hash = ([BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace("-", "")
    } finally {
        $sha256.Dispose()
    }
    [ordered]@{ version = $Version; install_dir = $install; backup_dir = if (Test-Path $backup) { $backup } else { $null }; sha256 = $hash } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $install "package-manifest.json") -Encoding UTF8
    Write-Output "Promoted package to $install"
    if (Test-Path $backup) { Write-Output "Previous package retained at $backup" }
} catch {
    if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
    throw
}
