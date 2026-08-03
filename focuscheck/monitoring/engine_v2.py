"""Monitoring engine stub for Version 2 prompts."""

import copy
import time
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from ..settings.website_flags import normalize_website_domain

from .base import BaseEngine
from ..platform_specific.activity_probe import get_active_window_info
from ..ui.dialogs.v2_prompt_dialog import V2PromptDialog
from ..ui.dialogs.v2_subpopup_dialog import V2SubPopupDialog
from ..ui.dialogs.intervention_wizard import InterventionWizard
from ..settings import save_settings
from ..utils.timers import TimerRegistry
from .activity import safe_activity_snapshot

try:
    from ..utils.logging_utils import get_logger
except Exception:  # pragma: no cover - fallback
    def get_logger():
        import logging
        return logging.getLogger(__name__)


class EngineV2(BaseEngine):
    """Activity-aware monitoring engine (Version 2)."""

    name = "v2"

    def __init__(self, app, activity_provider=None, clock=None):
        super().__init__(app)
        self._last_hwnd = None
        self._subpopup_active = False
        self._subpopup_dialog = None
        self._subpopup_generation = 0
        self._settings = None
        self._activity_provider = activity_provider or get_active_window_info
        runtime_clock = getattr(getattr(app, "_runtime_state", None), "clock", None)
        clock_source = clock if clock is not None else runtime_clock
        if clock_source is None:
            self._activity_clock = None
        else:
            def _activity_now():
                try:
                    value = clock_source() if callable(clock_source) else clock_source.now_utc()
                    if isinstance(value, datetime):
                        return value
                except (AttributeError, TypeError, ValueError, OverflowError):
                    pass
                return datetime.now(timezone.utc)

            self._activity_clock = _activity_now
        monotonic = getattr(clock_source, "monotonic", None)

        def _safe_monotonic():
            if callable(monotonic):
                try:
                    return float(monotonic())
                except (TypeError, ValueError, OverflowError):
                    pass
            return time.monotonic()

        self._monotonic = _safe_monotonic
        self._last_switch_mono = self._monotonic()
        if callable(clock):
            self._now = clock
        elif clock_source is not None and hasattr(clock_source, "now_utc"):
            def _safe_now():
                try:
                    return clock_source.now_utc().timestamp()
                except (AttributeError, TypeError, ValueError, OverflowError):
                    return time.time()
            self._now = _safe_now
        else:
            self._now = time.time
        self._timers = TimerRegistry(getattr(app, "root", None)) if getattr(app, "root", None) is not None else None

    def create_prompt(self, settings, slot_info):
        activity_info = self._get_activity_info()
        return V2PromptDialog(
            self.app.root,
            settings,
            on_submit=self.app._on_prompt_done,
            slot_start_dt=slot_info,
            activity_info=activity_info,
            app_ref=self.app,
            taskdb=getattr(self.app, "taskdb", None),
        )

    def on_settings_updated(self, settings):
        self._settings = settings
        self._schedule_subpopup_check()

    def shutdown(self):
        self._subpopup_generation += 1
        dialog = self._subpopup_dialog
        self._subpopup_dialog = None
        self._subpopup_active = False
        if dialog is not None:
            try:
                dialog.destroy()
            except Exception:
                pass
        if self._timers is not None:
            self._timers.close()

    def _get_activity_info(self):
        snapshot = safe_activity_snapshot(
            self._activity_provider,
            clock=getattr(self, "_activity_clock", None),
        )
        now_utc = None
        activity_clock = getattr(self, "_activity_clock", None)
        if callable(activity_clock):
            try:
                now_utc = activity_clock()
            except Exception:
                now_utc = None
        info = snapshot.as_mapping()
        age_seconds = snapshot.age_seconds(now=now_utc)
        info["activity_age_s"] = age_seconds
        info["activity_fresh"] = snapshot.is_fresh(now=now_utc)
        info["activity_usable"] = bool(info["activity_fresh"] and not snapshot.errors)
        hwnd = info.get("hwnd")
        now = getattr(self, "_monotonic", time.monotonic)()
        if hwnd and hwnd == self._last_hwnd:
            duration = now - self._last_switch_mono
        else:
            self._last_hwnd = hwnd
            self._last_switch_mono = now
            duration = 0.0
        info["active_duration_s"] = duration
        return info

    def _schedule_subpopup_check(self):
        if self._timers is None or self._timers.closed:
            return
        self._timers.schedule(
            "website-subpopup",
            3000,
            self._subpopup_tick,
            interval_ms=3000,
        )

    def _subpopup_tick(self):
        if self._should_check_subpopup():
            self._maybe_show_subpopup()

    def _should_check_subpopup(self):
        if self._subpopup_active:
            return False
        if getattr(self.app, "_current_prompt", None) is not None:
            return False
        if bool(getattr(self.app, "_intervention_active", False)):
            return False
        settings = self._settings or getattr(self.app, "settings", {})
        runtime_state = getattr(self.app, "_runtime_state", None)
        if runtime_state is not None:
            try:
                # RuntimeStateCoordinator is authoritative for manual,
                # snooze, and guard pause composition.
                return not runtime_state.is_effectively_paused()
            except Exception:
                # Preserve standalone/test adapter compatibility, but do not
                # allow a broken coordinator to enable a website intervention.
                return False
        try:
            if bool(settings.get("paused", False)):
                return False
            if bool(settings.get("pause_when_inactive_or_lid_closed", True)):
                guard = getattr(self.app, "guard", None)
                if guard is not None and guard.should_pause():
                    return False
        except Exception:
            pass
        return True

    def _maybe_show_subpopup(self):
        settings = self._settings or getattr(self.app, "settings", {})
        flags = settings.get("website_flags", []) or []
        if not flags:
            return
        info = self._get_activity_info()
        # A provider error or stale timestamp must never trigger a website
        # intervention, even if a partial title/URL happens to match.
        if info.get("activity_usable", True) is not True:
            return
        match = self._match_flag(info, flags)
        if not match:
            return
        entry, domain = match
        severity = entry.get("severity", 2)
        self._subpopup_active = True
        self._subpopup_generation = getattr(self, "_subpopup_generation", 0) + 1
        generation = self._subpopup_generation

        try:
            entry_index = next(index for index, candidate in enumerate(flags) if candidate is entry)
        except StopIteration:
            entry_index = None

        def _persist_flag_update(values):
            """Persist one flag change through App composition when available."""
            app_persist = getattr(type(self.app), "_persist_settings_draft", None)
            persist = getattr(self.app, "_persist_settings_draft", None)
            if entry_index is not None and callable(app_persist) and callable(persist):
                candidate = copy.deepcopy(settings)
                candidate_flags = candidate.get("website_flags", []) or []
                if entry_index >= len(candidate_flags):
                    return False
                candidate_flags[entry_index].update(values)
                candidate["website_flags"] = candidate_flags
                try:
                    result = persist(candidate)
                except Exception:
                    return False
                committed = getattr(result, "committed_settings", None)
                if result and isinstance(committed, dict):
                    settings.clear()
                    settings.update(committed)
                return bool(result)

            # Standalone engines retain compatibility with the module-level
            # repository, but do not leave an in-memory mutation after failure.
            previous = {key: entry.get(key) for key in values}
            entry.update(values)
            try:
                result = save_settings(settings)
            except Exception:
                result = False
            if not result:
                for key, value in previous.items():
                    if value is None:
                        entry.pop(key, None)
                    else:
                        entry[key] = value
            return bool(result)

        def _finish():
            if generation != self._subpopup_generation:
                return
            self._subpopup_active = False
            self._subpopup_dialog = None

        def _update_cooldown():
            try:
                _persist_flag_update({"last_dismissed": self._now(), "allow_once": False})
            except Exception:
                pass

        def _dismiss_once_or_start_cooldown():
            """Consume one configured dismissal before starting cooldown."""
            if not entry.get("allow_once"):
                _update_cooldown()
                return
            # A one-time dismissal is durable but deliberately does not set
            # last_dismissed; a failed write leaves the bypass available.
            _persist_flag_update({"allow_once": False})

        def _on_yes():
            try:
                runner = getattr(self.app, "run_intervention", None) if hasattr(type(self.app), "run_intervention") else None
                if callable(runner):
                    completed = bool(runner(
                        settings,
                        preselect_hwnd=info.get("hwnd"),
                        preselect_title=info.get("title"),
                    ))
                else:
                    wizard = InterventionWizard(self.app.root, settings)
                    completed = bool(wizard.run(preselect_hwnd=info.get("hwnd"), preselect_title=info.get("title")))
                # A cancelled or failed intervention must remain retryable;
                # only a completed intervention starts the cooldown.
                if completed:
                    _update_cooldown()
            finally:
                _finish()

        def _on_no():
            _dismiss_once_or_start_cooldown()
            _finish()

        if severity >= 3:
            # Title-only activity is useful for a warning but is not strong
            # enough evidence for an immediate intervention.
            if info.get("confidence") != "high":
                _finish()
                return
            _on_yes()
            return

        try:
            dialog = V2SubPopupDialog(
                self.app.root,
                domain=domain,
                severity=severity,
                on_yes=_on_yes,
                on_no=_on_no,
            )
            self._subpopup_dialog = dialog
        except Exception:
            _finish()
            try:
                get_logger().exception("v2 subpopup construction failed", exc_info=True)
            except Exception:
                pass
            return
        try:
            dialog.grab_set()
        except Exception:
            _finish()
            try:
                dialog.destroy()
            except Exception:
                pass

    def _match_flag(self, info, flags):
        title = (info.get("title") or "").lower()
        url = (info.get("url") or "").lower()
        host = ""
        if url:
            try:
                parsed = urlparse(url if "://" in url else f"https://{url}")
                host = (parsed.hostname or "").lower()
            except Exception:
                host = ""
        for entry in flags:
            try:
                if not entry.get("enabled", True):
                    continue
                domain = normalize_website_domain(entry.get("domain", ""))
                if not domain:
                    continue
                cooldown = int(entry.get("cooldown_minutes", 5))
                last = entry.get("last_dismissed")
                if isinstance(last, (int, float)) and cooldown > 0:
                    if (self._now() - float(last)) < (cooldown * 60):
                        continue
                if host and self._domain_matches(domain, host):
                    return entry, domain
                # A parsed host is authoritative. Title fallback is only for
                # providers that cannot supply a URL; never let an unrelated
                # page title override a valid non-matching host.
                tokens = [domain.split(".")[0]] if "." in domain else [domain]
                title_fallback = not host and any(
                    tok and re.search(rf"(?<![a-z0-9]){re.escape(tok)}(?![a-z0-9])", title)
                    for tok in tokens
                )
                if title_fallback:
                    return entry, domain
            except Exception:
                continue
        return None

    def _domain_matches(self, domain, host):
        if not domain or not host:
            return False
        if host == domain:
            return True
        # Allow subdomain match (e.g., www.reddit.com endswith reddit.com)
        return host.endswith("." + domain)
