# Windows Install

## Development

1. Use Python 3.11 on Windows.
2. Install runtime dependencies with `py -3 -m pip install -r requirements.txt`.
3. Run the supervised application with `start_focuscheck.bat`.

## Release build

1. Install pinned development dependencies with `py -3 -m pip install -r requirements-dev.txt`.
2. Run `powershell -ExecutionPolicy Bypass -File tools/build_package.ps1`.
3. Treat `dist/FocusCheck` as a package candidate only after the manual Windows evidence matrix passes.

The supervisor owns the application process. Do not create an independent startup entry for the child executable.
