param(
    [switch]$SkipGui,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logDir = Join-Path $repoRoot "_verify_runtime"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# The Python runner owns stage isolation, timeouts, logs, and JSON evidence.
# Keep this PowerShell entry point for existing operators and CI jobs.
& py -3 (Join-Path $repoRoot "tools\verification_runner.py") --timeout $TimeoutSeconds
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "All verification stages passed. Logs: $logDir"
