param(
    [Parameter(Mandatory = $true)][string]$PackageDir,
    [switch]$RequireSigned
)

$ErrorActionPreference = "Stop"
$sha256 = [Security.Cryptography.SHA256]::Create()
function Get-Sha256Hex([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    return ([BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
}
$package = [IO.Path]::GetFullPath($PackageDir)
if (-not (Test-Path -LiteralPath $package -PathType Container)) {
    throw "Package directory does not exist: $package"
}

# A release package must be a self-contained directory tree. Reparse points
# could redirect validation or installation outside the package root.
$reparsePoints = Get-ChildItem -LiteralPath $package -Recurse -Force -ErrorAction Stop |
    Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }
if ($reparsePoints) {
    throw "Package contains reparse points: $($reparsePoints.FullName -join ', ')"
}

$required = @("FocusCheck.exe", "FocusCheckSupervisor.exe", "package-manifest.json")
foreach ($name in $required) {
    $path = Join-Path $package $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Package is missing required artifact: $name"
    }
}

$forbiddenExtensions = @(".py", ".pyc", ".pdb", ".sqlite3", ".jsonl")
$forbidden = Get-ChildItem -LiteralPath $package -Recurse -File | Where-Object {
    $forbiddenExtensions -contains $_.Extension.ToLowerInvariant()
}
if ($forbidden) {
    throw "Package contains source, debug, or runtime-data files: $($forbidden.FullName -join ', ')"
}

if ($RequireSigned) {
    foreach ($name in @("FocusCheck.exe", "FocusCheckSupervisor.exe")) {
        $signature = Get-AuthenticodeSignature -LiteralPath (Join-Path $package $name)
        if ($signature.Status -ne "Valid") {
            throw "Unsigned or invalid executable: $name ($($signature.Status))"
        }
    }
}

$manifest = Get-Content -LiteralPath (Join-Path $package "package-manifest.json") -Raw | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace([string]$manifest.version) -or $manifest.files -eq $null) {
    throw "Package manifest must contain version and files"
}
$manifestByPath = @{}
foreach ($entry in $manifest.files) {
    $relative = ([string]$entry.path).Replace('\', '/')
    if ([string]::IsNullOrWhiteSpace($relative) -or [IO.Path]::IsPathRooted($relative) -or
        $relative -eq '..' -or $relative.StartsWith('../', [StringComparison]::Ordinal)) {
        throw "Package manifest contains an unsafe path: $relative"
    }
    if ($manifestByPath.ContainsKey($relative)) {
        throw "Package manifest contains a duplicate path: $relative"
    }
    $candidate = [IO.Path]::GetFullPath((Join-Path $package $relative))
    $packagePrefix = $package.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if (-not $candidate.StartsWith($packagePrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Package manifest path escapes package root: $relative"
    }
    $digest = [string]$entry.sha256
    if ($digest -notmatch '^[0-9a-fA-F]{64}$') {
        throw "Package manifest contains an invalid SHA-256 digest: $relative"
    }
    $manifestByPath[$relative] = $digest
}
$actualFiles = Get-ChildItem -LiteralPath $package -Recurse -File | Where-Object { $_.Name -ne "package-manifest.json" }
foreach ($file in $actualFiles) {
    $relative = ($file.FullName.Substring($package.Length).TrimStart('\', '/')).Replace('\', '/')
    if (-not $manifestByPath.ContainsKey($relative)) {
        throw "Package manifest is missing: $relative"
    }
    $hash = Get-Sha256Hex $file.FullName
    if ($hash -ne $manifestByPath[$relative].ToLowerInvariant()) {
        throw "Package manifest hash mismatch: $relative"
    }
}
foreach ($path in $manifestByPath.Keys) {
    if (-not (Test-Path -LiteralPath (Join-Path $package $path) -PathType Leaf)) {
        throw "Package manifest references missing file: $path"
    }
}

Write-Output "Package validation passed: $package"
