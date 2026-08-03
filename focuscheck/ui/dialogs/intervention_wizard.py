"""
Intervention workflow: selection + blackout/spotlight + verification.
"""

import time
import os
import uuid
import tkinter as tk
import queue
import threading
from tkinter import ttk, messagebox

from ...platform_specific.window_enumeration import (
    list_top_level_windows,
    is_window_open,
)
from ...platform_specific.browser_info import is_supported_browser
from ...platform_specific.browser_tabs import try_list_browser_tabs
from ...utils.timers import TimerRegistry

try:
    from ...utils import get_logger, privacy_summary
except Exception:  # pragma: no cover - fallback
    def get_logger():
        import logging
        return logging.getLogger(__name__)

    def privacy_summary(value):
        return {"type": type(value).__name__, "length": len(str(value or "")), "sha256": None}

try:
    from .intervention_reflection_dialog import InterventionReflectionDialog
except Exception:
    InterventionReflectionDialog = None  # type: ignore


def _configure_spotlight_region_api(user32, gdi32):
    """Declare region/cursor signatures before native spotlight updates."""
    import ctypes
    from ctypes import wintypes

    region_args = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    gdi32.CreateRectRgn.argtypes = region_args
    gdi32.CreateRectRgn.restype = wintypes.HANDLE
    gdi32.CreateEllipticRgn.argtypes = region_args
    gdi32.CreateEllipticRgn.restype = wintypes.HANDLE
    gdi32.CombineRgn.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.c_int,
    ]
    gdi32.CombineRgn.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.DeleteObject.restype = wintypes.BOOL
    user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
    user32.SetWindowRgn.restype = ctypes.c_int
    user32.GetCursorPos.argtypes = [ctypes.c_void_p]
    user32.GetCursorPos.restype = wintypes.BOOL


def _configure_window_position_api(user32):
    """Declare user32 signatures used by virtual-screen positioning helpers."""
    import ctypes
    from ctypes import wintypes

    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL


def _release_spotlight_regions(gdi32, full, hole, combined, window_owns_combined):
    """Release temporary regions while respecting SetWindowRgn ownership."""
    for handle in (full, hole):
        if handle:
            try:
                gdi32.DeleteObject(handle)
            except Exception:
                pass
    if combined and not window_owns_combined:
        try:
            gdi32.DeleteObject(combined)
        except Exception:
            pass


class WindowSelectionDialog(tk.Toplevel):
    """Select open windows to close."""

    def __init__(self, parent, windows, preselect_hwnd=None, preselect_title=None):
        super().__init__(parent)
        self.title("Select distractions")
        self.geometry("620x420+120+120")
        self.resizable(True, True)
        try:
            if _is_window_viewable(parent):
                self.transient(parent)
            else:
                try:
                    get_logger().info("selection dialog: parent not viewable; skipping transient")
                except Exception:
                    pass
        except Exception:
            try:
                get_logger().exception("selection dialog: transient failed", exc_info=True)
            except Exception:
                pass
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            try:
                get_logger().exception("selection dialog grab_set failed", exc_info=True)
            except Exception:
                pass

        self._windows = windows
        self._items = []
        self._selection = None
        self._closed = False
        self._tab_queue = queue.Queue()
        self._tab_threads = []
        self._tab_scan_cancel = threading.Event()
        self._front_timer_id = None
        self._tab_scan_timer_id = None
        self._timers = TimerRegistry(self)

        try:
            self._build_ui(preselect_hwnd, preselect_title)
        except Exception:
            try:
                get_logger().exception("selection dialog: build_ui failed", exc_info=True)
            except Exception:
                pass
        try:
            _log_window_state("selection dialog built", self)
        except Exception:
            pass
        try:
            _center_on_virtual_screen(self)
        except Exception:
            pass
        try:
            _clamp_to_primary_screen(self)
        except Exception:
            pass
        try:
            _log_window_state("selection dialog positioned", self)
        except Exception:
            pass
        try:
            self._force_front_loop()
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Return>", lambda _e: self._continue())
        self.bind("<KP_Enter>", lambda _e: self._continue())
        try:
            self.listbox.focus_set()
        except Exception:
            pass

    def _build_ui(self, preselect_hwnd, preselect_title):
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Select windows/tabs to close (click to toggle):").pack(anchor="w")

        list_frame = ttk.Frame(container)
        list_frame.pack(fill="both", expand=True, pady=(6, 10))

        self.listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        try:
            self.listbox.bind("<Button-1>", self._toggle_selection, add=False)
            self.listbox.bind("<space>", self._toggle_selection_key, add=True)
        except Exception:
            pass

        self._items = []
        for entry in self._windows:
            title = entry.get("title", "")
            proc = entry.get("process_name", "")
            label = f"Window: {title} ({proc})" if proc else f"Window: {title}"
            self._items.append({"type": "window", "data": entry})
            self.listbox.insert("end", label)
            if preselect_hwnd and entry.get("hwnd") == preselect_hwnd:
                try:
                    self.listbox.selection_set(len(self._items) - 1)
                except Exception:
                    pass

        # Tab discovery runs asynchronously to avoid freezing the UI
        self._start_tab_scan(preselect_title)

        btns = ttk.Frame(container)
        btns.pack(fill="x")
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="Continue", command=self._continue).pack(side="right", padx=(0, 8))

    def _continue(self):
        indices = list(self.listbox.curselection())
        if not indices:
            messagebox.showinfo("Select windows", "Please select at least one window.")
            return
        selected_windows = []
        selected_tabs = []
        for idx in indices:
            try:
                item = self._items[int(idx)]
                if item.get("type") == "header":
                    continue
                if item["type"] == "window":
                    selected_windows.append(item["data"])
                elif item["type"] == "tab":
                    selected_tabs.append(item["data"])
            except Exception:
                continue
        try:
            get_logger().info("selection made | windows=%s tabs=%s", len(selected_windows), len(selected_tabs))
        except Exception:
            pass
        self._selection = {
            "windows": selected_windows,
            "tabs": selected_tabs,
        }
        self._close()

    def _toggle_selection(self, event):
        try:
            idx = int(self.listbox.nearest(event.y))
            if idx < 0:
                return "break"
            try:
                item = self._items[idx]
                if item.get("type") == "header":
                    return "break"
            except Exception:
                pass
            if idx in self.listbox.curselection():
                self.listbox.selection_clear(idx)
            else:
                self.listbox.selection_set(idx)
            return "break"
        except Exception:
            return None

    def _toggle_selection_key(self, _event):
        try:
            idx = int(self.listbox.index("active"))
            try:
                item = self._items[idx]
                if item.get("type") == "header":
                    return "break"
            except Exception:
                pass
            if idx in self.listbox.curselection():
                self.listbox.selection_clear(idx)
            else:
                self.listbox.selection_set(idx)
            return "break"
        except Exception:
            return None

    def _cancel(self):
        self._selection = None
        try:
            get_logger().info("selection dialog cancelled")
        except Exception:
            pass
        self._close()

    def _close(self):
        self._cancel_scheduled_callbacks()
        try:
            self.grab_release()
        except Exception:
            pass
        self._closed = True
        try:
            self.destroy()
        except Exception:
            try:
                get_logger().exception("selection dialog destroy failed", exc_info=True)
            except Exception:
                pass

    def _cancel_scheduled_callbacks(self):
        """Cancel recurring callbacks before the Toplevel is destroyed."""
        self._tab_scan_cancel.set()
        self._timers.close()
        self._front_timer_id = None
        self._tab_scan_timer_id = None
        for thread in self._tab_threads:
            if thread.is_alive() and thread is not threading.current_thread():
                try:
                    thread.join(timeout=0.1)
                except Exception:
                    pass
        self._tab_threads.clear()

    def destroy(self):
        self._cancel_scheduled_callbacks()
        return super().destroy()

    def _force_front_loop(self):
        if self._closed:
            return
        try:
            self.lift()
            self.attributes("-topmost", True)
            self.focus_force()
            _center_on_virtual_screen(self)
            _clamp_to_primary_screen(self)
        except Exception:
            pass
        try:
            self._timers.schedule("force-front", 800, self._force_front_loop)
            self._front_timer_id = self._timers.callback_id("force-front")
        except Exception:
            pass

    def _start_tab_scan(self, preselect_title):
        def worker(entry):
            if self._tab_scan_cancel.is_set():
                return
            title = entry.get("title", "")
            proc = entry.get("process_name", "")
            hwnd = entry.get("hwnd")
            if not is_supported_browser(proc):
                return
            tabs = []
            try:
                tabs = try_list_browser_tabs(hwnd, proc)
            except Exception:
                tabs = []
            if self._tab_scan_cancel.is_set():
                return
            try:
                self._tab_queue.put((entry, tabs, preselect_title))
            except Exception:
                pass
        for entry in self._windows:
            proc = entry.get("process_name", "")
            if not is_supported_browser(proc):
                continue
            t = threading.Thread(target=worker, args=(entry,), daemon=True)
            self._tab_threads.append(t)
            t.start()
        try:
            self._timers.schedule("tab-scan", 200, self._drain_tab_queue)
            self._tab_scan_timer_id = self._timers.callback_id("tab-scan")
        except Exception:
            pass

    def _drain_tab_queue(self):
        if self._closed:
            return
        drained = False
        while True:
            try:
                entry, tabs, preselect_title = self._tab_queue.get_nowait()
            except Exception:
                break
            drained = True
            title = entry.get("title", "")
            proc = entry.get("process_name", "")
            try:
                get_logger().info("tabs for title_summary=%s (%s): %s", privacy_summary(title), proc, len(tabs))
            except Exception:
                pass
            if not tabs:
                continue
            header_label = f"Tabs for {title} ({proc})" if proc else f"Tabs for {title}"
            self._items.append({"type": "header", "data": {"window": entry}})
            self.listbox.insert("end", header_label)
            for tab_title in tabs:
                self._items.append({"type": "tab", "data": {"title": tab_title, "window": entry}})
                self.listbox.insert("end", f"  Tab: {tab_title}")
                if preselect_title and tab_title and tab_title in preselect_title:
                    try:
                        self.listbox.selection_set(len(self._items) - 1)
                    except Exception:
                        pass
        # Replace the one-shot scan through the registry so the slower
        # cadence after a productive drain is preserved without raw Tk IDs.
        self._timers.schedule("tab-scan", 200 if not drained else 400, self._drain_tab_queue)
        self._tab_scan_timer_id = self._timers.callback_id("tab-scan")

    @staticmethod
    def prompt(parent, windows, preselect_hwnd=None, preselect_title=None, raise_above=None):
        dlg = WindowSelectionDialog(parent, windows, preselect_hwnd=preselect_hwnd, preselect_title=preselect_title)
        try:
            if raise_above is not None:
                _raise_above_window(dlg, raise_above)
                dlg.lift()
                dlg.attributes("-topmost", True)
        except Exception:
            pass
        parent.wait_window(dlg)
        return dlg._selection


class SpotlightOverlay(tk.Toplevel):
    """Full-screen blackout overlay with transparent spotlight around cursor."""

    def __init__(self, parent, radius=120):
        super().__init__(parent)
        self._radius = radius
        self._mask_color = "#ff00ff"
        self._closed = False
        self._region_supported = False
        self._use_native = False
        self._native_overlay = None
        self._no_overlay = False
        self._last_tick_log = 0.0
        self._last_region_log = 0.0
        self._after_id = None
        self._timers = TimerRegistry(self)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        origin_x, origin_y, screen_w, screen_h = _get_virtual_screen_rect()
        self._origin_x = origin_x
        self._origin_y = origin_y
        self._screen_w = screen_w
        self._screen_h = screen_h
        try:
            get_logger().info(
                "spotlight: init | rect=%sx%s+%s+%s radius=%s",
                screen_w, screen_h, origin_x, origin_y, radius,
            )
        except Exception:
            pass
        self._use_native = self._init_native_overlay(origin_x, origin_y, screen_w, screen_h)
        if not self._use_native:
            self._no_overlay = True
            try:
                get_logger().warning("native overlay unavailable; no blackout shown")
            except Exception:
                pass
            try:
                self.withdraw()
            except Exception:
                pass
            self._update_spotlight()
            return
        try:
            self.withdraw()
        except Exception:
            pass
        self._update_spotlight()

    def _init_region_support(self):
        try:
            import platform
            if platform.system().lower() != "windows":
                return False
            import ctypes
            self._user32 = ctypes.windll.user32
            self._gdi32 = ctypes.windll.gdi32
            _configure_spotlight_region_api(self._user32, self._gdi32)
            self._RGN_DIFF = 4
            return True
        except Exception:
            return False

    def _init_native_overlay(self, origin_x, origin_y, screen_w, screen_h):
        try:
            import platform
            if platform.system().lower() != "windows":
                return False
            from ...platform_specific.windows import WinClickThroughOverlay
            try:
                get_logger().info("spotlight: creating native overlay")
            except Exception:
                pass
            self._native_overlay = WinClickThroughOverlay(
                origin_x,
                origin_y,
                screen_w,
                screen_h,
                color_hex="#000000",
                log_tag="spotlight",
            )
            self._native_overlay.set_alpha(0.9)
            self._region_supported = self._init_region_support()
            try:
                get_logger().info("native overlay created | size=%sx%s origin=%s,%s", screen_w, screen_h, origin_x, origin_y)
            except Exception:
                pass
            return True
        except Exception:
            try:
                get_logger().exception("native overlay creation failed", exc_info=True)
                code, msg = _get_last_error_info()
                get_logger().error("spotlight: native overlay last_error=%s msg=%s", code, msg)
            except Exception:
                pass
            self._native_overlay = None
            return False

    def _apply_region_spotlight(self, x, y):
        full = hole = combined = None
        window_owns_combined = False
        try:
            hwnd = self.winfo_id()
            r = self._radius
            left = int(x - r)
            top = int(y - r)
            right = int(x + r)
            bottom = int(y + r)
            full = self._gdi32.CreateRectRgn(0, 0, int(self._screen_w), int(self._screen_h))
            hole = self._gdi32.CreateEllipticRgn(left, top, right, bottom)
            combined = self._gdi32.CreateRectRgn(0, 0, 1, 1)
            self._gdi32.CombineRgn(combined, full, hole, self._RGN_DIFF)
            ok = self._user32.SetWindowRgn(hwnd, combined, True)
            window_owns_combined = bool(ok)
            if not ok:
                try:
                    code, msg = _get_last_error_info()
                    get_logger().error("spotlight: SetWindowRgn failed | err=%s msg=%s", code, msg)
                except Exception:
                    pass
        except Exception:
            self._region_supported = False
        finally:
            _release_spotlight_regions(
                getattr(self, "_gdi32", None), full, hole, combined, window_owns_combined,
            )

    def _apply_region_spotlight_native(self, x, y):
        full = hole = combined = None
        window_owns_combined = False
        try:
            if not self._native_overlay or not self._region_supported:
                return
            hwnd = self._native_overlay.hwnd
            r = self._radius
            left = int(x - r)
            top = int(y - r)
            right = int(x + r)
            bottom = int(y + r)
            full = self._gdi32.CreateRectRgn(0, 0, int(self._screen_w), int(self._screen_h))
            hole = self._gdi32.CreateEllipticRgn(left, top, right, bottom)
            combined = self._gdi32.CreateRectRgn(0, 0, 1, 1)
            self._gdi32.CombineRgn(combined, full, hole, self._RGN_DIFF)
            window_owns_combined = bool(self._user32.SetWindowRgn(hwnd, combined, True))
            try:
                now = time.monotonic()
                if (now - self._last_region_log) > 2.0:
                    self._last_region_log = now
                    get_logger().info("spotlight: applying region | center=%s,%s radius=%s", int(x), int(y), r)
            except Exception:
                pass
        except Exception:
            self._region_supported = False
            try:
                get_logger().exception("native spotlight region failed", exc_info=True)
            except Exception:
                pass
        finally:
            _release_spotlight_regions(
                getattr(self, "_gdi32", None), full, hole, combined, window_owns_combined,
            )

    def _update_spotlight(self):
        if self._closed:
            return
        try:
            if self._no_overlay:
                try:
                    now = time.monotonic()
                    if (now - self._last_tick_log) > 2.0:
                        self._last_tick_log = now
                        get_logger().info("spotlight: update tick running (no overlay)")
                except Exception:
                    pass
                self._timers.schedule("spotlight-update", 200, self._update_spotlight)
                self._after_id = self._timers.callback_id("spotlight-update")
                return
            if self._use_native and self._native_overlay:
                try:
                    import ctypes
                    class POINT(ctypes.Structure):
                        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                    pt = POINT()
                    if self._user32.GetCursorPos(ctypes.byref(pt)):
                        x = pt.x - self._origin_x
                        y = pt.y - self._origin_y
                        self._apply_region_spotlight_native(x, y)
                except Exception:
                    pass
            else:
                x = self.winfo_pointerx() - self._origin_x
                y = self.winfo_pointery() - self._origin_y
                r = self._radius
                if self._region_supported:
                    self._apply_region_spotlight(x, y)
                else:
                    self.canvas.coords(self._spot_id, x - r, y - r, x + r, y + r)
            try:
                now = time.monotonic()
                if (now - self._last_tick_log) > 2.0:
                    self._last_tick_log = now
                    get_logger().info("spotlight: update tick running")
            except Exception:
                pass
        except Exception:
            try:
                get_logger().exception("spotlight: update tick failed, closing overlay", exc_info=True)
            except Exception:
                pass
            self.close()
            return
        self._timers.schedule("spotlight-update", 50, self._update_spotlight)
        self._after_id = self._timers.callback_id("spotlight-update")

    def _enable_click_through(self):
        try:
            from ...platform_specific.windows import enable_click_through_windows, install_httransparent_wndproc
        except Exception:
            return
        try:
            self.update_idletasks()
            hwnd = self.winfo_id()
            enable_click_through_windows(hwnd)
            install_httransparent_wndproc(hwnd, owner_widget=self)
            try:
                canvas_hwnd = self.canvas.winfo_id()
                enable_click_through_windows(canvas_hwnd)
                install_httransparent_wndproc(canvas_hwnd, owner_widget=self.canvas)
            except Exception:
                pass
        except Exception:
            pass

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._timers.close()
        self._after_id = None
        try:
            if self._native_overlay is not None:
                self._native_overlay.destroy()
                self._native_overlay = None
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


class InterventionActionDialog(tk.Toplevel):
    """Instruction panel shown during the spotlight stage."""

    def __init__(self, parent, on_verify, on_cancel):
        super().__init__(parent)
        # The dialog owns its recurring callbacks so a window-manager close
        # cannot leave work queued against a destroyed Toplevel.
        self._timers = TimerRegistry(self)
        self.title("Intervention")
        self.geometry("420x200")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", on_cancel)
        self.bind("<Escape>", lambda _e: on_cancel())
        self.bind("<Return>", lambda _e: on_verify())
        self.bind("<KP_Enter>", lambda _e: on_verify())
        try:
            _center_on_virtual_screen(self)
        except Exception:
            pass

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="Close the selected items now.", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text="A spotlight follows your cursor. Close the windows/tabs you selected.",
            wraplength=380,
        ).pack(anchor="w", pady=(8, 12))

        btns = ttk.Frame(container)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right")
        verify_btn = ttk.Button(btns, text="Verify", command=on_verify)
        verify_btn.pack(side="right", padx=(0, 8))
        try:
            verify_btn.focus_set()
        except Exception:
            pass

    def destroy(self):
        self._timers.close()
        return super().destroy()


from ...settings import gates


class InterventionWizard:
    """Run the intervention workflow."""

    def __init__(self, parent, settings=None):
        self.parent = parent
        self.settings = settings if settings is not None else getattr(parent, "settings", {})
        self._error_shown = False
        # Keep the parent-owned fail-safe timer generation-aware so a late
        # callback cannot inspect or destroy a selection dialog from a prior run.
        self._timers = TimerRegistry(parent)

    def _schedule_prompt_focus(self, prompt_ref) -> bool:
        """Schedule prompt focus recovery through the prompt's timer owner."""
        if prompt_ref is None:
            return False
        callback = getattr(prompt_ref, "_force_window_to_front", None)
        if not callable(callback):
            return False
        owner = getattr(prompt_ref, "_timers", None)
        if owner is None or getattr(owner, "closed", False):
            owner = self._timers
        return bool(owner.schedule("intervention-prompt-focus", 50, callback))

    def run(self, preselect_hwnd=None, preselect_title=None, prompt_ref=None, hide_prompt=False, intervention_id=None):
        logger = None
        try:
            logger = get_logger()
        except Exception:
            logger = None
        if not _is_tk_thread(self.parent):
            try:
                if logger:
                    logger.warning("intervention: run called off Tk thread; marshaling to Tk loop")
            except Exception:
                pass
            done = threading.Event()
            cancelled = threading.Event()
            result_holder = {}

            def _run_on_ui():
                if cancelled.is_set() or getattr(self, "_closed", False):
                    done.set()
                    return
                try:
                    result_holder["value"] = self._run_internal(
                        preselect_hwnd=preselect_hwnd,
                        preselect_title=preselect_title,
                        prompt_ref=prompt_ref,
                        hide_prompt=hide_prompt,
                        intervention_id=intervention_id,
                    )
                except Exception:
                    if logger:
                        logger.exception("intervention: run failed on Tk thread", exc_info=True)
                    result_holder["value"] = False
                finally:
                    done.set()

            dispatch_name = "off-thread-dispatch"
            try:
                if not self._timers.schedule(dispatch_name, 0, _run_on_ui):
                    raise RuntimeError("intervention timer registry is closed")
            except Exception:
                if logger:
                    logger.exception("intervention: failed to marshal to Tk thread", exc_info=True)
                return False
            if not done.wait(timeout=60.0):
                # The UI callback may still be queued after the caller's
                # bounded wait. Invalidate it so a late Tk dispatch cannot
                # open an intervention invisibly.
                cancelled.set()
                self._timers.cancel(dispatch_name)
                return False
            return bool(result_holder.get("value"))
        return self._run_internal(
            preselect_hwnd=preselect_hwnd,
            preselect_title=preselect_title,
            prompt_ref=prompt_ref,
            hide_prompt=hide_prompt,
            intervention_id=intervention_id,
        )

    def _run_internal(self, preselect_hwnd=None, preselect_title=None, prompt_ref=None, hide_prompt=False, intervention_id=None):
        logger = None
        try:
            logger = get_logger()
        except Exception:
            logger = None
        try:
            if logger:
                logger.info("intervention: run start | thread=%s", threading.current_thread().name)
        except Exception:
            pass
        if not intervention_id:
            try:
                intervention_id = uuid.uuid4().hex
            except Exception:
                intervention_id = None
        if logger:
            logger.info("intervention: id=%s", intervention_id)
        try:
            windows = list_top_level_windows()
        except Exception:
            windows = []
            if logger:
                logger.exception("intervention: window enumeration failed", exc_info=True)
        try:
            if logger:
                logger.info("intervention: windows found=%s", len(windows))
        except Exception:
            pass
        if not windows:
            try:
                messagebox.showinfo("No windows", "No open windows found to close.")
            except Exception:
                if logger:
                    logger.exception("intervention: failed to show empty windows dialog", exc_info=True)
            return False

        overlays_enabled = gates.are_overlays_enabled(self.settings)
        blackout = None
        if overlays_enabled:
            try:
                if logger:
                    logger.info("intervention: creating blackout overlay")
                blackout = BlackoutOverlay(self.parent, alpha=0.9)
                if logger:
                    logger.info("intervention: blackout overlay created | %s", _window_state_snapshot(blackout))
            except Exception:
                blackout = None
                if logger:
                    logger.exception("intervention: blackout overlay failed", exc_info=True)
        else:
            try:
                if logger:
                    logger.info("intervention: overlays disabled by env")
            except Exception:
                pass

        prompt_hidden = False
        if prompt_ref is not None and hide_prompt:
            try:
                prompt_ref.withdraw()
                prompt_hidden = True
                if logger:
                    logger.info("intervention: prompt hidden for selection stage")
            except Exception:
                if logger:
                    logger.exception("intervention: failed to hide prompt", exc_info=True)

        selection_dialog = None
        try:
            if logger:
                logger.info("intervention: creating selection dialog")
                try:
                    logger.info(
                        "intervention: selection thread check | thread_id=%s tk_thread_id=%s is_tk_thread=%s parent_state=%s",
                        threading.get_ident(),
                        _get_tk_thread_id(self.parent),
                        _is_tk_thread(self.parent),
                        _window_state_snapshot(self.parent),
                    )
                except Exception:
                    pass
            selection_dialog = WindowSelectionDialog(
                self.parent,
                windows,
                preselect_hwnd=preselect_hwnd,
                preselect_title=preselect_title,
            )
            try:
                selection_dialog.update_idletasks()
                if logger:
                    logger.info("intervention: selection dialog post-create | %s", _window_state_snapshot(selection_dialog))
            except Exception:
                if logger:
                    logger.exception("intervention: selection dialog post-create snapshot failed", exc_info=True)
            try:
                if blackout is not None:
                    try:
                        blackout.attributes("-topmost", False)
                        blackout.lower()
                    except Exception:
                        if logger:
                            logger.exception("intervention: blackout z-order pre-adjust failed", exc_info=True)
            except Exception:
                if logger:
                    logger.exception("intervention: blackout pre-adjust exception", exc_info=True)
            try:
                selection_dialog.deiconify()
                selection_dialog.lift()
                selection_dialog.attributes("-topmost", True)
                selection_dialog.focus_force()
                selection_dialog.update_idletasks()
            except Exception:
                if logger:
                    logger.exception("intervention: selection dialog show failed", exc_info=True)
            try:
                if logger:
                    logger.info("intervention: selection dialog created | %s", _window_state_snapshot(selection_dialog))
                    logger.info("intervention: blackout state | %s", _overlay_state_snapshot(blackout))
            except Exception:
                pass
        except Exception:
            if logger:
                logger.exception("intervention: selection dialog creation failed", exc_info=True)
            try:
                if blackout is not None:
                    blackout.close()
            except Exception:
                if logger:
                    logger.exception("intervention: failed to close blackout after selection error", exc_info=True)
            if prompt_ref is not None and prompt_hidden:
                try:
                    prompt_ref.deiconify()
                    prompt_ref.lift()
                    self._schedule_prompt_focus(prompt_ref)
                except Exception:
                    if logger:
                        logger.exception("intervention: failed to restore prompt after selection error", exc_info=True)
            try:
                messagebox.showerror(
                    "Intervention",
                    "Selection dialog failed to open. Prompt restored.",
                    parent=prompt_ref if prompt_ref is not None else self.parent,
                )
                self._error_shown = True
            except Exception:
                if logger:
                    logger.exception("intervention: failed to show selection error", exc_info=True)
            return False

        fail_safe = {"fired": False}

        def _cancel_selection_visibility_check():
            self._timers.cancel("selection-visibility")

        def _restore_prompt_with_error(reason):
            _cancel_selection_visibility_check()
            if fail_safe["fired"]:
                return
            fail_safe["fired"] = True
            try:
                if logger:
                    logger.error("intervention: selection dialog not visible | %s", reason)
            except Exception:
                pass
            try:
                if selection_dialog is not None:
                    selection_dialog._selection = None
                    selection_dialog._closed = True
                    selection_dialog.destroy()
            except Exception:
                if logger:
                    logger.exception("intervention: failed to destroy selection dialog in fail-safe", exc_info=True)
            try:
                if blackout is not None:
                    blackout.close()
            except Exception:
                if logger:
                    logger.exception("intervention: failed to close blackout in fail-safe", exc_info=True)
            if prompt_ref is not None and prompt_hidden:
                try:
                    prompt_ref.deiconify()
                    prompt_ref.lift()
                    self._schedule_prompt_focus(prompt_ref)
                except Exception:
                    if logger:
                        logger.exception("intervention: failed to restore prompt in fail-safe", exc_info=True)
            try:
                messagebox.showerror(
                    "Intervention",
                    "Selection dialog failed to open. The main prompt was restored.",
                    parent=prompt_ref if prompt_ref is not None else self.parent,
                )
                self._error_shown = True
            except Exception:
                if logger:
                    logger.exception("intervention: failed to show fail-safe error", exc_info=True)

        def _selection_visibility_check():
            if fail_safe["fired"]:
                return
            if selection_dialog is None or getattr(selection_dialog, "_closed", False):
                return
            state = _window_state_snapshot(selection_dialog)
            offscreen = _is_offscreen(selection_dialog)
            if not state.get("viewable") or state.get("state") == "withdrawn" or offscreen:
                try:
                    if logger:
                        logger.warning(
                            "intervention: selection dialog visibility check failed; attempting recovery | %s",
                            _window_state_snapshot(selection_dialog),
                        )
                except Exception:
                    pass
                # Attempt recovery first
                try:
                    selection_dialog.deiconify()
                    selection_dialog.lift()
                    selection_dialog.attributes("-topmost", True)
                    selection_dialog.focus_force()
                    selection_dialog.update_idletasks()
                except Exception:
                    if logger:
                        logger.exception("intervention: selection dialog recovery failed", exc_info=True)
                state = _window_state_snapshot(selection_dialog)
                offscreen = _is_offscreen(selection_dialog)
                if not state.get("viewable") or state.get("state") == "withdrawn" or offscreen:
                    reason = "viewable=%s state=%s offscreen=%s geom=%s" % (
                        state.get("viewable"),
                        state.get("state"),
                        offscreen,
                        state.get("geometry"),
                    )
                    try:
                        if logger:
                            logger.error("intervention: blackout state on fail-safe | %s", _overlay_state_snapshot(blackout))
                    except Exception:
                        pass
                    _restore_prompt_with_error(reason)

        try:
            self._timers.schedule("selection-visibility", 500, _selection_visibility_check)
        except Exception:
            if logger:
                logger.exception("intervention: failed to schedule selection fail-safe", exc_info=True)

        try:
            self.parent.wait_window(selection_dialog)
        except Exception:
            if logger:
                logger.exception("intervention: wait_window failed", exc_info=True)
        _cancel_selection_visibility_check()

        try:
            if blackout is not None:
                blackout.close()
        except Exception:
            if logger:
                logger.exception("intervention: failed to close blackout after selection", exc_info=True)
        selection = getattr(selection_dialog, "_selection", None)
        try:
            if logger:
                logger.info("intervention: selection dialog closed | selected=%s", bool(selection))
        except Exception:
            pass
        if not selection:
            if prompt_ref is not None and prompt_hidden:
                try:
                    prompt_ref.deiconify()
                    prompt_ref.lift()
                except Exception:
                    if logger:
                        logger.exception("intervention: failed to restore prompt after cancel", exc_info=True)
            return False
        selected_windows = selection.get("windows", [])
        selected_tabs = selection.get("tabs", [])
        if not selected_windows and not selected_tabs:
            if hide_prompt and prompt_ref is not None:
                try:
                    prompt_ref.deiconify()
                    prompt_ref.lift()
                except Exception:
                    if logger:
                        logger.exception("intervention: failed to restore prompt after empty selection", exc_info=True)
            return False

        if hide_prompt and prompt_ref is not None:
            try:
                if logger:
                    logger.info("intervention: prompt already hidden for spotlight stage")
            except Exception:
                pass

        overlay = None
        if overlays_enabled:
            try:
                if logger:
                    logger.info("intervention: creating spotlight overlay")
                overlay = SpotlightOverlay(self.parent, radius=120)
                if getattr(overlay, "_no_overlay", False):
                    try:
                        if logger:
                            logger.warning("intervention: spotlight overlay unavailable; continuing without overlay")
                    except Exception:
                        pass
                    try:
                        overlay.close()
                    except Exception:
                        if logger:
                            logger.exception("intervention: failed to close no-op overlay", exc_info=True)
                    overlay = None
                if logger:
                    logger.info(
                        "intervention: spotlight overlay started | native=%s",
                        getattr(overlay, "_use_native", False) if overlay is not None else False,
                    )
            except Exception:
                overlay = None
                if logger:
                    logger.exception("intervention: spotlight overlay failed", exc_info=True)
        else:
            try:
                if logger:
                    logger.info("intervention: spotlight overlay disabled")
            except Exception:
                pass

        result = {"done": False, "cancel": False}
        action_timers = {"owner": None}
        cleanup_complete = {"value": False}

        def _action_timers_closed():
            owner = action_timers.get("owner")
            return owner is None or owner.closed

        def _verify(silent=False):
            try:
                if logger:
                    logger.info("intervention: verify requested | silent=%s", silent)
            except Exception:
                pass
            remaining_windows = []
            for entry in selected_windows:
                hwnd = entry.get("hwnd")
                if hwnd and is_window_open(hwnd):
                    remaining_windows.append(entry)
            remaining_tabs = []
            if selected_tabs:
                for tab in selected_tabs:
                    window = tab.get("window") or {}
                    hwnd = window.get("hwnd")
                    proc = window.get("process_name")
                    try:
                        tabs = try_list_browser_tabs(hwnd, proc)
                    except Exception:
                        tabs = []
                        if logger:
                            logger.exception("intervention: tab lookup failed", exc_info=True)
                    title = tab.get("title")
                    if not tabs:
                        if hwnd and is_window_open(hwnd):
                            remaining_tabs.append(tab)
                        continue
                    if not title:
                        if hwnd and is_window_open(hwnd):
                            remaining_tabs.append(tab)
                        continue
                    if title in tabs:
                        remaining_tabs.append(tab)
            if remaining_windows or remaining_tabs:
                try:
                    if logger:
                        logger.info("intervention: remaining windows=%s tabs=%s", len(remaining_windows), len(remaining_tabs))
                except Exception:
                    pass
                if silent:
                    return False
                try:
                    messagebox.showwarning(
                        "Still open",
                        "Some selected items are still open. Please close them, then click Verify again.",
                    )
                except Exception:
                    if logger:
                        logger.exception("intervention: failed to show remaining warning", exc_info=True)
                return False
            result["done"] = True
            try:
                if logger:
                    logger.info("intervention: verify success")
            except Exception:
                pass
            _cleanup()
            return True

        def _cancel():
            result["cancel"] = True
            try:
                if logger:
                    logger.info("intervention: cancelled")
            except Exception:
                pass
            _cleanup()

        def _cleanup():
            if cleanup_complete["value"]:
                return
            cleanup_complete["value"] = True
            owner = action_timers.get("owner")
            if owner is not None and not owner.closed:
                owner.close()
            try:
                if overlay is not None:
                    overlay.close()
            except Exception:
                if logger:
                    logger.exception("intervention: failed to close spotlight overlay", exc_info=True)
            try:
                action.destroy()
            except Exception:
                if logger:
                    logger.exception("intervention: failed to destroy action dialog", exc_info=True)

        def _auto_check():
            if _action_timers_closed() or result["done"] or result["cancel"]:
                return
            if _verify(silent=True):
                return
            try:
                action_timers["owner"].schedule("auto", 800, _auto_check)
            except Exception:
                if logger:
                    logger.exception("intervention: auto-check schedule failed", exc_info=True)

        action = InterventionActionDialog(self.parent, on_verify=_verify, on_cancel=_cancel)
        action_timers["owner"] = action._timers
        try:
            if logger:
                logger.info("intervention: action dialog shown | %s", _window_state_snapshot(action))
        except Exception:
            pass

        def _keep_action_visible():
            try:
                if _action_timers_closed() or result["done"] or result["cancel"]:
                    return
                if overlay is not None:
                    if getattr(overlay, "_use_native", False) and getattr(overlay, "_native_overlay", None) is not None:
                        _raise_above_hwnd(action, overlay._native_overlay.hwnd)
                    else:
                        _raise_above_window(action, overlay)
                action.lift()
                action.attributes("-topmost", True)
            except Exception:
                if logger:
                    logger.exception("intervention: keep action visible failed", exc_info=True)
            try:
                action_timers["owner"].schedule("visible", 500, _keep_action_visible)
            except Exception:
                if logger:
                    logger.exception("intervention: keep action schedule failed", exc_info=True)

        try:
            _keep_action_visible()
            action.focus_force()
            action_timers["owner"].schedule("auto", 800, _auto_check)
        except Exception:
            if logger:
                logger.exception("intervention: action dialog setup failed", exc_info=True)
        try:
            self.parent.wait_window(action)
        except Exception:
            if logger:
                logger.exception("intervention: wait_window action failed", exc_info=True)
        finally:
            # WM_DELETE_WINDOW and unexpected wait failures must use the same
            # cleanup contract as Verify and Cancel.
            _cleanup()
        if bool(result.get("done")) and not bool(result.get("cancel")):
            try:
                if InterventionReflectionDialog is not None and intervention_id:
                    ctx = {
                        "selected_windows": len(selected_windows),
                        "selected_tabs": len(selected_tabs),
                    }
                    InterventionReflectionDialog.prompt(
                        self.parent,
                        intervention_id=intervention_id,
                        outcome="success",
                        context=ctx,
                    )
            except Exception:
                if logger:
                    logger.exception("intervention: reflection dialog failed", exc_info=True)
        return bool(result["done"]) and not bool(result["cancel"])


class BlackoutOverlay(tk.Toplevel):
    """Full-screen dim overlay for stage 1 selection."""

    def __init__(self, parent, alpha=0.9):
        super().__init__(parent)
        self._closed = False
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", alpha)
        except Exception:
            pass
        self.configure(bg="#000000")
        origin_x, origin_y, w, h = _get_virtual_screen_rect()
        self.geometry(_format_geometry(w, h, origin_x, origin_y))
        _apply_absolute_geometry(self, origin_x, origin_y, w, h)
        try:
            self.lower()
        except Exception:
            pass

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.destroy()
        except Exception:
            pass


def _format_geometry(w, h, x, y):
    sx = f"{x:+d}" if x < 0 else f"+{x}"
    sy = f"{y:+d}" if y < 0 else f"+{y}"
    return f"{w}x{h}{sx}{sy}"


def _get_virtual_screen_rect():
    try:
        import platform
        if platform.system().lower() == "windows":
            import ctypes
            user32 = ctypes.windll.user32
            _configure_window_position_api(user32)
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            if w > 0 and h > 0:
                return int(x), int(y), int(w), int(h)
    except Exception:
        pass
    # Fallback: primary screen
    root = tk.Tk()
    root.withdraw()
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.destroy()
    return 0, 0, int(w), int(h)


def _center_on_virtual_screen(window):
    try:
        window.update_idletasks()
    except Exception:
        pass
    try:
        w = int(window.winfo_width())
        h = int(window.winfo_height())
    except Exception:
        w, h = 520, 360
    origin_x, origin_y, screen_w, screen_h = _get_virtual_screen_rect()
    x = origin_x + max(0, int((screen_w - w) / 2))
    y = origin_y + max(0, int((screen_h - h) / 2))
    try:
        window.geometry(_format_geometry(w, h, x, y))
        _apply_absolute_geometry(window, x, y, w, h)
    except Exception:
        pass


def _apply_absolute_geometry(window, x, y, w, h):
    try:
        import platform
        if platform.system().lower() != "windows":
            return False
        import ctypes
        user32 = ctypes.windll.user32
        _configure_window_position_api(user32)
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        user32.SetWindowPos(window.winfo_id(), None, int(x), int(y), int(w), int(h), SWP_NOZORDER | SWP_NOACTIVATE)
        return True
    except Exception:
        return False


def _raise_above_window(window, below_window):
    try:
        import platform
        if platform.system().lower() != "windows":
            return False
        import ctypes
        user32 = ctypes.windll.user32
        _configure_window_position_api(user32)
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        user32.SetWindowPos(
            window.winfo_id(),
            below_window.winfo_id(),
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
        return True
    except Exception:
        return False


def _raise_above_hwnd(window, below_hwnd):
    try:
        import platform
        if platform.system().lower() != "windows":
            return False
        import ctypes
        user32 = ctypes.windll.user32
        _configure_window_position_api(user32)
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        user32.SetWindowPos(
            window.winfo_id(),
            int(below_hwnd),
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
        return True
    except Exception:
        return False


def _intervention_overlays_enabled():
    try:
        val = str(os.environ.get("FOCUSCHECK_DISABLE_INTERVENTION_OVERLAY", "")).strip().lower()
        return val not in ("1", "true", "yes", "on")
    except Exception:
        return True


def _is_tk_thread(widget):
    try:
        root = widget.winfo_toplevel()
    except Exception:
        root = widget
    tid = _get_tk_thread_id(root)
    if tid is None:
        return True
    return threading.get_ident() == tid


def _get_tk_thread_id(widget):
    try:
        return getattr(widget, "_focuscheck_tk_thread_id", None)
    except Exception:
        return None


def _is_window_viewable(window):
    try:
        return bool(window.winfo_viewable())
    except Exception:
        return False


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


def _log_window_state(label, window):
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


def _overlay_state_snapshot(overlay):
    if overlay is None:
        return {"present": False}
    state = {"present": True}
    try:
        state.update(_window_state_snapshot(overlay))
    except Exception:
        pass
    try:
        state["topmost"] = bool(overlay.attributes("-topmost"))
    except Exception:
        state["topmost"] = None
    return state


def _clamp_to_primary_screen(window):
    try:
        window.update_idletasks()
        w = int(window.winfo_width())
        h = int(window.winfo_height())
        if w <= 0 or h <= 0:
            return False
        screen_w = int(window.winfo_screenwidth())
        screen_h = int(window.winfo_screenheight())
        x = int(window.winfo_x())
        y = int(window.winfo_y())
        max_x = max(0, screen_w - w)
        max_y = max(0, screen_h - h)
        new_x = min(max(0, x), max_x)
        new_y = min(max(0, y), max_y)
        if new_x != x or new_y != y:
            window.geometry(_format_geometry(w, h, new_x, new_y))
            _apply_absolute_geometry(window, new_x, new_y, w, h)
            return True
        return False
    except Exception:
        return False


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


def _get_last_error_info():
    try:
        import ctypes
        code = ctypes.get_last_error()
        if not code:
            code = ctypes.windll.kernel32.GetLastError()
        msg = ""
        try:
            FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
            FORMAT_MESSAGE_IGNORE_INSERTS = 0x00000200
            buf = ctypes.create_unicode_buffer(1024)
            ctypes.windll.kernel32.FormatMessageW(
                FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                None,
                code,
                0,
                buf,
                len(buf),
                None,
            )
            msg = buf.value.strip()
        except Exception:
            msg = ""
        return int(code), msg
    except Exception:
        return None, ""


__all__ = ["InterventionWizard"]
