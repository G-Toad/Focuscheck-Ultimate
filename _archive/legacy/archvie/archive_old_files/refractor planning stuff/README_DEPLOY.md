FocusCheck — Windows Packaging and Startup

Summary
- Build a Windows executable with PyInstaller (no console).
- Optional custom tray icon via `assets/focus.ico`.
- Install to run on login via registry (HKCU Run) with helper scripts or CLI flags.

Dev Run (no EXE)
- Double‑click `Start FocusCheck.cmd` to run the app without a console window while you iterate.
- To auto‑start while developing (no EXE), use the tray menu: Enable Run on Startup. It registers the Python command.

Prereqs
- Python 3.9+ on Windows
- PowerShell

Build
1) Optional: put an icon at `assets/focus.ico`.
2) Run the build script:
   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
   # or single-file exe:
   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -OneFile

Output appears under `dist/FocusCheck/FocusCheck.exe` (or a single exe under `dist`).

Install to Startup (current user)
Option A — scripts
   powershell -ExecutionPolicy Bypass -File scripts\install_startup.ps1
   # uninstall:
   powershell -ExecutionPolicy Bypass -File scripts\uninstall_startup.ps1

Option B — inside the app
   FocusCheck.exe --install-startup
   # uninstall:
   FocusCheck.exe --uninstall-startup
   # Dev mode without EXE:
   python guard.py --install-startup
   python guard.py --uninstall-startup

Notes
- The app already runs as a background tray app with a hidden Tk root; prompts appear as needed.
- If you see no icon, ensure `assets/focus.ico` exists before building, otherwise a system icon is used.
- Single-instance is enforced on Windows via a named mutex.

Troubleshooting
- If Tk/tcl resources are missing in the built exe, upgrade PyInstaller and rebuild.
- If the icon doesn’t show: confirm the `.ico` file path and format (contains 16/32 px sizes).
- If the app starts twice: check Task Manager startup and HKCU Run for duplicates.
