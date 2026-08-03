"""Best-effort browser tab listing using bounded UI Automation on Windows."""

import platform
import threading

from .browser_info import is_supported_browser
from .browser_sessions import collect_browser_tabs
from .cdp_browser import list_tab_titles

_MAX_UIA_ITEMS = 256
_MAX_TAB_TITLE_LENGTH = 2048
_DEFAULT_UIA_TIMEOUT = 0.5
_UIA_STATE_LOCK = threading.Lock()
_UIA_IN_FLIGHT = False


def _list_uia_tabs(hwnd):
    """Read UIA tab titles; callers must bound this COM operation."""
    import comtypes.client  # type: ignore

    try:
        from comtypes.gen import UIAutomationClient as UIA  # type: ignore
    except Exception:
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen import UIAutomationClient as UIA  # type: ignore
    uia = comtypes.client.CreateObject("UIAutomationClient.CUIAutomation")
    root = uia.ElementFromHandle(int(hwnd))
    cond = uia.CreatePropertyCondition(UIA.UIA_ControlTypePropertyId, UIA.UIA_TabItemControlTypeId)
    items = root.FindAll(UIA.TreeScope_Subtree, cond)
    if items is None:
        return []
    titles = []
    for i in range(min(int(items.Length), _MAX_UIA_ITEMS)):
        el = items.GetElement(i)
        name = str(el.CurrentName or "").strip()[:_MAX_TAB_TITLE_LENGTH]
        if name:
            titles.append(name)
    seen = set()
    return [title for title in titles if not (title in seen or seen.add(title))]


def _bounded_uia_tabs(hwnd, timeout):
    """Run one UIA call at a time so a hung COM server cannot pile up workers."""
    global _UIA_IN_FLIGHT
    with _UIA_STATE_LOCK:
        if _UIA_IN_FLIGHT:
            return None
        _UIA_IN_FLIGHT = True
    result = []
    finished = threading.Event()

    def worker():
        global _UIA_IN_FLIGHT
        try:
            result.extend(_list_uia_tabs(hwnd))
        except Exception:
            pass
        finally:
            with _UIA_STATE_LOCK:
                _UIA_IN_FLIGHT = False
            finished.set()

    threading.Thread(target=worker, name="FocusCheck-UIA", daemon=True).start()
    if not finished.wait(max(0.01, float(timeout))):
        return None
    return result


def try_list_browser_tabs(hwnd, process_name, *, timeout=_DEFAULT_UIA_TIMEOUT):
    """Return browser tab titles without allowing UIA COM to block the caller."""
    if platform.system().lower() != "windows":
        return []
    if not is_supported_browser(process_name):
        return []
    # Try UIA first for per-window accuracy (includes incognito windows when accessible)
    uia_titles = _bounded_uia_tabs(hwnd, timeout)
    if uia_titles:
        return uia_titles
    # Fallback: CDP (not window-specific but can capture more tabs)
    try:
        titles = list_tab_titles()
        if titles:
            return titles
    except Exception:
        pass
    # Session files are a read-only last resort. They do not identify the
    # foreground window, so expose titles only to the selection wizard.
    try:
        recovered = collect_browser_tabs(process_name)
        if recovered:
            return [tab.title or tab.url for tab in recovered if tab.title or tab.url]
    except Exception:
        pass
    return []


__all__ = ["try_list_browser_tabs"]
