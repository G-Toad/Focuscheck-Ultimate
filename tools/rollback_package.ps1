param(
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [Parameter(Mandatory = $true)][string]$BackupDir
)

$ErrorActionPreference = "Stop"
$install = [IO.Path]::GetFullPath($InstallDir)
$backup = (Resolve-Path -LiteralPath $BackupDir).Path
if (-not (Test-Path -LiteralPath (Join-Path $backup "FocusCheck.exe") -PathType Leaf)) {
    throw "BackupDir must contain FocusCheck.exe"
}
if ($backup.TrimEnd('\') -ieq $install.TrimEnd('\')) {
    throw "InstallDir and BackupDir must be different"
}
$parent = Split-Path -Parent $install
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$failed = Join-Path $parent (".FocusCheck.failed.{0}" -f [Guid]::NewGuid().ToString("N"))
if (Test-Path -LiteralPath $install) {
    Move-Item -LiteralPath $install -Destination $failed
}
try {
    Move-Item -LiteralPath $backup -Destination $install
    Write-Output "Rolled back package to $install"
    Write-Output "Failed package retained at $failed"
} catch {
    if ((Test-Path -LiteralPath $failed) -and -not (Test-Path -LiteralPath $install)) {
        Move-Item -LiteralPath $failed -Destination $install
    }
    throw
}
