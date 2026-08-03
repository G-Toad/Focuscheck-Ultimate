"""
Task management mixin for PromptDialog.

Contains methods for task panel rendering, task lifecycle management,
and analytics display.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone, timedelta
from ....utils.task_payload import build_task_payload

try:
    from ....utils import log_exception
except ImportError:
    def log_exception(msg):
        pass


class TaskManagementMixin:
    """Mixin for task management functionality in PromptDialog."""

    def _task_now_utc(self):
        """Return the composed runtime UTC clock, with a safe standalone fallback."""
        source = getattr(self, "_task_clock", None)
        if source is None:
            runtime_state = getattr(getattr(self, "app_ref", None), "_runtime_state", None)
            source = getattr(runtime_state, "clock", None)
        if source is None:
            source = getattr(getattr(self, "taskdb", None), "_clock", None)
        try:
            value = source() if callable(source) else source.now_utc()
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                return value.astimezone(timezone.utc)
        except (AttributeError, TypeError, ValueError, OverflowError):
            pass
        return datetime.now(timezone.utc)

    def _toggle_task_entry(self, _evt=None):
        """
        Toggle inline task entry form visibility.

        Shows or hides the task entry form for creating new tasks.

        Args:
            _evt: Optional event object
        """
        if not self.taskdb:
            return
        # Toggle inline task entry frame below panel or time label
        if getattr(self, "_task_entry_frame", None) is not None:
            try:
                self._task_entry_frame.destroy()
            except Exception:
                pass
            self._task_entry_frame = None
            return
        self._task_entry_frame = tk.Frame(self, bg="#111", highlightthickness=1, highlightbackground="#333")
        self._task_entry_frame.pack(padx=14, pady=(6,0), fill="x")
        tk.Label(self._task_entry_frame, text="New Task Title", fg="#ddd", bg="#111").grid(row=0, column=0, sticky="w", padx=8, pady=(6,0))
        title_var = tk.StringVar()
        ttk.Entry(self._task_entry_frame, textvariable=title_var, width=48).grid(row=0, column=1, sticky="we", padx=8, pady=(6,0))
        tk.Label(self._task_entry_frame, text="Why", fg="#bbb", bg="#111").grid(row=1, column=0, sticky="w", padx=8)
        why_var = tk.StringVar(); ttk.Entry(self._task_entry_frame, textvariable=why_var, width=48).grid(row=1, column=1, sticky="we", padx=8)
        tk.Label(self._task_entry_frame, text="Consequences", fg="#bbb", bg="#111").grid(row=2, column=0, sticky="w", padx=8)
        cons_var = tk.StringVar(); ttk.Entry(self._task_entry_frame, textvariable=cons_var, width=48).grid(row=2, column=1, sticky="we", padx=8)
        tk.Label(self._task_entry_frame, text="Expected completion (mins or HH:MM)", fg="#bbb", bg="#111").grid(row=3, column=0, sticky="w", padx=8)
        due_var = tk.StringVar(); ttk.Entry(self._task_entry_frame, textvariable=due_var, width=20).grid(row=3, column=1, sticky="w", padx=8)
        btns = ttk.Frame(self._task_entry_frame); btns.grid(row=4, column=0, columnspan=2, sticky="e", padx=8, pady=(6,8))
        def save_inline():
            data = build_task_payload(title_var.get(), why_var.get(), cons_var.get(), due_var.get())
            self._on_new_task(data)
            try:
                self._task_entry_frame.destroy()
            except Exception:
                pass
            self._task_entry_frame = None
        def cancel_task_entry():
            try:
                if self._task_entry_frame:
                    self._task_entry_frame.destroy()
            except Exception:
                pass
            finally:
                self._task_entry_frame = None
        ttk.Button(btns, text="Cancel", command=cancel_task_entry).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=save_inline).pack(side="right")

    def _ensure_task_entry_visible(self):
        """
        Ensure task entry form is visible.

        Shows the task entry form if not already displayed.
        """
        if not self.taskdb:
            return
        try:
            fr = getattr(self, "_task_entry_frame", None)
            exists = bool(fr is not None and int(fr.winfo_exists()) == 1)
        except Exception:
            exists = False
        if not exists:
            try:
                self._toggle_task_entry(None)
            except Exception:
                pass

    def _on_new_task(self, task_data):
        """
        Handle creation of a new task.

        Args:
            task_data: Dictionary with task fields (title, why, consequences, due_utc)
        """
        try:
            title = task_data.get("title", "").strip()
            why = task_data.get("why", "").strip()
            cons = task_data.get("consequences", "").strip()
            due_iso = task_data.get("due_utc")
            if not title:
                return
            task_id = self.taskdb.start_task(
                title=title,
                due_utc=due_iso,
                why=why,
                consequences=cons,
            )
            if not task_id:
                messagebox.showerror("Task Error", "The task could not be saved.")
                return
            self._render_task_panel()
            self._refresh_analytics()
        except Exception:
            log_exception("Task UI: failed to create task")
            messagebox.showerror("Task Error", "The task could not be saved.")

    def _render_task_panel(self):
        """
        Render the task panel showing active task or prompt to create one.

        Displays task information, deadline, evaluation window status,
        and action buttons.
        """
        if not self._task_panel or not self.taskdb:
            return
        # Preserve open change form while updating the rest
        keep_form = getattr(self, "_task_change_form", None)
        try:
            if keep_form is not None and int(keep_form.winfo_exists()) == 1:
                try:
                    keep_form.pack_forget()
                except Exception:
                    pass
            else:
                keep_form = None
        except Exception:
            keep_form = None
        for w in list(self._task_panel.winfo_children()):
            if keep_form is not None and w == keep_form:
                continue
            try:
                w.destroy()
            except Exception:
                pass
        active = None
        try:
            active = self.taskdb.get_active()
        except Exception:
            active = None
        if not active:
            # Header row with History button even when no active task
            header_row = tk.Frame(self._task_panel, bg="#111")
            header_row.pack(fill="x", padx=8, pady=(6,0))
            hist = tk.Label(header_row, text="History", fg="#7fffb7", bg="#111", cursor="hand2", font=("Segoe UI", 9, "underline"))
            hist.pack(side="right")
            hist.bind("<Button-1>", self._open_task_history)
            # No task message
            lbl = tk.Label(self._task_panel, text="No task set. Click ? Task to define one.", fg="#bbb", bg="#111", font=("Segoe UI", 10))
            lbl.pack(anchor="w", padx=8, pady=6)
            return

        # Build active task UI
        title = active.get("title", "")
        why = active.get("why", "")
        cons = active.get("consequences", "")
        due_iso = active.get("due_utc")
        due_txt = "No due time"
        overdue = False
        time_left = ""
        try:
            if due_iso:
                due_dt = datetime.fromisoformat(due_iso)
                local_due = due_dt.astimezone().strftime("%Y-%m-%d %H:%M")
                now = self._task_now_utc()
                if now > due_dt:
                    overdue = True
                    due_txt = f"Due: {local_due} (LIMIT REACHED)"
                else:
                    rem = due_dt - now
                    mm = int(rem.total_seconds() // 60)
                    ss = int(rem.total_seconds() % 60)
                    due_txt = f"Due: {local_due}"
                    time_left = f"Time left: {mm}m {ss}s"
        except Exception:
            pass

        fg = "#ffb0b0" if overdue else "#cfe9cf"
        # Header row with History button on the right
        header_row = tk.Frame(self._task_panel, bg="#111")
        header_row.pack(fill="x", padx=8, pady=(6,0))
        head = tk.Label(header_row, text=f"Current task: {title}", fg="#eaeaea", bg="#111", font=("Segoe UI", 11, "bold"))
        head.pack(side="left")
        hist = tk.Label(header_row, text="History", fg="#7fffb7", bg="#111", cursor="hand2", font=("Segoe UI", 9, "underline"))
        hist.pack(side="right")
        hist.bind("<Button-1>", self._open_task_history)
        sub = tk.Label(self._task_panel, text=f"Why: {why}", fg="#ddd", bg="#111", font=("Segoe UI", 10))
        sub.pack(anchor="w", padx=8)
        sub2 = tk.Label(self._task_panel, text=f"If not done: {cons}", fg="#ddd", bg="#111", font=("Segoe UI", 10))
        sub2.pack(anchor="w", padx=8)
        due_l = tk.Label(self._task_panel, text=due_txt + (f"  |  {time_left}" if time_left else ""), fg=fg, bg="#111", font=("Segoe UI", 10, "bold" if overdue else ""))
        due_l.pack(anchor="w", padx=8, pady=(0,6))

        # Decision prompt depending on evaluation mode
        self._task_decision_required = False
        self._task_decision_task_id = None
        self._focus_prompt_open = False
        self._task_decision_can_fail = False

        try:
            window_m = int(self.settings.get("tasks_decision_window_minutes", 10))
        except Exception:
            window_m = 10
        decision_enabled = bool(self.settings.get("tasks_decision_prompt_enabled", True))
        decision_due = False
        auto_failed = False
        eval_mode = str(self.settings.get("tasks_evaluation_mode", "before")).strip().lower()
        try:
            if due_iso:
                due_dt = datetime.fromisoformat(due_iso)
                now = self._task_now_utc()
                if eval_mode == "before":
                    window_start = due_dt - timedelta(minutes=window_m)
                    if now >= due_dt:
                        self._task_decision_can_fail = True
                        # Auto-fail: evaluation window ended at due time
                        try:
                            if active.get("status") == "active":
                                auto_failed = bool(self.taskdb.mark_failed(active.get("id"), timed_out=True))
                        except Exception:
                            pass
                        decision_due = False
                    elif now >= window_start:
                        decision_due = True
                else:  # after
                    window_end = due_dt + timedelta(minutes=window_m)
                    if now < due_dt:
                        decision_due = False
                    elif now >= due_dt and now < window_end:
                        decision_due = True
                    else:
                        self._task_decision_can_fail = True
                        # Auto-fail after window end
                        try:
                            if active.get("status") == "active":
                                auto_failed = bool(self.taskdb.mark_failed(active.get("id"), timed_out=True))
                        except Exception:
                            pass
                        decision_due = False
        except Exception:
            decision_due = False

        # The transition removed the active task; never build stale controls
        # against the now-failed record.
        if auto_failed:
            self._render_task_panel()
            return

        if decision_enabled and decision_due:
            self._task_decision_required = True
            self._task_decision_task_id = active.get("id")
            if eval_mode == "before":
                msg = "Approaching deadline. Decide: PASSED or FAILED."
            else:
                msg = "Evaluation period started. Mark task as PASSED or FAILED."
            warn = tk.Label(self._task_panel, text=msg, fg="#ff6b6b", bg="#111", font=("Segoe UI", 10, "bold"))
            warn.pack(anchor="w", padx=8, pady=(0,6))
        else:
            # Informational guidance based on mode
            if decision_enabled and due_iso:
                try:
                    due_dt = datetime.fromisoformat(due_iso)
                    now = self._task_now_utc()
                    if eval_mode == "after":
                        window_end = due_dt + timedelta(minutes=window_m)
                        if now < due_dt:
                            info = tk.Label(self._task_panel, text="Work until the limit; evaluation will be after the deadline.", fg="#aaa", bg="#111", font=("Segoe UI", 9))
                            info.pack(anchor="w", padx=8, pady=(0,6))
                        elif now >= due_dt and now < window_end:
                            remain = window_end - now
                            mm = int(remain.total_seconds() // 60)
                            ss = int(remain.total_seconds() % 60)
                            info = tk.Label(self._task_panel, text=f"Limit reached; evaluation in {mm}m {ss}s.", fg="#ffbd6b", bg="#111", font=("Segoe UI", 9))
                            info.pack(anchor="w", padx=8, pady=(0,6))
                        elif now >= window_end:
                            info = tk.Label(self._task_panel, text="Evaluation window timed out - recorded as FAILED.", fg="#ff6b6b", bg="#111", font=("Segoe UI", 9, "bold"))
                            info.pack(anchor="w", padx=8, pady=(0,6))
                    else:  # before mode
                        window_start = due_dt - timedelta(minutes=window_m)
                        if now < window_start:
                            info = tk.Label(self._task_panel, text=f"Decision window opens {window_m}m before deadline.", fg="#aaa", bg="#111", font=("Segoe UI", 9))
                            info.pack(anchor="w", padx=8, pady=(0,6))
                except Exception:
                    pass

        # Action buttons
        row = tk.Frame(self._task_panel, bg="#111")
        row.pack(anchor="w", padx=6, pady=(0,6))
        done_btn = tk.Button(row, text="?", fg="#0f0", bg="#222", font=("Segoe UI", 12, "bold"), width=3,
                             command=lambda tid=active["id"], d=due_iso: self._task_mark_done(tid, d))
        change_btn = tk.Button(row, text="?", fg="#f33", bg="#222", font=("Segoe UI", 12, "bold"), width=3,
                               command=lambda tid=active["id"]: self._show_change_form(tid))
        done_btn.pack(side="left", padx=(2,6))
        change_btn.pack(side="left")

        # Re-attach preserved change form (if any)
        if keep_form is not None:
            try:
                keep_form.pack(fill="x", padx=8, pady=(0,6))
            except Exception:
                pass

        # Live countdown refresh
        if self._task_timer_id:
            self._cancel_timer(self._task_timer_id)
            self._task_timer_id = None
        try:
            self._task_timer_id = self._schedule_timer(1000, self._render_task_panel)
        except Exception:
            pass

    def _task_mark_done(self, task_id, due_iso):
        """
        Mark a task as done (completed or failed based on deadline).

        Args:
            task_id: ID of the task to mark
            due_iso: ISO format due date string
        """
        try:
            # If overdue relative to due_iso, mark as failed even if done
            is_overdue = False
            try:
                if due_iso:
                    due_dt = datetime.fromisoformat(due_iso)
                    is_overdue = self._task_now_utc() >= due_dt
            except Exception:
                is_overdue = False
            if is_overdue:
                # Mark as failed with timed_out=True to distinguish from manual fails
                saved = self.taskdb.mark_failed(task_id, timed_out=True)
            else:
                saved = self.taskdb.mark_completed(task_id)
            if not saved:
                messagebox.showerror("Task Error", "The task status could not be saved.")
                return
        except Exception:
            log_exception("Task UI: failed to save task status")
            messagebox.showerror("Task Error", "The task status could not be saved.")
            return
        self._task_decision_required = False
        self._task_decision_task_id = None
        self._focus_prompt_open = False
        self._render_task_panel()
        self._refresh_analytics()

    def _show_change_form(self, task_id):
        """
        Show inline form for changing current task.

        Args:
            task_id: ID of the task to change
        """
        # Inline change form under task panel (preserved across refresh)
        try:
            if getattr(self, "_task_change_form", None) is not None and int(self._task_change_form.winfo_exists()) == 1:
                try: self._task_change_form.lift()
                except Exception: pass
                return
        except Exception:
            pass
        form = tk.Frame(self._task_panel, bg="#111")
        form.pack(fill="x", padx=8, pady=(0,6))
        self._task_change_form = form
        tk.Label(form, text="Why change?", fg="#ddd", bg="#111").grid(row=0, column=0, sticky="w")
        reason_var = tk.StringVar()
        ttk.Entry(form, textvariable=reason_var, width=50).grid(row=0, column=1, sticky="we")
        tk.Label(form, text="New task (optional)", fg="#bbb", bg="#111").grid(row=1, column=0, sticky="w", pady=(4,0))
        new_title = tk.StringVar(); ttk.Entry(form, textvariable=new_title, width=40).grid(row=1, column=1, sticky="we", pady=(4,0))
        tk.Label(form, text="Due (mins or HH:MM)", fg="#bbb", bg="#111").grid(row=2, column=0, sticky="w")
        new_due = tk.StringVar(); ttk.Entry(form, textvariable=new_due, width=16).grid(row=2, column=1, sticky="w")
        tk.Label(form, text="Why", fg="#bbb", bg="#111").grid(row=3, column=0, sticky="w")
        new_why = tk.StringVar(); ttk.Entry(form, textvariable=new_why, width=40).grid(row=3, column=1, sticky="we")
        tk.Label(form, text="Consequences", fg="#bbb", bg="#111").grid(row=4, column=0, sticky="w")
        new_cons = tk.StringVar(); ttk.Entry(form, textvariable=new_cons, width=40).grid(row=4, column=1, sticky="we")
        btns = ttk.Frame(form); btns.grid(row=5, column=0, columnspan=2, sticky="e", pady=(6,0))
        def save_change():
            reason = reason_var.get().strip()
            if not reason:
                messagebox.showerror("Required", "Please provide a reason for changing the task.")
                return
            # Optional new task
            new_task = None
            nt = new_title.get().strip()
            if nt:
                new_task = build_task_payload(nt, new_why.get(), new_cons.get(), new_due.get())
            try:
                atomic_change = getattr(self.taskdb, "change_task", None)
                if callable(atomic_change):
                    saved = atomic_change(task_id, reason, new_task=new_task)
                else:
                    # Compatibility for older task-store adapters.
                    saved = self.taskdb.mark_changed(task_id, reason)
                    if saved and new_task is not None:
                        saved = self.taskdb.start_task(
                            title=new_task["title"],
                            due_utc=new_task["due_utc"],
                            why=new_task["why"],
                            consequences=new_task["consequences"],
                        )
                if not saved:
                    messagebox.showerror("Task Error", "The task change could not be saved.")
                    return
            except Exception:
                log_exception("Task UI: failed to change task")
                messagebox.showerror("Task Error", "The task change could not be saved.")
                return
            try:
                form.destroy()
            except Exception:
                pass
            try:
                self._task_change_form = None
            except Exception:
                pass
            self._render_task_panel()
            self._refresh_analytics()
        def cancel_change():
            try: form.destroy()
            finally:
                try: self._task_change_form = None
                except Exception: pass
        ttk.Button(btns, text="Cancel", command=cancel_change).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=save_change).pack(side="right")

    def _refresh_analytics(self):
        """
        Refresh task analytics display.

        Updates the analytics label with current task statistics.
        """
        if not self._analytics_lbl or not self.taskdb:
            return
        try:
            tscale = str(self.settings.get("tasks_analytics_timescale", "lifetime"))
            changed_as_fail = bool(self.settings.get("tasks_change_counts_as_fail", True))
            stats = self.taskdb.analytics_counts(timescale=tscale, treat_changed_as_fail=changed_as_fail)
            self._analytics_lbl.config(text=f"? Completed: {stats['completed']}   ? Failed: {stats['failed']}   ~ Changed: {stats['changed']}   ? Timed-out: {stats.get('timed_out',0)}")
        except Exception:
            try:
                self._analytics_lbl.config(text="")
            except Exception:
                pass

    def _open_task_history(self, _evt=None):
        """
        Open the task history window.

        Args:
            _evt: Optional event object
        """
        if not self.taskdb:
            messagebox.showerror("Unavailable", "Task database not available.")
            return
        try:
            # Need to reach the top-level ui.windows module (two levels up)
            from ...windows import TaskHistoryWindow
            TaskHistoryWindow(self, self.taskdb)
        except Exception:
            log_exception("failed to open TaskHistoryWindow")
