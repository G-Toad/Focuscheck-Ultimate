"""Monitoring engine stub for Version 2 prompts."""

import time
import re
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

    def __init__(self, app, activity_provider=None):
        super().__init__(app)
        self._last_hwnd = None
        self._last_switch_mono = time.monotonic()
        self._subpopup_active = False
        self._settings = None
        self._activity_provider = activity_provider or get_active_window_info
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
        if self._timers is not None:
            self._timers.close()

    def _get_activity_info(self):
        info = safe_activity_snapshot(self._activity_provider).as_mapping()
        hwnd = info.get("hwnd")
        now = time.monotonic()
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
        match = self._match_flag(info, flags)
        if not match:
            return
        entry, domain = match
        severity = entry.get("severity", 2)
        self._subpopup_active = True

        def _finish():
            self._subpopup_active = False

        def _update_cooldown():
            try:
                entry["last_dismissed"] = time.time()
                if entry.get("allow_once"):
                    entry["allow_once"] = False
                save_settings(settings)
            except Exception:
                pass

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
            _update_cooldown()
            _finish()

        if severity >= 3:
            _on_yes()
            return

        dialog = V2SubPopupDialog(
            self.app.root,
            domain=domain,
            severity=severity,
            on_yes=_on_yes,
            on_no=_on_no,
        )
        try:
            dialog.grab_set()
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
                    if (time.time() - float(last)) < (cooldown * 60):
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
