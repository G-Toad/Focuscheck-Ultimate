# Process Lifecycle Map

1. Launcher starts the supervisor.
2. Supervisor acquires an atomic lock and launches `main.py`.
3. App enters `starting`, loads/migrates settings, initializes TaskDB, starts one App-owned heartbeat, tray, guard, and engine, then enters `ready`.
4. App transitions pause/snooze/prompt/intervention state on the Tk owner thread; lifecycle phase is included in heartbeat metadata.
5. App enters `stopping`, atomically writes a nonce- and generation-bound intentional-stop request, and flushes owned resources before supervised exit.
6. Supervisor distinguishes intentional exit, crash, stale/malformed heartbeat, and shutdown; a child exception is represented as `failed` rather than a clean exit.
7. Cleanup enters `stopped`; unexpected exits use bounded backoff; unrelated system processes are never terminated.
