"""Single-owner runtime pause and lifecycle state."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, MutableMapping, Any
from ..utils.clock import SystemClock


@dataclass
class RuntimeSnapshot:
    manual_paused: bool = False
    snooze_until_utc: str = ""
    guard_reasons: set[str] = field(default_factory=set)
    prompt_active: bool = False
    intervention_active: bool = False
    shutdown_requested: bool = False

    @property
    def effectively_paused(self) -> bool:
        return self.manual_paused or self.snooze_active() or bool(self.guard_reasons)

    def snooze_active(self, now: datetime | None = None) -> bool:
        if not self.snooze_until_utc:
            return False
        try:
            until = datetime.fromisoformat(self.snooze_until_utc.replace("Z", "+00:00"))
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            current = now or datetime.now(timezone.utc)
            return until.astimezone(timezone.utc) > current.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return False


class RuntimeStateCoordinator:
    """Own state transitions and persist related settings atomically."""

    def __init__(
        self,
        settings: MutableMapping[str, Any],
        persist: Callable[[MutableMapping[str, Any]], bool] | None = None,
        clock: Any | None = None,
    ) -> None:
        self.settings = settings
        self._persist = persist
        self.clock = clock or SystemClock()
        self.snapshot = RuntimeSnapshot(
            manual_paused=bool(settings.get("paused", False)),
            snooze_until_utc=str(settings.get("snooze_until_utc", "") or ""),
        )

    def refresh_from_settings(self, settings: MutableMapping[str, Any]) -> None:
        """Adopt a reloaded settings document without losing runtime leases."""
        self.settings = settings
        self.snapshot.manual_paused = bool(settings.get("paused", False))
        self.snapshot.snooze_until_utc = str(settings.get("snooze_until_utc", "") or "")

    def _commit(self, mutate: Callable[[], None]) -> bool:
        before_settings = deepcopy(dict(self.settings))
        before_snapshot = deepcopy(self.snapshot)
        mutate()
        self.settings["paused"] = self.snapshot.manual_paused or bool(self.snapshot.snooze_until_utc)
        self.settings["snooze_until_utc"] = self.snapshot.snooze_until_utc
        if self._persist is not None:
            try:
                if not self._persist(self.settings):
                    self.settings.clear()
                    self.settings.update(before_settings)
                    self.snapshot = before_snapshot
                    return False
            except Exception:
                self.settings.clear()
                self.settings.update(before_settings)
                self.snapshot = before_snapshot
                return False
        return True

    def set_manual_paused(self, value: bool) -> bool:
        value = bool(value)
        if self.snapshot.manual_paused == value:
            return False
        return self._commit(lambda: setattr(self.snapshot, "manual_paused", value))

    def set_snooze_until(self, until: datetime | str | None) -> bool:
        if until is None:
            value = ""
        elif isinstance(until, datetime):
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            value = until.astimezone(timezone.utc).isoformat()
        else:
            value = str(until)
        if self.snapshot.snooze_until_utc == value:
            return False
        return self._commit(lambda: setattr(self.snapshot, "snooze_until_utc", value))

    def clear_snooze(self) -> bool:
        return self.set_snooze_until(None)

    def set_guard_reason(self, reason: str, active: bool) -> None:
        reason = str(reason).strip()
        if not reason:
            return
        if active:
            self.snapshot.guard_reasons.add(reason)
        else:
            self.snapshot.guard_reasons.discard(reason)

    def begin_prompt(self) -> bool:
        if self.snapshot.shutdown_requested or self.snapshot.prompt_active or self.snapshot.intervention_active:
            return False
        self.snapshot.prompt_active = True
        return True

    def end_prompt(self) -> None:
        self.snapshot.prompt_active = False

    def begin_intervention(self) -> bool:
        if self.snapshot.shutdown_requested or self.snapshot.intervention_active or self.snapshot.prompt_active:
            return False
        self.snapshot.intervention_active = True
        return True

    def end_intervention(self) -> None:
        self.snapshot.intervention_active = False

    def request_shutdown(self) -> bool:
        if self.snapshot.shutdown_requested:
            return False
        self.snapshot.shutdown_requested = True
        return True

    def can_start_prompt(self) -> bool:
        return not self.snapshot.shutdown_requested and not self.is_effectively_paused() and not self.snapshot.prompt_active and not self.snapshot.intervention_active

    def is_effectively_paused(self, now=None) -> bool:
        """Evaluate effective pause against the injected or supplied clock."""
        current = self.clock.now_utc() if now is None else now
        return self.snapshot.manual_paused or self.snapshot.snooze_active(current) or bool(self.snapshot.guard_reasons)
