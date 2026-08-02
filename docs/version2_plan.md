# FocusCheck Version 2 Architecture Plan

## Goals
- Add a mode toggle so the user can switch between Version 1 (existing prompt flow) and Version 2 (activity-aware prompts + interventions).
- Keep the unified UI shell intact (history, tasks, settings, camera, bio features) regardless of mode.
- Layer Version 2 specific capabilities: Windows activity probe, browser data collectors, new popup/intervention UX, sub-popup triggers, and website flag management.

## Proposed Architecture

### Mode Toggle + Monitoring Engines
- Introduce `focuscheck.monitoring` package containing:
  - `BaseEngine` protocol: start(), stop(), on_settings_changed(), tick()/handle_event hooks.
  - `EngineV1`: wraps the existing scheduling + PromptDialog pipeline. Implementation begins by moving the current `_schedule_next`, `_maybe_show_prompt`, `_on_prompt_done` logic into this class.
  - `EngineV2`: new activity-aware engine.
- App bootstrapping:
  - App remains owner of Tk root, windows hooks, tray, etc.
  - App instantiates the engine selected in settings (`settings.get("monitoring_mode", "v1")`).
  - App forwards lifecycle events to the engine (resume, pause, manual snooze toggles, etc.).
  - Both engines write events through the same history/task subsystems.

### Data Providers
- `focuscheck.activity` package containing:
  - `activity_probe.py`: wraps Win32 APIs (`GetForegroundWindow`, `GetWindowThreadProcessId`, `GetWindowText`, `GetClassName`, `GetWindowPlacement`). Tracks active handle + timestamps to compute "foreground duration".
  - `process_utils.py`: resolves PID → executable path, friendly app name, icon extraction (via `LoadIcon`, `ExtractIconEx`).
  - `browser_data.py`: per browser collectors that can parse session/profile files when available.

#### Browser Data Strategy
1. Baseline: always supply window title + process name.
2. Chromium collectors:
   - Locate profile directories for Chrome, Edge, Brave, Opera.
   - Copy `Current Tabs`/`Current Session` files to temp dir and parse Chromium `SessionWindow/SessionTab` protobufs to get selected tab URL/title.
   - Provide fallback if parsing fails.
3. Firefox collector:
   - Copy `%APPDATA%\Mozilla\Firefox\Profiles\<profile>\sessionstore-backups\recovery.jsonlz4`.
   - Decompress and parse JSON to retrieve selected tab per window.
4. Module returns `BrowserActivity` objects (window handle, window id, tab list, active tab metadata, timestamp of last refresh).
5. Activity probe merges UI info + best-effort browser metadata for the popup.

### Version 2 Popup Flow
- Build new dialog (e.g., `ActivityAwarePromptDialog`) living under `focuscheck.ui.dialogs.version2_prompt`.
- Layout sections:
  1. Activity info box: shows icon, app name/title, active duration.
  2. Question 1: "What are you doing on <APP_NAME>?" + text input using existing validation mixins.
  3. Question 2: yes/no input for intervention.
- Validation integrates with the same heuristics module. Settings add flag "Version 2 uses all validation rules".
- The engine runs a 60s loop: gather activity snapshot → show dialog → handle answer.

### Intervention Workflow
- Lives in `focuscheck.ui.dialogs.intervention`. Steps:
  1. **Selection wizard**: overlay (full-screen Toplevel) listing windows/tabs. Need backend module that enumerates top-level windows + optionally tabs from browser_data. Users select entries.
  2. **Action overlay**: darken entire screen (transparent fullscreen window) + create circular clipping/spotlight around cursor. Provide instructions + option to auto-close windows/tabs programmatically (using `PostMessage(WM_CLOSE)` or DevTools for tabs). Fallback relies on user closing manually while overlay stays up.
  3. **Verification**: confirm closures (check handles still exist / tabs still reported). If success, remove overlay and log intervention.
- The workflow returns status to EngineV2; engine restarts timer once complete.

### Sub-Popup System
- Always-on watcher inside EngineV2 monitors activity snapshots (activity probe publishes events when active domain changes).
- Settings include Website Flags list with severity/cooldown parameters stored in JSON-like structure inside settings file.
- When active domain matches a flagged entry, trigger overlay/popup immediately regardless of 1-minute cycle.
- Severity levels:
  1. Warning only → show overlay, allow dismissal.
  2. Warning + ask intervention → same prompt as main Q2.
  3. Immediate intervention → directly open intervention workflow with current tab/window preselected.
- Cooldown timestamp stored per site to avoid repeated prompts.

### Settings Updates
- General tab: add radio buttons or dropdown for "Prompt Mode" (Version 1 vs Version 2). Toggling saves `monitoring_mode`.
- Validation tab: add checkbox "Version 2 enforces all validation rules".
- New Website Flags tab/section: table-style editor (listbox + add/edit/remove) storing entries like `{ "domain": "reddit.com", "enabled": true, "severity": 3, "cooldown_minutes": 5 }` plus optional "allow once" state.

### Feature Parity Strategy
- Camera, bio, tasks, history remain untouched because they belong to UI shell and PromptDialog mixins reused by Version 2 question 1 (via shared validation component).
- Both engines continue to record history entries using existing database/log helpers so the History view stays populated.

### Technical Write-Up Placeholder
- Add `docs/version2_browser_data.md` later summarizing actual data per browser, stating parsing approach and limitations.

## Implementation Phases
1. **Scaffolding**
   - Create monitoring package + BaseEngine interface.
   - Move current scheduling logic into EngineV1 with zero behavior change.
   - Wire App to use new engines.
   - Add General tab toggle + settings plumbing.
2. **Version 2 Core Loop**
   - Implement activity probe + baseline popup UI (without interventions yet).
   - Ensure validation integration + basic yes/no handling.
3. **Interventions + Overlays**
   - Window/tab selection, blackout overlay, closure verification.
4. **Sub-Popups + Website Flags**
   - Settings UI for flagged sites, runtime triggering, cooldown handling.
5. **Browser data modules** (Chromium parsers, Firefox recovery parser) + documentation.
6. **Polish + Testing**
   - End-to-end testing, history/task parity verification, README write-up.

## Next Steps
- Implement scaffolding (Phase 1) to unlock further work.
- Begin coding BaseEngine + EngineV1 wrapper.
- Extend settings defaults/schema for `monitoring_mode`, `v2_force_all_validations`, `website_flags`.
