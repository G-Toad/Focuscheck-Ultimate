# Package Evidence

- Build command: `powershell -ExecutionPolicy Bypass -File tools/build_package.ps1 -OutputDir _package_test`
- PyInstaller: `6.16.0`
- Python: `3.11.9`
- Target: Windows 10/11 x64 environment
- Artifacts: `FocusCheck.exe` (72,412,721 bytes, SHA-256 `5D370A6828664BF9D445C693B3FD5834D0CAC3BDC7E8C6D9C4E5F533B554E49D`) and `FocusCheckSupervisor.exe` (8,247,294 bytes, SHA-256 `723E33D7D26D337C105E81C78DC37EB090025CEC66BEE1B1669ED97CDEDDE9EB`).
- Packaged child `--selftest`: exited `0` with `FOCUS_DATA_DIR` set to disposable `_package_frozen_probe_runtime`.
- Frozen supervisor `--help`: exited `0`; frozen supervisor target resolution points at sibling `FocusCheck.exe`.
- Packaged supervisor self-test: reached a protocol-version `1` ready heartbeat, captured a valid child PID, and reaped the supervisor process tree within the bounded timeout on Windows (forced tree termination reports exit code `1`).
- Current packaged protocol rerun: reached `READY`, wrote a generation-bound intentional-stop request, received a matching durable acknowledgement, and exited cleanly after supervisor-owned cleanup of both the outer frozen child and validated inner heartbeat PID; no package-owned processes remained afterward.
- Disposable package transaction simulation: promotion retained the previous package and wrote a SHA-256 manifest; rollback restored the previous executable and retained the failed package directory; install/upgrade/uninstall preserved the data root and archived binaries.

This proves the source package build, dual frozen entrypoints, packaged child self-test, bounded packaged supervisor readiness/intentional-stop/reaping, and scripted package lifecycle transactions. Installer shell integration, code signing, production-duration packaged supervision, and native manual evidence remain open.
