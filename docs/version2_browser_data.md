Version 2 Browser Data Notes

Current data sources (Windows 10):
- Baseline (all browsers): foreground window title + process name (via Win32 APIs).
- Optional URL (best effort): UI Automation address-bar scraping using comtypes if available.
- Optional URL/Tabs (best effort): CDP discovery if a Chromium browser is already running with remote debugging enabled.
- Optional recovered tabs (read-only last resort): Chromium session URL extraction and Firefox `recovery.jsonlz4` selected-entry parsing.

Supported browsers (best effort):
- Chromium: Chrome, Edge, Brave, Opera, Opera GX.
- Firefox: address bar scraping attempted when UIA is available.

How it works:
- `platform_specific/activity_probe.py` collects HWND, title, process, and class.
- `platform_specific/browser_info.py` tries UI Automation to read the address bar value.
- `platform_specific/browser_tabs.py` falls back from bounded UIA to CDP and then to `browser_sessions.py`.
- `platform_specific/browser_sessions.py` reads bounded copies of browser session files without modifying profiles.
- Recovered session tabs are exposed to the intervention selection wizard only; they are never treated as proof of the foreground window or active tab.

Limitations:
- UIA requires comtypes to be installed. If missing, URL extraction is skipped.
- Some browser windows may block UIA or expose non-standard address-bar controls.
- Titles often reflect page titles (not URLs), so domain inference can be incomplete.
- Tab listing uses UIA TabItem controls; it is best effort and may miss tabs on some builds.
- CDP requires an existing remote-debugging port (no registry edits; only works if browser was launched with it).
- Chromium session files are versioned protobuf streams, so the offline fallback extracts only valid HTTP(S) URL strings and cannot reliably assign active-window or title metadata.
- Firefox recovery parsing uses the selected entry per recovered window, but recovery files can be stale or absent while Firefox is running.

Upgrade paths:
- Continue preferring CDP/UIA for live foreground identity; session recovery is intentionally non-authoritative.
- Add a schema-versioned Chromium protobuf decoder only if a future requirement needs exact offline window/tab reconstruction.
