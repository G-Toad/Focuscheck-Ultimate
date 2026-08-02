@echo off
REM Launch FocusCheck via the supervisor so it survives crashes/sleep
setlocal

REM Base directory is wherever this script lives
pushd "%~dp0" >NUL || (
    echo Failed to change directory to script location.&exit /b 1
)

REM Prefer pythonw.exe to avoid a visible console window
set "PY_CMD=pythonw.exe"
where pythonw.exe >NUL 2>&1
if errorlevel 1 set "PY_CMD=python.exe"

set "FOCUSCHECK_FORCE_STARTED=1"

start "FocusCheck Supervisor" "%PY_CMD%" focuscheck_supervisor.py --run --base-dir "%CD%"
popd >NUL
endlocal
