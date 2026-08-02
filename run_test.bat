@echo off
echo Running the isolated snooze dialog test...
echo All output will be saved to test_output.log
echo.

if not exist _archive\scratch mkdir _archive\scratch
py -3 tools\manual_snooze_dialog.py > _archive\scratch\test_output.log 2>&1

echo --- TEST COMPLETE ---
echo.
echo The full output is captured in test_output.log.
echo Displaying contents below:
echo.
echo ======================================================================
type test_output.log
echo ======================================================================
echo.
pause
