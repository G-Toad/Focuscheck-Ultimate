# Windows Install

## Development

1. Use Python 3.11 on Windows.
2. Install runtime dependencies with `py -3 -m pip install -r requirements.txt`.
3. Run the supervised application with `start_focuscheck.bat`.

## Release build

1. Install pinned development dependencies with `py -3 -m pip install -r requirements-dev.txt`.
2. Run `powershell -ExecutionPolicy Bypass -File tools/build_package.ps1`. PyInstaller’s work tree is kept outside the candidate directory.
3. Validate the candidate before promotion:

```powershell
powershell -ExecutionPolicy Bypass -File tools/validate_package.ps1 -PackageDir .\dist\FocusCheck
```

Use `-RequireSigned` for a signed release. The validator checks both frozen
executables, the SHA-256 manifest, and rejects source/debug/runtime-data files.
Treat the output directory as a release candidate only after validation and the
manual Windows evidence matrix pass.

## Install or upgrade a package

Promote a tested package without modifying user data:

```powershell
powershell -ExecutionPolicy Bypass -File tools\promote_package.ps1 -PackageDir .\dist\FocusCheck -InstallDir "$env:LOCALAPPDATA\FocusCheck\app" -Version 1.0.0
```

For a disposable install/upgrade/uninstall lifecycle check, use
`tools\package_lifecycle.ps1`. Install and upgrade promote the package; uninstall
archives the binary and never removes the data root:

```powershell
powershell -ExecutionPolicy Bypass -File tools\package_lifecycle.ps1 -Action Install -PackageDir .\dist\FocusCheck -InstallDir "$env:LOCALAPPDATA\FocusCheck\app" -DataDir "$env:APPDATA\FocusCheck" -Version 1.0.0
powershell -ExecutionPolicy Bypass -File tools\package_lifecycle.ps1 -Action Uninstall -InstallDir "$env:LOCALAPPDATA\FocusCheck\app" -DataDir "$env:APPDATA\FocusCheck"
```

Add `-RegisterStartup` to the install/upgrade command when enabling the
canonical per-user Run entry. The entry targets `FocusCheckSupervisor.exe`,
never the child executable; uninstall removes it only when it still points at
the installation being removed.

The previous package is retained beside the install directory and the promoted executable receives a SHA-256 manifest. A release package must contain both `FocusCheck.exe` and `FocusCheckSupervisor.exe`; the frozen supervisor launches the sibling child executable.

The supervisor owns the application process. Do not create an independent startup entry for the child executable.
