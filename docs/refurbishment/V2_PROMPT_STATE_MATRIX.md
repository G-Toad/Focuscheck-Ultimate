# V2 Prompt and Website-Intervention State Matrix

This matrix is the V2 acceptance contract. Automated evidence proves deterministic
state and cleanup behavior; `manual_pending` is not promoted by simulated or headless
runs.

| State/transition | Required invariant | Automated evidence | Status |
| --- | --- | --- | --- |
| Activity missing or malformed | Missing, `None`, malformed, or bounded provider output is safe and cannot crash Tk. | `tests/test_taskdb_monitoring.py` activity snapshot/provider regressions; `tests/test_v2_flows.py` provider-boundary tests. | automated; live provider manual_pending |
| Activity provider error | Provider exception produces unusable activity and cannot trigger a website intervention. | `test_activity_provider_error_is_not_usable_for_website_intervention`. | automated |
| Stale activity | Stale capture is visible as unusable metadata and cannot trigger a website intervention. | `test_stale_activity_is_not_usable_for_website_intervention`. | automated |
| No enabled flags | Provider polling is not performed and no subpopup is created. | `test_disabled_website_flags_do_not_query_activity_provider`; settings-update cancellation tests. | automated |
| Manual/effective pause, snooze, guard, shutdown | Website polling and intervention eligibility are suppressed by the canonical runtime state. | `test_subpopup_gate_covers_runtime_pause_and_lifecycle_matrix`; standalone suppression matrix tests. | automated; live lock/sleep manual_pending |
| Active prompt/intervention | Website polling remains cancelled until the owning lease is released and all other gates allow resume. | Prompt/intervention transition and no-resume-while-active tests. | automated |
| Severity-2 match | A matching trusted activity opens exactly one owned warning dialog. | `test_active_window_flag_triggers_severity_two_subpopup_with_fake_activity`. | automated; visible UI manual_pending |
| Severity-2 dismissal | Normal dismissal starts cooldown; configured `allow_once` is consumed without starting cooldown. | Cooldown boundary and allow-once persistence tests. | automated |
| Severity-3 high-confidence match | Immediate intervention routes through the App-owned intervention lease and records cooldown only after success. | `test_active_window_flag_triggers_severity_three_intervention`; App intervention lease tests. | automated; overlay/manual browser evidence pending |
| Severity-3 low-confidence match | Title-only or otherwise low-confidence evidence cannot trigger an aggressive intervention. | `test_severity_three_title_only_activity_does_not_intervene`; confidence/provider tests. | automated |
| Intervention cancellation/failure | Cancellation or failure releases the intervention lease, restores prompt state, and does not start cooldown. | `test_cancelled_intervention_does_not_start_cooldown`; wizard failure/cleanup tests. | automated; visible restoration manual_pending |
| Subpopup construction failure | Active latch and dialog ownership are cleared on construction failure. | `test_subpopup_construction_failure_releases_active_latch`. | automated |
| Shutdown during warning | Owned warning is destroyed, timers close, and no later callback can reopen it. | `test_subpopup_shutdown_closes_owned_dialog`; timer-generation tests. | automated; live shutdown manual_pending |
| Duplicate/stale completion | A closed generation cannot mutate current state or write a second outcome. | Prompt coordinator outcome/idempotency tests and generation-owned timer tests. | automated |

## Exit Gate

The automated rows must remain green in the full verifier. The manual-pending rows
require target Windows/browser/overlay execution and must be recorded through
`docs/refurbishment/manual-evidence.json` with human confirmation.
