# Package Evidence

- Build command: `powershell -ExecutionPolicy Bypass -File tools/build_package.ps1 -OutputDir _package_test`
- PyInstaller: `6.16.0`
- Python: `3.11.9`
- Target: Windows 10/11 x64 environment
- Artifacts: `FocusCheck.exe` (72,412,190 bytes, SHA-256 `3C50A6CB45DDB92CC8FF13C0B9AB2186DE30D1BA5F2B9988E247272AAAC613D0`) and `FocusCheckSupervisor.exe` (8,246,636 bytes, SHA-256 `C10D616A2241048974DFB29B2C86C5BBDD9F0425B041AF03283F2DBDC111CF59`).
- Packaged child `--selftest`: exited `0` with `FOCUS_DATA_DIR` set to disposable `_package_frozen_probe_runtime`.
- Frozen supervisor `--help`: exited `0`; frozen supervisor target resolution points at sibling `FocusCheck.exe`.
- Disposable package transaction simulation: promotion retained the previous package and wrote a SHA-256 manifest; rollback restored the previous executable and retained the failed package directory; install/upgrade/uninstall preserved the data root and archived binaries.

This proves the source package build, dual frozen entrypoints, packaged child self-test, and scripted package lifecycle transactions. Installer shell integration, code signing, a long-running packaged supervisor launch, and native manual evidence remain open.
