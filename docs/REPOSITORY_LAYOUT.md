# Repository Layout

The active FocusCheck project is the Python desktop app at the repository root.

## Active Runtime

- `main.py` starts the app, handles CLI selftests, startup install/uninstall flags, and heartbeat writing.
- `focuscheck_supervisor.py` keeps `main.py` alive and can install/remove a Windows startup command.
- `focuscheck/` contains the app package:
  - `app.py` coordinates Tk, monitoring, tray, dialogs, tasks, settings, and scheduling.
  - `monitoring/` contains v1 and v2 monitoring engines.
  - `ui/` contains settings windows, dialogs, prompt flows, camera UI, and modern widgets.
  - `settings/` contains defaults, validation, registry metadata, and feature gates.
  - `platform_specific/` contains Windows integration, startup registration, browser/window probes, and icon extraction.
  - `database/` contains SQLite/CSV task and history persistence.
  - `utils/` contains paths, logging, audio, file, and UI helpers.

## Supporting Material

- `tests/` contains automated test scripts.
- `tools/` contains manual diagnostic/selftest tools, including interactive UI smoke tests.
- `docs/` contains planning, browser-data notes, settings notes, supervisor docs, and manual repro checklists.
- `docs/SOFTWARE_MAP.md` maps runtime phases, UI/backend states, and functional ownership.
- `docs/specs/` contains preserved raw product/spec input.
- `ports/csharp-wpf/` contains the experimental WPF port.
- `ports/ios/` contains the iOS prototype/reference implementation.
- `_archive/` contains material intentionally excluded from active runtime:
  - `scratch/` for temporary files.
  - `legacy/` for old archived trees and exploratory code.
  - `analysis/` for generated Codex/analysis output.
  - `reference/` for reference dumps.
  - `packages/` for copied zip packages.
  - `generated/` for caches or generated output.

## Root Rules

- Keep launchers, `main.py`, `focuscheck_supervisor.py`, `README.md`, dependency files, and active package folders at root.
- Do not put prompts, generated logs, zip exports, cache folders, or exploratory copies at root.
- If an archived implementation becomes active again, move only the required files back into an active folder and update this document.
