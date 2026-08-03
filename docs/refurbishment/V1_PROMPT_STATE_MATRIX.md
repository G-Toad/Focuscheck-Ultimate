# V1 Prompt State Matrix

This matrix is the V1 prompt acceptance contract. `automated` identifies deterministic
unit or QA coverage; `manual_pending` requires an interactive Windows run and must not
be promoted to a pass from simulated evidence.

| State/transition | Required invariant | Automated evidence | Status |
| --- | --- | --- | --- |
| Initial prompt visible | Exactly one prompt generation owns the dialog and its timers. | `PromptCoordinator` lifecycle tests; resource-leak self-test. | automated; visible UI manual_pending |
| Studying response | A valid studying choice reaches one completion callback and one focus-log attempt. | `test_v1_prompt_notifies_owner_after_studying_choice`; `test_v1_focus_and_waste_detail_flows_complete_through_parent`; prompt finalization tests. | automated; full detail flow manual_pending |
| Wasting-time response | A valid wasting choice reaches one completion callback and one waste-log attempt. | `test_v1_focus_and_waste_detail_flows_complete_through_parent`; QA scenario and CSV logging tests. | automated; full detail flow manual_pending |
| Required active task | Missing required task blocks completion and routes to task entry instead of closing silently. | Task-management and prompt eligibility tests. | automated; interactive validation manual_pending |
| Task create/change/complete/fail | Task transitions preserve the one-active-task invariant and record auditable outcomes. | TaskDB lifecycle, deadline, and task-dialog tests. | automated; full UI flow manual_pending |
| Focus detail enabled/disabled | Disabled detail skips its child dialog; enabled detail validates and returns to the owning prompt path; interruption closes the child and resets the owning prompt state; initial-focus work is owned and cancelled with dialog destruction. | `test_v1_focus_and_waste_detail_flows_complete_through_parent`; `test_v1_detail_dialogs_close_with_parent_interruption`; `gui.v1.detail_completion_and_interruption` in `qa_scenario_runner.py`; dialog callback/failure-isolation tests; `test_focus_detail_rejects_failed_challenge_without_submitting`; `test_focus_detail_rejects_failed_spam_validation_without_submitting`; `test_focus_and_waste_dialogs_own_initial_focus_timer`; withdrawn-root Tk `resource_leak_selftest`. | partial; enabled interactive flow manual_pending |
| Waste detail enabled/disabled | Disabled detail skips its child dialog; enabled detail validates and returns to the owning prompt path; interruption closes the child and resets the owning prompt state; initial-focus work is owned and cancelled with dialog destruction. | `test_v1_focus_and_waste_detail_flows_complete_through_parent`; `test_v1_detail_dialogs_close_with_parent_interruption`; `gui.v1.detail_completion_and_interruption` in `qa_scenario_runner.py`; dialog callback/failure-isolation tests; `test_focus_and_waste_dialogs_own_initial_focus_timer`; withdrawn-root Tk `resource_leak_selftest`. | partial; enabled interactive flow manual_pending |
| Challenge enabled/disabled | Challenge cancellation or validation failure does not claim a successful prompt completion; interruption closes the acronym child without completing the prompt. | Phrase/challenge timer and callback cleanup tests; `test_v1_acronym_dialog_closes_with_parent_interruption`. | partial; complete challenge matrix manual_pending |
| Spam validation enabled/disabled | Disabled spam checks do not reject responses; enabled checks use the configured policy. | Settings coercion and spam policy tests; QA scenario. | automated; interactive response matrix manual_pending |
| Intensification stages | Intensity and overdrive state are bounded, timer-owned, and reset on completion or interruption. | Intensification signature/lifecycle and prompt cleanup tests. | automated; visual timing manual_pending |
| Overdrive stage 4 | Flash/shake timers remain cancellable and cannot resurrect after close. | Timer registry and cleanup regressions. | automated; visual/manual Windows pending |
| Overdrive stage 5 | Overlay failure falls back safely; shutdown/close releases every owned overlay. | Native overlay self-test and fake-DLL cleanup tests. | automated; multi-monitor/DPI manual_pending |
| Camera enabled/disabled | Disabled or unavailable camera never blocks completion; captured data is opt-in and canonical-root bound. | Camera capability, missing-dependency, failed-encode, and callback-generation tests. | automated; hardware manual_pending |
| Pause/settings interruption | Open V1 prompt cleans up before pause or settings regeneration and cannot leave an orphan dialog. | App lifecycle, prompt regeneration, and lock/sleep simulation tests. | automated; live interruption manual_pending |
| Shutdown/close interruption | Close attempts do not claim success; committed shutdown performs idempotent cleanup. | Lifecycle and prompt close/failure-isolation tests. | automated; live tray/shutdown manual_pending |

## Exit Gate

The V1 matrix is complete only when every row has a passing automated or manual
evidence reference, the manual-only rows are executed on the target Windows machine,
and the full verifier is rerun at the final commit.
