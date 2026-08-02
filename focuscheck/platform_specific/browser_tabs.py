"""Best-effort browser tab listing using UI Automation on Windows."""

import platform

from .browser_info import is_supported_browser
from .cdp_browser import list_tab_titles


def try_list_browser_tabs(hwnd, process_name):
    """Return a list of tab titles for a browser window, best effort."""
    if platform.system().lower() != "windows":
        return []
    if not is_supported_browser(process_name):
        return []
    # Try UIA first for per-window accuracy (includes incognito windows when accessible)
    try:
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
        if items is not None:
            titles = []
            for i in range(items.Length):
                el = items.GetElement(i)
                name = (el.CurrentName or "").strip()
                if not name:
                    continue
                titles.append(name)
            if titles:
                # De-dup while preserving order
                seen = set()
                unique = []
                for title in titles:
                    if title in seen:
                        continue
                    seen.add(title)
                    unique.append(title)
                return unique
    except Exception:
        pass
    # Fallback: CDP (not window-specific but can capture more tabs)
    try:
        titles = list_tab_titles()
        if titles:
            return titles
    except Exception:
        pass
    return []


__all__ = ["try_list_browser_tabs"]
