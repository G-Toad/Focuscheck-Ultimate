# Ownership Map

| Resource/state | Owner | Shutdown/recovery |
| --- | --- | --- |
| Tk root and callbacks | `App` | `_quit` destroys root after component cleanup. |
| Prompt instance | `App` plus prompt lifecycle methods | `_close`/cleanup is idempotent. |
| V2 subpopup timer | `EngineV2` | `shutdown` cancels timer. |
| Intervention wizard/overlay | `InterventionWizard` | wizard cleanup and cancellation path. |
| Settings persistence | `settings.manager` | process lock, temp file, backup, quarantine. |
| Task SQLite connection | `TaskDB` | context-managed connection per operation. |
| Supervisor child | `FocusCheckSupervisor` | terminate/kill tree on shutdown. |
| Supervisor lock/stop files | `SupervisorLock` / supervisor | stale-lock recovery and intentional-stop cleanup. |
| Heartbeat | `App._start_file_heartbeat` | supervisor treats stale/malformed heartbeat as unhealthy. |
