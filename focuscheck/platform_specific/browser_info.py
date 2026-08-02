"""Best-effort browser URL extraction for Windows."""

import platform


_CHROMIUM_PROCESSES = {
    "chrome.exe",
    "msedge.exe",
    "brave.exe",
    "opera.exe",
    "opera_gx.exe",
}
_FIREFOX_PROCESSES = {"firefox.exe"}


def try_get_browser_url(hwnd, process_name):
    """Return a best-effort URL for supported browsers, otherwise None."""
    if platform.system().lower() != "windows":
        return None
    proc = (process_name or "").lower()
    if proc in _CHROMIUM_PROCESSES or proc in _FIREFOX_PROCESSES:
        return _try_uia_address_bar(hwnd)
    return None


def is_supported_browser(process_name):
    proc = (process_name or "").lower()
    return proc in _CHROMIUM_PROCESSES or proc in _FIREFOX_PROCESSES


def _try_uia_address_bar(hwnd):
    """Best-effort UIA address bar extraction using comtypes if available."""
    try:
        import comtypes.client  # type: ignore
        try:
            from comtypes.gen import UIAutomationClient as UIA  # type: ignore
        except Exception:
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient as UIA  # type: ignore
    except Exception:
        return None

    try:
        uia = comtypes.client.CreateObject("UIAutomationClient.CUIAutomation")
        root = uia.ElementFromHandle(int(hwnd))
        cond = uia.CreatePropertyCondition(UIA.UIA_ControlTypePropertyId, UIA.UIA_EditControlTypeId)
        elements = root.FindAll(UIA.TreeScope_Subtree, cond)
        if elements is None:
            return None
        # Pass 1: prioritize address-bar labeled edits
        for i in range(elements.Length):
            el = elements.GetElement(i)
            name = (el.CurrentName or "").lower()
            auto_id = (el.CurrentAutomationId or "").lower()
            if "address" in name or "address" in auto_id or "omnibox" in auto_id:
                value = _get_value_pattern(el, UIA)
                if value:
                    return value
        # Pass 2: any edit containing a URL-like value
        for i in range(elements.Length):
            el = elements.GetElement(i)
            value = _get_value_pattern(el, UIA)
            if value and ("://" in value or value.startswith("www.")):
                return value
    except Exception:
        return None
    return None


def _get_value_pattern(el, UIA):
    try:
        pattern = el.GetCurrentPattern(UIA.UIA_ValuePatternId)
        if pattern is None:
            return None
        value_pattern = pattern.QueryInterface(UIA.IUIAutomationValuePattern)
        value = value_pattern.CurrentValue
        if value:
            return str(value)
    except Exception:
        return None
    return None


__all__ = ["try_get_browser_url", "is_supported_browser"]
