# Test Matrix

This matrix maps important behaviour to automated evidence and remaining manual checks.

| Area | Behaviour | Automated Evidence | Manual Windows Evidence |
| --- | --- | --- | --- |
| Supervisor | Duplicate supervisor lock rejects second loop | `SupervisorLifecycleTests` | Start a second supervisor and confirm no extra child |
| Supervisor | Intentional tray/app exit does not restart | `SupervisorHarnessTests`, `AppLifecycleTests`, `test_app_quit_writes_supervisor_stop_request`, `qa_scenario_runner` | Exit from tray while supervised and watch process list/log |
| Supervisor | Unexpected child exit restarts | `SupervisorHarnessTests`, `qa_scenario_runner` | Kill child process and confirm restart |
| Startup | Run key and startup script target supervisor; legacy command remains direct child launch | `StartupCommandTests`, `LaunchScriptContractTests` | Inspect Current User Run key |
| Startup | Startup uninstall removes entry | `StartupCommandTests` mocked registry install/uninstall/query tests | Enable/disable from tray and inspect Run key |
| Main app | Non-Windows API setup does not crash import | Compile/import/selftest | Not required |
| Settings | Missing/malformed/default normalization, Stage 5 clamps, save payload clamps, and representative tab round-trips | Existing settings tests, `SettingsWindowSaveTests`, and QA harness | Save Settings once in live UI |
| Settings | Webhook remains hidden while gentle-reminder settings round-trip through the generated Advanced tab | Settings truth table, `SettingsWindowSaveTests`, lifecycle tests | Confirm webhook is not exposed; enable gentle reminder and verify scheduler/close behavior |
| Pause/snooze | Snooze fields and disabled validation paths | `test_dialog_keyboard`, QA harness | Snooze from tray and prompt |
| Prompt | Prompt completion idempotency and intervention-active deferral | Existing V2 flow tests and QA harness app presenter scenario | Prompt Now and answer V1/V2 |
| V2 intervention | Exception/cancel resets app state | `tests/test_v2_flows.py` | Trigger, cancel at selection and spotlight |
| V2 intervention | Wizard gets settings source | EngineV2 matching test and V2 flow tests | Trigger V2 intervention after launch |
| Website flags | Exact/subdomain/cooldown/suffix rules and fake active-browser flow | `EngineV2MatchingTests`, QA harness fake activity scenario | Browser matrix with supported browsers |
| Tray | Menu gates reflect settings; command handlers delegate safely; exit dispatch respects disabled gate | QA harness, gates tests, `SystemTrayCommandTests`, `AppLifecycleTests` | Toggle each tray setting and inspect menu |
| Dialogs | Keyboard and close behaviour, including V2 sub-popup Enter/Escape outcomes | `tests/test_dialog_keyboard.py`, compile checks | Manual tab through Settings and dialogs |
| Camera | Missing dependency fallback | Existing import/QA checks | Open preview on target machine |
| CSV/TaskDB | Persistence lifecycle and shared task payload construction | `tests/test_taskdb_monitoring.py` | Create/change/complete task in UI |

## Required Verification Entry Point

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify.ps1
```

## Harness Gaps To Close

- QA report lists manual-only Windows gates so automation is not mistaken for full runtime proof.
- Live shell tray exit remains manual-only; fake app callback coverage exists.
- Native workstation lock/unlock notification remains manual-only; fake app guard hooks are covered.
- Native sleep/resume watchdog gap remains manual-only; fake app guard hooks are covered.
- Broader fake dialog presenter remains future work; intervention-active prompt deferral and V2 sub-popup Enter/Escape outcomes are covered.
- Real browser/activity provider matrix remains manual-only; fake activity-provider coverage exists.
- Full exhaustive settings round-trip snapshots for every active control; representative tabs and Stage 5 clamps are covered.
- Slice-level closeout status is tracked in `docs/SLICE_COMPLETION_STATUS.md`.
