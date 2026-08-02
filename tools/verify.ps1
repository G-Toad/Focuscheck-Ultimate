param(
    [switch]$SkipGui
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logDir = Join-Path $repoRoot "_verify_runtime"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Invoke-Stage {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$CommandLine
    )

    $safeName = $Name -replace '[^A-Za-z0-9_.-]', '_'
    $logPath = Join-Path $logDir "$safeName.log"
    Write-Host "==> $Name"
    try {
        Push-Location $repoRoot
        cmd.exe /d /s /c "$CommandLine > `"$logPath`" 2>&1"
        $exit = $LASTEXITCODE
        if (Test-Path $logPath) {
            Get-Content $logPath
        }
        if ($null -ne $exit -and $exit -ne 0) {
            throw "stage exited with code $exit"
        }
        Write-Host "PASS: $Name"
    }
    catch {
        Write-Host "FAIL: $Name"
        Write-Host "Log: $logPath"
        Write-Host $_
        exit 1
    }
    finally {
        Pop-Location
    }
}

$python = "py"
$pythonArgs = @("-3")

try {
    & $python @pythonArgs -c "import sys; print(sys.version)" *> $null
}
catch {
    $python = "python"
    $pythonArgs = @()
}

$py = (@($python) + $pythonArgs) -join " "

Invoke-Stage "compileall" "$py -m compileall main.py focuscheck focuscheck_supervisor.py tests tools"

Invoke-Stage "unittest" "$py -m unittest discover -s tests -p `"test*.py`""

if ($SkipGui) {
    Invoke-Stage "qa_scenario_runner" "$py tools\qa_scenario_runner.py --reset --skip-gui"
}
else {
    Invoke-Stage "qa_scenario_runner" "$py tools\qa_scenario_runner.py --reset"
}

Invoke-Stage "main_selftest" "$py main.py --selftest"

Invoke-Stage "tray_selftest" "$py main.py --tray-selftest"

Invoke-Stage "settings_inventory" "$py tools\settings_inventory.py"

Write-Host "All verification stages passed. Logs: $logDir"
