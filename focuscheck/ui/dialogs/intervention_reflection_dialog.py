"""
Intervention reflection dialog (quick, no typing).
"""

import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone

try:
    from ...database import append_intervention_reflection
except Exception:  # pragma: no cover - fallback
    append_intervention_reflection = None  # type: ignore

try:
    from ...utils import get_logger
except Exception:  # pragma: no cover - fallback
    def get_logger():
        import logging
        return logging.getLogger(__name__)

from ...utils.timers import TimerRegistry


TAXONOMY_VERSION = "v1"

DRIFT_TYPES = [
    "avoidance",
    "stimulation",
    "emotion_regulation",
    "habit_autopilot",
    "pseudo_productivity",
    "social_pull",
    "break_ran_long",
]

NEEDS = [
    "relief_calm",
    "novelty",
    "certainty",
    "control_order",
    "validation",
    "connection",
    "anger_outlet",
    "rest_sleep",
]

TRIGGERS = [
    "task_unclear",
    "difficulty_spike",
    "fatigue",
    "hunger_low_energy",
    "notification_recommendation",
    "waiting_downtime",
    "stress_event",
    "environment_cue",
]


def _labelize(value):
    return value.replace("_", " ").strip().title()


def _center_window(window, width=560, height=520):
    try:
        window.update_idletasks()
    except Exception:
        pass
    try:
        screen_w = int(window.winfo_screenwidth())
        screen_h = int(window.winfo_screenheight())
    except Exception:
        screen_w, screen_h = 1024, 768
    x = max(0, int((screen_w - width) / 2))
    y = max(0, int((screen_h - height) / 2))
    try:
        window.geometry(f"{width}x{height}+{x}+{y}")
    except Exception:
        pass


def _get_tk_thread_id(widget):
    try:
        return getattr(widget, "_focuscheck_tk_thread_id", None)
    except Exception:
        return None


class InterventionReflectionDialog(tk.Toplevel):
    """Quick reflection dialog shown after a successful intervention."""

    def __init__(self, parent, intervention_id, outcome="success", context=None, taxonomy_version=TAXONOMY_VERSION):
        super().__init__(parent)
        self._parent = parent
        self._context = context or {}
        self._taxonomy_version = taxonomy_version
        self._intervention_id = intervention_id
        self._outcome = outcome
        self._result = None
        self._closed = False

        self.title("Quick Reflection (10s)")
        try:
            self.transient(parent)
        except Exception:
            pass
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self._skip)
        try:
            self.bind("<Escape>", lambda _e: self._skip(), add=True)
            self.bind("<Return>", lambda _e: self._save(), add=True)
        except Exception:
            pass

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Quick Reflection (10s)", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text="Capture the pattern behind the drift. No typing needed.",
            wraplength=520,
        ).pack(anchor="w", pady=(4, 10))

        self._drift_var = tk.StringVar(value="")
        drift_frame = ttk.LabelFrame(container, text="Drift Type (one)")
        drift_frame.pack(fill="x", pady=(6, 8))
        for opt in DRIFT_TYPES:
            ttk.Radiobutton(
                drift_frame,
                text=_labelize(opt),
                value=opt,
                variable=self._drift_var,
            ).pack(anchor="w", padx=6, pady=2)

        self._needs_vars = [tk.BooleanVar(value=False) for _ in NEEDS]
        needs_frame = ttk.LabelFrame(container, text="Needs (up to 3)")
        needs_frame.pack(fill="x", pady=(6, 8))
        for idx, opt in enumerate(NEEDS):
            ttk.Checkbutton(
                needs_frame,
                text=_labelize(opt),
                variable=self._needs_vars[idx],
                command=lambda i=idx: self._enforce_max(self._needs_vars, 3, i),
            ).pack(anchor="w", padx=6, pady=2)

        self._triggers_vars = [tk.BooleanVar(value=False) for _ in TRIGGERS]
        triggers_frame = ttk.LabelFrame(container, text="Triggers (up to 2)")
        triggers_frame.pack(fill="x", pady=(6, 8))
        for idx, opt in enumerate(TRIGGERS):
            ttk.Checkbutton(
                triggers_frame,
                text=_labelize(opt),
                variable=self._triggers_vars[idx],
                command=lambda i=idx: self._enforce_max(self._triggers_vars, 2, i),
            ).pack(anchor="w", padx=6, pady=2)

        intensity_frame = ttk.LabelFrame(container, text="Urge Intensity (1-5)")
        intensity_frame.pack(fill="x", pady=(6, 8))
        self._urge_var = tk.IntVar(value=0)
        row = ttk.Frame(intensity_frame)
        row.pack(anchor="w", padx=6, pady=4)
        for val in range(1, 6):
            ttk.Radiobutton(row, text=str(val), value=val, variable=self._urge_var).pack(side="left", padx=4)

        helpful_frame = ttk.LabelFrame(container, text="Helpfulness (optional, 1-5)")
        helpful_frame.pack(fill="x", pady=(6, 8))
        self._helpful_var = tk.IntVar(value=0)
        row2 = ttk.Frame(helpful_frame)
        row2.pack(anchor="w", padx=6, pady=4)
        for val in range(1, 6):
            ttk.Radiobutton(row2, text=str(val), value=val, variable=self._helpful_var).pack(side="left", padx=4)

        btns = ttk.Frame(container)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Skip", command=self._skip).pack(side="right")
        self._save_btn = ttk.Button(btns, text="Save", command=self._save)
        self._save_btn.pack(side="right", padx=(0, 8))
        try:
            self._save_btn.focus_set()
        except Exception:
            pass

        _center_window(self)

    def _enforce_max(self, var_list, max_count, idx):
        try:
            if not var_list[idx].get():
                return
            count = sum(1 for v in var_list if v.get())
            if count <= max_count:
                return
            var_list[idx].set(False)
            try:
                self.bell()
            except Exception:
                pass
        except Exception:
            pass

    def _collect(self, skipped=False):
        needs = [NEEDS[i] for i, v in enumerate(self._needs_vars) if v.get()]
        triggers = [TRIGGERS[i] for i, v in enumerate(self._triggers_vars) if v.get()]
        data = {
            "event": "intervention_reflection",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "intervention_id": self._intervention_id,
            "outcome": self._outcome,
            "taxonomy_version": self._taxonomy_version,
            "drift_type": self._drift_var.get() or None,
            "needs": needs[:3],
            "triggers": triggers[:2],
            "urge_intensity": int(self._urge_var.get() or 0) or None,
            "helpfulness": int(self._helpful_var.get() or 0) or None,
            "skipped": bool(skipped),
        }
        if self._context:
            data["context"] = self._context
        return data

    def _persist(self, data):
        if append_intervention_reflection is None:
            raise RuntimeError("append_intervention_reflection unavailable")
        append_intervention_reflection(data)

    def _save(self):
        if self._closed:
            return
        self._closed = True
        try:
            data = self._collect(skipped=False)
            try:
                self._persist(data)
            except Exception:
                get_logger().exception("reflection save failed", exc_info=True)
        finally:
            self._result = "saved"
            try:
                self.destroy()
            except Exception:
                pass

    def _skip(self):
        if self._closed:
            return
        self._closed = True
        try:
            data = self._collect(skipped=True)
            try:
                self._persist(data)
            except Exception:
                get_logger().exception("reflection skip failed", exc_info=True)
        finally:
            self._result = "skipped"
            try:
                self.destroy()
            except Exception:
                pass

    @staticmethod
    def prompt(parent, intervention_id, outcome="success", context=None, taxonomy_version=TAXONOMY_VERSION):
        logger = get_logger()
        result_holder = {"value": None}

        def _open():
            try:
                dlg = InterventionReflectionDialog(
                    parent,
                    intervention_id=intervention_id,
                    outcome=outcome,
                    context=context,
                    taxonomy_version=taxonomy_version,
                )
                parent.wait_window(dlg)
                result_holder["value"] = getattr(dlg, "_result", None)
            except Exception:
                logger.exception("reflection dialog failed", exc_info=True)
                result_holder["value"] = None

        tid = _get_tk_thread_id(parent)
        if tid is not None and threading.get_ident() != tid:
            done = threading.Event()
            cancelled = threading.Event()
            dispatch_timers = TimerRegistry(parent)

            def _run_on_ui():
                if cancelled.is_set():
                    done.set()
                    return
                try:
                    _open()
                finally:
                    done.set()

            try:
                dispatch_timers.schedule("reflection-dispatch", 0, _run_on_ui)
                if not done.wait(timeout=30.0):
                    cancelled.set()
            except Exception:
                logger.exception("reflection dialog marshal failed", exc_info=True)
            finally:
                # Cancel a queued dispatch after timeout or completion so a
                # late callback cannot open a dialog after the caller returns.
                dispatch_timers.close()
        else:
            _open()
        return result_holder["value"]


__all__ = ["InterventionReflectionDialog"]
