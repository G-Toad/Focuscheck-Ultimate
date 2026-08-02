# FocusCheck Supervisor

`focuscheck_supervisor.py` keeps `main.py` alive, restarts it whenever it dies, and can drop a launcher into the Windows **Startup** folder so it boots with your profile. The watchdog also watches for long pauses (sleep/hibernate/Win+L) and cycles FocusCheck once the machine wakes back up, which avoids the crashes you were seeing after power transitions.

## Usage

```
python focuscheck_supervisor.py --run
```

- Run the command above from this repo once to test it. A foreground console run logs to `%LOCALAPPDATA%\FocusCheck\focuscheck_supervisor.log`.
- Press `Ctrl+C` to stop the supervisor; it will tear down the FocusCheck child cleanly.
- Use optional knobs:
  - `--check-interval` (seconds, default 10) – how often the watcher checks the child.
  - `--resume-gap` (seconds, default 90) – if the loop stalls longer than this (sleep/hibernate/unlock), the supervisor restarts FocusCheck.
  - `--restart-delay` (seconds, default 5) – base delay before restarting after a crash. The delay backs off when repeated failures happen.

## Auto-start

```
python focuscheck_supervisor.py --install-startup
```

- The command above creates `RunFocusCheckSupervisor.cmd` inside `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.
- The `.cmd` fires `pythonw.exe` so no console window stays open. Remove it any time via `--uninstall-startup`.
- Because the supervisor stays alive through suspend/hibernate, FocusCheck is relaunched whenever the box wakes up even if the original instance crashed on resume.

## Manual stop / cleanup

```
python focuscheck_supervisor.py --uninstall-startup
```

- Removes the startup launcher.
- Logs live under `%LOCALAPPDATA%\FocusCheck\focuscheck_supervisor.log` with a `.bak` rotation.
- If you need to inspect the child directly, open **Task Manager** and look for a `pythonw.exe` owned by `focuscheck_supervisor.py`. Killing the supervisor will automatically terminate and relaunch FocusCheck, so prefer `--uninstall-startup` first.
