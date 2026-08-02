Version 2 Browser Data Notes

Current data sources (Windows 10):
- Baseline (all browsers): foreground window title + process name (via Win32 APIs).
- Optional URL (best effort): UI Automation address-bar scraping using comtypes if available.
- Optional URL/Tabs (best effort): CDP discovery if a Chromium browser is already running with remote debugging enabled.

Supported browsers (best effort):
- Chromium: Chrome, Edge, Brave, Opera, Opera GX.
- Firefox: address bar scraping attempted when UIA is available.

How it works:
- `platform_specific/activity_probe.py` collects HWND, title, process, and class.
- `platform_specific/browser_info.py` tries UI Automation to read the address bar value.
- If UIA is unavailable or fails, URL is None and only title/process are used.

Limitations:
- UIA requires comtypes to be installed. If missing, URL extraction is skipped.
- Some browser windows may block UIA or expose non-standard address-bar controls.
- Titles often reflect page titles (not URLs), so domain inference can be incomplete.
- Tab listing uses UIA TabItem controls; it is best effort and may miss tabs on some builds.
- CDP requires an existing remote-debugging port (no registry edits; only works if browser was launched with it).

Upgrade paths:
- Add DevTools Protocol support for Chromium (without registry edits) for reliable URLs and tab lists.
- Add a lightweight UIA element cache to reduce overhead on frequent polls.
