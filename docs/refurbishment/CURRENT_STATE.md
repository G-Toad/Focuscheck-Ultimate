# FocusCheck Refurbishment State

- Repository: `G-Toad/Focuscheck-Ultimate`
- Source folder: `FocusCheck_newest_20260802_221221/3`
- Starting snapshot: `0f3beb5` (initial upload)
- Current automated baseline after hardening: `149` unittest cases passing.
- Runtime state now writes bounded metadata-only transition records under the canonical data root.
- Compile/self-tests: passing.
- Isolated native overlay self-test: passing with virtual-screen region updates.
- Safe QA runner: passing with `qa_failures=0`; verification asserts the live profile is unchanged.
- Release decision: `NOT_READY`.
- Manual blocker: live Tk/tray, Windows supervisor/startup, browser/window APIs, native lock/sleep/resume, overlays, and packaging require target Windows evidence.

This file distinguishes code-reviewed and automated evidence from manual Windows evidence. It is not a completion claim.
