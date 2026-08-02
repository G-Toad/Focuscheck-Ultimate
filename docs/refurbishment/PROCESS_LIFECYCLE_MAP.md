# Process Lifecycle Map

1. Launcher starts the supervisor.
2. Supervisor acquires an atomic lock and launches `main.py`.
3. App loads/migrates settings, initializes TaskDB, starts one App-owned heartbeat, tray, guard, and engine.
4. App transitions pause/snooze/prompt/intervention state on the Tk owner thread.
5. App writes an intentional-stop marker before supervised exit.
6. Supervisor distinguishes intentional exit, crash, stale/malformed heartbeat, and shutdown.
7. Unexpected exits use bounded backoff; unrelated system processes are never terminated.
