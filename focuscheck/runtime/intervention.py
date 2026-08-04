"""Application-owned intervention orchestration boundary."""

from __future__ import annotations

import uuid
from typing import Any

from ..utils.logging_utils import get_logger


class InterventionOrchestrator:
    """Own one intervention lease, identity, visibility scope, and cleanup."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def run(
        self,
        settings,
        *,
        preselect_hwnd=None,
        preselect_title=None,
        prompt_ref=None,
        hide_prompt=False,
    ) -> bool:
        app = self._app
        state = getattr(app, "_runtime_state", None)
        if state is not None and not state.begin_intervention():
            app._record_operational_event("intervention", event="rejected", outcome="lease_unavailable")
            return False
        app._intervention_active = True
        intervention_id = uuid.uuid4().hex
        app._active_intervention_id = intervention_id
        app._notify_engine_intervention_state(active=True, source="intervention_started")
        hidden = False
        outcome = "failed"
        app._record_operational_event("intervention", event="started", outcome="started")
        try:
            from ..ui.dialogs.intervention_wizard import InterventionWizard

            if hide_prompt and prompt_ref is not None:
                try:
                    prompt_ref.withdraw()
                    hidden = True
                except Exception:
                    get_logger().exception("intervention prompt hide failed", exc_info=True)
            wizard_factory = getattr(
                getattr(app, "_dependencies", None),
                "intervention_wizard_factory",
                None,
            )
            wizard = (wizard_factory or InterventionWizard)(app.root, settings)
            completed = bool(wizard.run(
                preselect_hwnd=preselect_hwnd,
                preselect_title=preselect_title,
                prompt_ref=prompt_ref,
                hide_prompt=hide_prompt,
                intervention_id=intervention_id,
            ))
            outcome = "completed" if completed else "cancelled"
            return completed
        except Exception:
            try:
                get_logger().exception("intervention coordinator failed", exc_info=True)
            except Exception:
                pass
            return False
        finally:
            if hidden:
                try:
                    prompt_ref.deiconify()
                    prompt_ref.lift()
                    prompt_ref.focus_force()
                except Exception:
                    get_logger().exception("intervention prompt restore failed", exc_info=True)
            app._intervention_active = False
            app._active_intervention_id = None
            try:
                if state is not None:
                    state.end_intervention()
            finally:
                app._notify_engine_intervention_state(active=False, source="intervention_ended")
                app._record_operational_event("intervention", event="ended", outcome=outcome)


__all__ = ["InterventionOrchestrator"]
