# Contradiction Register

| ID | Contradiction | Decision | Evidence | Status |
| --- | --- | --- | --- | --- |
| CONTR-001 | Normal supervised startup forced `FOCUSCHECK_FORCE_STARTED=1`, overriding persisted manual pause. | Normal supervision preserves pause; force-start is explicit only through `--force-start`. | `resolve_initial_monitoring_state`, launcher contract, QA, and supervisor forwarding tests. | fixed |
| CONTR-002 | `main.py` and `App` wrote different heartbeat files. | `App` owns one JSON `hb.txt` protocol consumed by the supervisor. | `paths.py`, `app.py`, supervisor heartbeat parser. | fixed |
| CONTR-003 | Existing finish docs described automated completion while the V1 plan requires native/manual evidence. | Automated, simulated, and manual evidence are separate labels. | refurbishment state and manual evidence files. | documented |
