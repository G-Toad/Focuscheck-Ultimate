# Manual Windows Evidence

Current status: `NOT RUN`.

Required on a disposable Windows profile:

- supervisor launch, duplicate supervisor, child crash/restart, intentional tray exit;
- startup Run-key install/uninstall and path correctness;
- real tray menu, Tk prompt keyboard/close behavior, settings save/reload;
- lock, sleep, resume, idle, browser/window activity, and supported browser flags;
- spotlight/blackout/multi-monitor overlay cleanup and DPI behavior;
- camera dependency fallback and native resource cleanup;
- install, upgrade, repair, uninstall, and rollback.

No item above is claimed as manually verified by the current automated run.

## Recording Results

Inspect the checklist without changing it:

```powershell
py -3 tools\manual_evidence.py list
py -3 tools\manual_evidence.py validate
```

After executing a case on the target machine, record it atomically. Passing or failing requires explicit human confirmation; automated or simulated runs must remain `not_run`:

```powershell
py -3 tools\manual_evidence.py record --case WIN-001 --outcome pass --human-confirmed --tester "Name" --machine "Machine" --observed "Observed result" --screenshot "evidence\win-001.png"
```
