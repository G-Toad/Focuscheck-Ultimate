# FocusCheck Refurbishment State

- Repository: `G-Toad/Focuscheck-Ultimate`
- Source folder: `FocusCheck_newest_20260802_221221/3`
- Starting snapshot: `0f3beb5` (initial upload)
- Current automated baseline after hardening: `198` unittest cases passing.
- App composition now captures one immutable `AppPaths` snapshot for task, journal, heartbeat, tray, log-header, and data-control ownership.
- Runtime state now writes bounded metadata-only transition records under the canonical data root.
- Compile/self-tests: passing.
- Isolated native overlay self-test: passing with virtual-screen region updates.
- Safe QA runner: passing with `qa_failures=0`; verification asserts the live profile is unchanged.
- Release decision: `NOT_READY`.
- Manual blocker: live Tk/tray, Windows supervisor/startup, browser/window APIs, native lock/sleep/resume, overlays, and packaging require target Windows evidence.
- Supervisor stop requests now have an atomic generation-bound acknowledgement; cancellation-aware restart waits avoid delaying explicit supervisor shutdown.
- Pause-guard native API failures now publish bounded health metadata rather than degrading silently.
- Startup inspection distinguishes legacy and duplicate launch mechanisms, and repair promotes the registry route while removing the known legacy launcher.
- Single-instance mutex ownership now has explicit Win32 signatures and deterministic handle release on application exit/failure.
- App lifecycle transitions are validated by a coordinator and exposed in the App heartbeat.
- Lifecycle/runtime metadata is persisted in a bounded privacy-safe structured event ledger and is eligible for sanitized diagnostic bundles.
- Settings UI save-key/schema drift is statically checked; full schema-generated controls remain a separate open requirement.
- Windows shutdown query and committed end-session paths are distinct; committed shutdown uses the normal cleanup coordinator.
- Guard refreshes are coordinator-owned and unchanged guard states do not create duplicate transition records.
- The activity process-path probe now declares its Win32 handle, buffer, and pointer signatures before crossing the ctypes boundary.
- Foreground and top-level window enumeration now declare user32, process, and PSAPI signatures before crossing the ctypes boundary.
- Task analytics now store UTC while accepting an explicit timezone and injected clock for local-day/DST boundaries; existing callers retain an explicit UTC default.
- TaskDB schema migration version 3 normalizes recoverable legacy timestamps and clears invalid legacy due dates with an auditable repair reason; a checked-in legacy SQL fixture covers the path.
- Settings inventory now distinguishes editor references from runtime consumers and proves all 170 visible save keys have a non-editor consumer.
- TaskDB now verifies SQLite integrity and creates a numbered pre-migration backup before mutating an older database; corrupt files are rejected without replacement.
- `tools/export_data.py` and tray/App data controls provide atomic allowlisted export, metadata-only inventory, confirmed clear-log/personal-data actions, and explicit-age log retention with sensitive-category safeguards and metadata-only audit records; the bounded runner exercises the export path in a disposable root.
- The tray diagnostic bundle action previews allowlisted operational files and creates a sanitized bundle that excludes settings, tasks, camera files, and exports.

This file distinguishes code-reviewed and automated evidence from manual Windows evidence. It is not a completion claim.
