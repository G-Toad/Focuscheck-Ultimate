param(
    [Parameter(Mandatory = $true)][ValidateSet("Install", "Upgrade", "Uninstall")][string]$Action,
    [string]$PackageDir,
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [Parameter(Mandatory = $true)][string]$DataDir,
    [string]$Version = "dev",
    [switch]$RegisterStartup,
    [switch]$RequireSigned,
    [string]$StartupName = "FocusCheck"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$install = [IO.Path]::GetFullPath($InstallDir)
$data = [IO.Path]::GetFullPath($DataDir)

function Get-CanonicalStartupCommand([string]$InstallPath) {
    $supervisor = Join-Path $InstallPath "FocusCheckSupervisor.exe"
    return '"{0}" --run --base-dir "{1}"' -f $supervisor, $InstallPath
}

function Install-CanonicalStartup([string]$InstallPath, [string]$Name) {
    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    New-Item -Path $runKey -Force | Out-Null
    Set-ItemProperty -Path $runKey -Name $Name -Value (Get-CanonicalStartupCommand $InstallPath)
    Write-Output "Installed startup entry: $Name"
}

function Remove-MatchingStartup([string]$InstallPath, [string]$Name) {
    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    if (-not (Test-Path -LiteralPath $runKey)) { return }
    $current = (Get-ItemProperty -Path $runKey -Name $Name -ErrorAction SilentlyContinue).$Name
    if ([string]$current -eq (Get-CanonicalStartupCommand $InstallPath)) {
        Remove-ItemProperty -Path $runKey -Name $Name -ErrorAction SilentlyContinue
        Write-Output "Removed startup entry: $Name"
    } else {
        Write-Output "Startup entry retained because it does not target this installation: $Name"
    }
}

function Assert-PackageSourceSafe([string]$PackagePath) {
    $source = [IO.Path]::GetFullPath($PackagePath)
    $sourceItem = Get-Item -LiteralPath $source -Force
    if (-not $sourceItem.PSIsContainer) { throw "PackageDir must be a directory: $source" }
    if (($sourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "PackageDir cannot be a reparse point: $source"
    }
    $reparsePoints = Get-ChildItem -LiteralPath $source -Recurse -Force -ErrorAction Stop |
        Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }
    if ($reparsePoints) {
        throw "PackageDir contains reparse points: $($reparsePoints.FullName -join ', ')"
    }
    foreach ($name in @('FocusCheck.exe', 'FocusCheckSupervisor.exe')) {
        if (-not (Test-Path -LiteralPath (Join-Path $source $name) -PathType Leaf)) {
            throw "PackageDir must contain $name"
        }
    }
    $forbiddenExtensions = @('.py', '.pyc', '.pdb', '.sqlite3', '.jsonl')
    $forbidden = Get-ChildItem -LiteralPath $source -Recurse -File | Where-Object {
        $forbiddenExtensions -contains $_.Extension.ToLowerInvariant()
    }
    if ($forbidden) {
        throw "PackageDir contains source, debug, or runtime-data files: $($forbidden.FullName -join ', ')"
    }
}

function Assert-PackageSignatures([string]$PackagePath) {
    if (-not (Get-Command Get-AuthenticodeSignature -ErrorAction SilentlyContinue)) {
        throw "Signature validation is unavailable on this PowerShell host"
    }
    foreach ($name in @('FocusCheck.exe', 'FocusCheckSupervisor.exe')) {
        $signature = Get-AuthenticodeSignature -LiteralPath (Join-Path $PackagePath $name)
        if ($signature.Status -ne 'Valid') {
            throw "Unsigned or invalid executable: $name ($($signature.Status))"
        }
    }
}

function Get-ValidatedBackup([string]$InstallPath, [string]$Candidate) {
    if ([string]::IsNullOrWhiteSpace($Candidate)) { return $null }
    try {
        $installParent = [IO.Path]::GetFullPath((Split-Path -Parent $InstallPath))
        $backup = Get-Item -LiteralPath $Candidate -Force
        if (-not $backup.PSIsContainer) { return $null }
        if (($backup.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return $null }
        $backupParent = [IO.Path]::GetFullPath((Split-Path -Parent $backup.FullName))
        if ($backupParent.TrimEnd('\', '/') -ine $installParent.TrimEnd('\', '/') -or
            -not $backup.Name.StartsWith('.FocusCheck.backup.', [StringComparison]::OrdinalIgnoreCase)) {
            return $null
        }
        $reparsePoints = Get-ChildItem -LiteralPath $backup.FullName -Recurse -Force -ErrorAction Stop |
            Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }
        if ($reparsePoints) { return $null }
        if (-not (Test-Path -LiteralPath (Join-Path $backup.FullName 'FocusCheck.exe') -PathType Leaf)) {
            return $null
        }
        return $backup.FullName
    } catch {
        return $null
    }
}

function Restore-FailedPromotion([string]$InstallPath) {
    if (-not (Test-Path -LiteralPath $InstallPath)) { return }
    $manifestPath = Join-Path $InstallPath "package-manifest.json"
    $backup = $null
    if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
        try {
            $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
            if (-not [string]::IsNullOrWhiteSpace([string]$manifest.backup_dir)) {
                $backup = [IO.Path]::GetFullPath([string]$manifest.backup_dir)
            }
        } catch {
            Write-Warning "Unable to read promoted package manifest during rollback: $($_.Exception.Message)"
        }
    }
    $backup = Get-ValidatedBackup $InstallPath $backup
    $parent = Split-Path -Parent $InstallPath
    $failed = Join-Path $parent (".FocusCheck.failed.{0}" -f [Guid]::NewGuid().ToString("N"))
    Move-Item -LiteralPath $InstallPath -Destination $failed
    if ($backup -and (Test-Path -LiteralPath $backup)) {
        Move-Item -LiteralPath $backup -Destination $InstallPath
        Write-Warning "Validation failed; previous package restored. Failed package retained at $failed"
    } else {
        Write-Warning "Validation failed; no previous package was available. Failed package retained at $failed"
    }
}

if ($Action -ne "Uninstall" -and [string]::IsNullOrWhiteSpace($PackageDir)) {
    throw "$Action requires -PackageDir"
}

if ($Action -eq "Install" -or $Action -eq "Upgrade") {
    Assert-PackageSourceSafe $PackageDir
    if ($RequireSigned) { Assert-PackageSignatures $PackageDir }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "tools\promote_package.ps1") `
        -PackageDir $PackageDir -InstallDir $install -Version $Version
    if ($LASTEXITCODE -ne 0) { throw "Package promotion failed with exit code $LASTEXITCODE" }
    try {
        if ($RequireSigned) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "tools\validate_package.ps1") `
                -PackageDir $install -RequireSigned
        } else {
            & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "tools\validate_package.ps1") `
                -PackageDir $install
        }
        if ($LASTEXITCODE -ne 0) { throw "Promoted package validation failed with exit code $LASTEXITCODE" }
    } catch {
        Restore-FailedPromotion $install
        throw
    }
    if ($RegisterStartup) { Install-CanonicalStartup $install $StartupName }
    Write-Output "$Action completed; data root preserved at $data"
    exit 0
}

# Uninstall is intentionally reversible for release verification. The binary
# is archived beside the install directory; user data and its root are never
# removed by this script.
if (Test-Path -LiteralPath $install) {
    Remove-MatchingStartup $install $StartupName
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
