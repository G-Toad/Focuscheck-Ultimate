# Timer, Thread, and Native Resource Map

| Resource | Creation | Cancellation/release | Evidence |
| --- | --- | --- | --- |
| Named EngineV2 timers | `TimerRegistry.schedule` | generation-aware `cancel`/`close` | runtime-foundation tests; verification runner |
| Main prompt timer | `App._schedule_next` / `TimerRegistry` | named replacement and generation cancellation. | unit tests |
| Snooze expiry timer | `App._tray_snooze` | `_cancel_snooze`. | unit tests |
| V2 subpopup timer | `EngineV2._schedule_subpopup_check` | `EngineV2.shutdown`. | unit tests/QA |
| Tk dialog timers | dialog cleanup methods | dialog close/destructor paths. | keyboard tests; manual UI pending |
| Supervisor child process | `subprocess.Popen` | process-tree termination. | fake supervisor harness |
| Structured heartbeat | `App._write_heartbeat` | supervisor validates protocol/generation/PID/freshness. | heartbeat protocol tests |
| Windows hooks/tray | platform modules | explicit close methods. | self-test; manual Windows pending |
| Camera/overlay handles | dialog/window implementations | exception cleanup paths. | imports and QA; native manual pending |
