# Package Evidence

- Build command: `powershell -ExecutionPolicy Bypass -File tools/build_package.ps1 -OutputDir <disposable-temp-root>`
- PyInstaller: `6.16.0`
- Python: `3.11.9`
- Target: Windows 10/11 x64 environment
- Historical artifacts from commit `f48fb5b`: `FocusCheck.exe` (SHA-256 `27066AC2DE1F77D63B1D1C2B5BECB311FE340817821CC96F46C6505C83DDFEC7`) and `FocusCheckSupervisor.exe` (SHA-256 `0737E135526CC714E4628738A14511C9E6FE9A233B2A6C4BC31B7749444A69AA`).
- Packaged child `--selftest`: exited `0` with `FOCUS_DATA_DIR` set to disposable `_package_frozen_probe_runtime`.
- Frozen supervisor `--help`: exited `0`; frozen supervisor target resolution points at sibling `FocusCheck.exe`.
- Packaged supervisor self-test: reached a protocol-version `1` ready heartbeat, captured a valid child PID, and completed the bounded stop/acknowledgement/reaping flow on Windows; older harness runs that required forced tree termination are retained only as historical context.
- Current packaged protocol rerun: reached `READY`, wrote a generation-bound intentional-stop request, received a matching durable acknowledgement, and exited cleanly after supervisor-owned cleanup of both the outer frozen child and validated inner heartbeat PID; no package-owned processes remained afterward.
- Disposable package transaction simulation: promotion retained the previous package and wrote a complete SHA-256 file manifest; rollback restored the previous executable and retained the failed package directory; install/upgrade/uninstall preserved the data root and archived binaries. Package-candidate validation passed and rejected a tampered executable.
- Current candidate from commit `61f862b`: `FocusCheck.exe` (SHA-256 `50EC387E3CFEDC37E2DFABF890B10067ECAA49440A07236486FB5689E2C45B1D`) and `FocusCheckSupervisor.exe` (SHA-256 `7C91042B15A10D3FDFE16A5EA2DB3745862F653B3A816DF4E929A3BE69119E9C`). The distributable directory contained only the two executables; promotion generated the manifest, validation passed, the packaged child `--selftest` exited `0`, and the packaged supervisor READY/intentional-stop/reaping self-test passed.
- Current disposable lifecycle rerun: install, upgrade with backup retention, uninstall archiving, and data-root preservation all passed in a temporary install root.
- Signing decision: development and local evidence packages are intentionally unsigned; production promotion must invoke `tools/package_lifecycle.ps1 -RequireSigned`, which delegates to `validate_package.ps1 -RequireSigned` and rejects either executable unless Authenticode status is `Valid`. No production certificate is present in this repository.
- Signing enforcement simulation: the current unsigned package was rejected with `NotSigned` and exit code `1` when installed with `-RequireSigned`.
- Current rebuild from commit `c8c8f2d`: PyInstaller `6.16.0` produced both executables, promotion and manifest validation passed, and the frozen child `--selftest` exited `0`. SHA-256: `FocusCheck.exe` `1A1FC7BB12A8DE4751FFF85C23C35E6909BD151F39DFD31749008A7F05B098FE`; `FocusCheckSupervisor.exe` `243AF7A2BE6F66C79991A2965239BBE03A08D839D24C1213D17AFF840DE54E15`.
- Current packaged supervisor self-test reached READY, completed the generation-bound intentional-stop acknowledgement, and reaped the packaged child without a remaining package-owned process. Data was isolated under `_package_runtime`.
- Current disposable transaction also passed `Install`, `Upgrade`, and reversible `Uninstall` using fresh `_package_runtime` paths; upgrade retained the previous package backup, uninstall archived the binaries, and no data root was deleted. An unrelated existing startup entry was retained by the target-match safeguard.

This proves the source package build, dual frozen entrypoints, packaged child self-test, bounded packaged supervisor readiness/intentional-stop/reaping, package manifest/tamper validation, and scripted package lifecycle transactions. Installer shell integration, code signing, production-duration packaged supervision, and native manual evidence remain open.

Current rebuild from source checkpoint `6b86d3f` on 2026-08-03 produced `FocusCheck.exe` SHA-256 `B9B117A5B4308671B10E7ED4B686515BAB240CEB2A9748DB3346632254463FF3` and `FocusCheckSupervisor.exe` SHA-256 `A6F7AB71B141541541B76BB8AEB099C0118C60CBD43F9630BA761BBD2740D7B736D`; promotion generated a versioned manifest, validation passed, and the promoted frozen supervisor self-test reached READY and completed a durable intentional-stop acknowledgement with no package-owned process remaining.

The same current package then passed a fresh disposable `Install` -> `Upgrade` -> `Uninstall` transaction. Upgrade retained a timestamped backup, uninstall archived the binaries, and a sentinel file in the separate data root survived both operations; no startup entry was changed because registration was not requested.
