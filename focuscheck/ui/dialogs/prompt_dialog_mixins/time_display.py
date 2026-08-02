"""
Time display mixin for PromptDialog.

Contains methods for displaying and updating time information,
including elapsed time and task remaining time.
"""

from datetime import datetime, timedelta, timezone


class TimeDisplayMixin:
    """Mixin for time display functionality in PromptDialog."""

    def _format_now(self):
        """
        Format current time according to settings.

        Returns:
            Tuple of (datetime_now, formatted_string)
        """
        now = datetime.now()
        show_secs = bool(self.settings.get("time_info_show_seconds", False))
        use_12h = bool(self.settings.get("time_info_12h", False))
        if use_12h:
            fmt = "%I:%M:%S %p" if show_secs else "%I:%M %p"
            s = now.strftime(fmt).lstrip("0")
        else:
            fmt = "%H:%M:%S" if show_secs else "%H:%M"
            s = now.strftime(fmt)
        return now, s

    def _minutes_passed(self, now):
        """
        Calculate minutes passed based on configured mode.

        Args:
            now: Current datetime object

        Returns:
            Integer minutes passed since reference point
        """
        mode = str(self.settings.get("time_info_mode", "hour")).lower().strip()
        if mode == "day":
            return now.hour * 60 + now.minute
        if mode == "anchor":
            anc = str(self.settings.get("time_info_anchor_hhmm", "09:00"))
            try:
                hh, mm = anc.split(":"); hh = int(hh); mm = int(mm)
                anchor = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if now < anchor:
                    # use yesterday's anchor as most recent
                    anchor = anchor - timedelta(days=1)
                delta = now - anchor
                return max(0, int(delta.total_seconds() // 60))
            except Exception:
                return now.hour * 60 + now.minute
        if mode == "launch":
            try:
                if self.app_ref is not None and hasattr(self.app_ref, "_start_wall"):
                    delta = now - getattr(self.app_ref, "_start_wall")
                    return max(0, int(delta.total_seconds() // 60))
            except Exception:
                pass
            return now.minute
        # default hour mode
        return now.minute

    def _tick_time_info(self):
        """
        Update time info label periodically.

        This method is called on a timer to refresh the time display
        with current time and minutes passed information.
        """
        if self._closed or self._time_lbl is None:
            return
        try:
            if not self.settings.get("show_time_info", False):
                if self._time_lbl.winfo_manager():
                    try:
                        self._time_lbl.pack_forget()
                    except Exception:
                        pass
            else:
                if not self._time_lbl.winfo_manager():
                    try:
                        self._time_lbl.pack(pady=(6,0))
                    except Exception:
                        pass
                now, cur = self._format_now()
                mins = self._minutes_passed(now)
                mode = str(self.settings.get("time_info_mode", "hour")).lower().strip()
                extra = ""
                if mode == "anchor":
                    extra = f" since {self.settings.get('time_info_anchor_hhmm','09:00')}"
                elif mode == "launch":
                    extra = " since launch"
                # Optional task remaining
                task_left_txt = ""
                try:
                    if bool(self.settings.get("time_info_show_task_remaining", False)) and self.taskdb:
                        active = self.taskdb.get_active()
                        due_iso = active.get("due_utc") if active else None
                        if due_iso:
                            due_dt = datetime.fromisoformat(due_iso)
                            now_utc = datetime.now(timezone.utc)
                            rem = int((due_dt - now_utc).total_seconds())
                            if rem > 0:
                                mm, ss = divmod(rem, 60)
                                hh, mm = divmod(mm, 60)
                                if hh:
                                    task_left_txt = f" | task left {hh}h{mm:02d}m"
                                else:
                                    task_left_txt = f" | task left {mm}m{ss:02d}s"
                except Exception:
                    pass
                self._time_lbl.config(text=f"{mins} minutes passed{extra} | {cur}{task_left_txt}")
        except Exception:
            pass
        finally:
            try:
                refresh = int(self.settings.get("time_info_refresh_ms", 1000))
            except Exception:
                refresh = 1000
            self.after(refresh, self._tick_time_info)

    def _start_time_info(self):
        """
        Begin periodic updates of time info display.

        Initiates the timer loop for updating time information.
        """
        # begin periodic updates
        self._tick_time_info()
