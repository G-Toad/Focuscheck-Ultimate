"""UI-related utilities."""

from .logging_utils import get_logger

def log_window_state(label, window):
    """Logs a snapshot of a Tkinter window's state."""
    try:
        s = _window_state_snapshot(window)
        offscreen = _is_offscreen(window)
        get_logger().info(
            "%s | viewable=%s ismapped=%s state=%s geom=%s x=%s y=%s rootx=%s rooty=%s w=%s h=%s screen=%sx%s offscreen=%s",
            label,
            s.get("viewable"),
            s.get("ismapped"),
            s.get("state"),
            s.get("geometry"),
            s.get("x"),
            s.get("y"),
            s.get("rootx"),
            s.get("rooty"),
            s.get("w"),
            s.get("h"),
            s.get("screen_w"),
            s.get("screen_h"),
            offscreen,
        )
    except Exception:
        pass

def _window_state_snapshot(window):
    state = {
        "viewable": None,
        "ismapped": None,
        "state": None,
        "geometry": None,
        "x": None,
        "y": None,
        "rootx": None,
        "rooty": None,
        "w": None,
        "h": None,
        "screen_w": None,
        "screen_h": None,
    }
    try:
        window.update_idletasks()
    except Exception:
        pass
    try:
        state["viewable"] = bool(window.winfo_viewable())
    except Exception:
        pass
    try:
        state["ismapped"] = bool(window.winfo_ismapped())
    except Exception:
        pass
    try:
        state["state"] = window.state()
    except Exception:
        pass
    try:
        state["geometry"] = window.winfo_geometry()
    except Exception:
        pass
    try:
        state["x"] = int(window.winfo_x())
        state["y"] = int(window.winfo_y())
        state["rootx"] = int(window.winfo_rootx())
        state["rooty"] = int(window.winfo_rooty())
        state["w"] = int(window.winfo_width())
        state["h"] = int(window.winfo_height())
    except Exception:
        pass
    try:
        state["screen_w"] = int(window.winfo_screenwidth())
        state["screen_h"] = int(window.winfo_screenheight())
    except Exception:
        pass
    return state

def _is_offscreen(window):
    try:
        window.update_idletasks()
        w = int(window.winfo_width())
        h = int(window.winfo_height())
        if w <= 1 or h <= 1:
            return True
        x = int(window.winfo_x())
        y = int(window.winfo_y())
        screen_w = int(window.winfo_screenwidth())
        screen_h = int(window.winfo_screenheight())
        if x >= screen_w or y >= screen_h:
            return True
        if (x + w) <= 0 or (y + h) <= 0:
            return True
        return False
    except Exception:
        return False
