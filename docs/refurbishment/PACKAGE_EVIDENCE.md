# Package Evidence

- Build command: `powershell -ExecutionPolicy Bypass -File tools/build_package.ps1 -OutputDir <disposable-temp-root>`
- PyInstaller: `6.16.0`
- Python: `3.11.9`
- Target: Windows 10/11 x64 environment
- Current artifacts from commit `f48fb5b`: `FocusCheck.exe` (SHA-256 `27066AC2DE1F77D63B1D1C2B5BECB311FE340817821CC96F46C6505C83DDFEC7`) and `FocusCheckSupervisor.exe` (SHA-256 `0737E135526CC714E4628738A14511C9E6FE9A233B2A6C4BC31B7749444A69AA`).
- Packaged child `--selftest`: exited `0` with `FOCUS_DATA_DIR` set to disposable `_package_frozen_probe_runtime`.
- Frozen supervisor `--help`: exited `0`; frozen supervisor target resolution points at sibling `FocusCheck.exe`.
- Packaged supervisor self-test: reached a protocol-version `1` ready heartbeat, captured a valid child PID, and completed the bounded stop/acknowledgement/reaping flow on Windows; older harness runs that required forced tree termination are retained only as historical context.
- Current packaged protocol rerun: reached `READY`, wrote a generation-bound intentional-stop request, received a matching durable acknowledgement, and exited cleanly after supervisor-owned cleanup of both the outer frozen child and validated inner heartbeat PID; no package-owned processes remained afterward.
- Disposable package transaction simulation: promotion retained the previous package and wrote a complete SHA-256 file manifest; rollback restored the previous executable and retained the failed package directory; install/upgrade/uninstall preserved the data root and archived binaries. Package-candidate validation passed and rejected a tampered executable.
- Current candidate build: the distributable directory contained only `FocusCheck.exe` and `FocusCheckSupervisor.exe`; the separate PyInstaller work tree stayed outside it. Promotion generated the manifest, validation passed, and the packaged supervisor READY/intentional-stop/reaping self-test passed on commit `f48fb5b`.
- Current disposable lifecycle rerun: direct frozen child `--selftest` exited `0`; promotion, upgrade, rollback, manifest validation, uninstall archiving, and data-root preservation all passed in a temporary install root. The packaged supervisor harness reached `READY`, received a matching durable stop acknowledgement, and exited cleanly.
- Signing decision: development and local evidence packages are intentionally unsigned; production promotion must invoke `tools/package_lifecycle.ps1 -RequireSigned`, which delegates to `validate_package.ps1 -RequireSigned` and rejects either executable unless Authenticode status is `Valid`. No production certificate is present in this repository.
- Signing enforcement simulation: the current unsigned package was rejected with `NotSigned` and exit code `1` when installed with `-RequireSigned`.

This proves the source package build, dual frozen entrypoints, packaged child self-test, bounded packaged supervisor readiness/intentional-stop/reaping, package manifest/tamper validation, and scripted package lifecycle transactions. Installer shell integration, code signing, production-duration packaged supervision, and native manual evidence remain open.
