# Ownership Map

| Resource/state | Owner | Shutdown/recovery |
| --- | --- | --- |
| Tk root and callbacks | `App` | `_quit` destroys root after component cleanup. |
| Prompt instance | `App` plus prompt lifecycle methods | `_close`/cleanup is idempotent. |
| Next-prompt timer and prompt observers | `PromptScheduler` through `TimerRegistry` | named prompt/observer jobs are replaced or cancelled during prompt completion and shutdown. |
| V2 subpopup timer | `EngineV2` | `shutdown` cancels timer. |
| Intervention wizard/selection/overlay timers | `InterventionWizard`, `WindowSelectionDialog`, `SpotlightOverlay` | local registries close recurring callbacks before Tk/native destruction. |
| Intervention lease and identity | `InterventionOrchestrator` | releases runtime lease, restores hidden prompt, clears identity, and notifies engine in `finally`. |
| Settings persistence | `settings.manager` | process lock, temp file, backup, quarantine. |
| Task SQLite connection | `TaskDB` | context-managed connection per operation. |
| Data export/inventory/clear/retention/diagnostics | `DataControlService` | allowlisted utility operations return bounded durability/error results; App owns confirmation and Tk dispatch. |
| Health/status projection | `HealthSnapshotService` | read-only bounded payload; App-owned status window remains responsible for Tk destruction. |
| Startup registration | `StartupService` | canonical Run-key inspection/install/uninstall; App owns confirmation and dispatch, platform adapter owns registry handles. |
| Supervisor child | `FocusCheckSupervisor` | terminate/kill tree on shutdown. |
| Supervisor lock/stop files | `SupervisorLock` / supervisor | process-start-token ownership, stale-lock recovery, and generation-bound intentional-stop cleanup. |
| Canonical runtime paths | immutable `AppPaths` | selected once per data root; legacy selection remains migration-only. |
| Pause/snooze/runtime leases | `RuntimeStateCoordinator` | transactional persistence; prompt/intervention/shutdown lease methods. |
| Heartbeat payload/publication | `HeartbeatService` | App retains the compatibility delegate; atomic writes and bounded failure telemetry are isolated, while the supervisor treats stale/malformed heartbeat as unhealthy. |
| Guard sampling and pause-edge timer | `GuardMonitorService` | Samples `PauseGuard` once per interval, publishes `system_guard`, notifies the engine on effective-pause changes, and is cancelled by the App-owned `TimerRegistry` during shutdown. |
