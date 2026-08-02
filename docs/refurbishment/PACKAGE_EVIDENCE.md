# Package Evidence

- Build command: `powershell -ExecutionPolicy Bypass -File tools/build_package.ps1 -OutputDir _package_test`
- PyInstaller: `6.16.0`
- Python: `3.11.9`
- Target: Windows 10/11 x64 environment
- Artifact: `FocusCheck.exe`
- Artifact size: `72,391,894` bytes
- SHA-256: `016104D28D46423B5CC84D5AA754E8A8C0A6C29E0FE46A5190BFC717C37E0238`
- Packaged `--selftest`: passed with `FOCUS_DATA_DIR` set to disposable `_package_runtime/data`.
- Disposable package transaction simulation: promotion retained the previous package and wrote a SHA-256 manifest; rollback restored the previous executable and retained the failed package directory.

This proves the source package build, packaged self-test, and scripted package promotion/rollback transaction. Installer shell integration, code signing, and native manual evidence remain open.
