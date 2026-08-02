# FocusCheck Refurbishment State

- Repository: `G-Toad/Focuscheck-Ultimate`
- Source folder: `FocusCheck_newest_20260802_221221/3`
- Starting snapshot: `0f3beb5` (initial upload)
- Current automated baseline after hardening: `178` unittest cases passing.
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

This file distinguishes code-reviewed and automated evidence from manual Windows evidence. It is not a completion claim.
