param(
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [Parameter(Mandatory = $true)][string]$BackupDir
)

$ErrorActionPreference = "Stop"
$install = [IO.Path]::GetFullPath($InstallDir)
$backup = (Resolve-Path -LiteralPath $BackupDir).Path
$parent = [IO.Path]::GetFullPath((Split-Path -Parent $install))
$backupItem = Get-Item -LiteralPath $backup -Force
if (($backupItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "BackupDir cannot be a reparse point: $backup"
}
$backupParent = [IO.Path]::GetFullPath((Split-Path -Parent $backup))
if ($backupParent.TrimEnd('\', '/') -ine $parent.TrimEnd('\', '/') -or
    -not $backupItem.Name.StartsWith('.FocusCheck.backup.', [StringComparison]::OrdinalIgnoreCase)) {
    throw "BackupDir must be a generated backup beside InstallDir: $backup"
}
$backupReparsePoints = Get-ChildItem -LiteralPath $backup -Recurse -Force -ErrorAction Stop |
    Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }
if ($backupReparsePoints) {
    throw "BackupDir contains reparse points: $($backupReparsePoints.FullName -join ', ')"
}
if (-not (Test-Path -LiteralPath (Join-Path $backup "FocusCheck.exe") -PathType Leaf)) {
    throw "BackupDir must contain FocusCheck.exe"
}
if ($backup.TrimEnd('\') -ieq $install.TrimEnd('\')) {
    throw "InstallDir and BackupDir must be different"
}
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
