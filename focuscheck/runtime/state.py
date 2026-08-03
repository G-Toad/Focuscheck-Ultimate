"""Single-owner runtime pause and lifecycle state."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, MutableMapping, Any
from ..utils.clock import SystemClock


@dataclass
class RuntimeSnapshot:
    revision: int = 0
    manual_paused: bool = False
    snooze_until_utc: str = ""
    guard_reasons: set[str] = field(default_factory=set)
    prompt_active: bool = False
    intervention_active: bool = False
    shutdown_requested: bool = False
    _now_provider: Callable[[], datetime] | None = field(default=None, repr=False, compare=False)

    @property
    def effectively_paused(self) -> bool:
        now = self._now_provider() if self._now_provider is not None else None
        return self.manual_paused or self.snooze_active(now) or bool(self.guard_reasons)

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


@dataclass(frozen=True)
class RuntimeStateView:
    """Immutable, diagnostic-safe view of coordinator-owned runtime state."""

    revision: int
    manual_paused: bool
    snooze_until_utc: str
    snooze_active: bool
    guard_reasons: frozenset[str]
    prompt_active: bool
    intervention_active: bool
    shutdown_requested: bool
    effective_pause: bool
    effective_pause_reason: str | None


class RuntimeStateCoordinator:
    """Own state transitions and persist related settings atomically."""

    def __init__(
        self,
        settings: MutableMapping[str, Any],
        persist: Callable[[MutableMapping[str, Any]], bool] | None = None,
        clock: Any | None = None,
        transition_sink: Callable[[dict], None] | None = None,
    ) -> None:
        self.settings = settings
        self._persist = persist
        self.clock = clock or SystemClock()
        self._transition_sink = transition_sink
        self.snapshot = RuntimeSnapshot(
            manual_paused=self._manual_pause_from_settings(settings, self.clock.now_utc()),
            snooze_until_utc=str(settings.get("snooze_until_utc", "") or ""),
            _now_provider=self.clock.now_utc,
        )

    @staticmethod
    def _manual_pause_from_settings(settings: MutableMapping[str, Any], now: datetime | None = None) -> bool:
        """Read separated intent, preserving raw-dictionary compatibility."""
        if "manual_paused" in settings:
            return bool(settings.get("manual_paused", False))
        # Settings loaded through validate_settings receive an explicit
        # migration result. Callers constructing legacy dictionaries directly
        # retain the historical manual-pause-preserving behavior.
        return bool(settings.get("paused", False))

    def refresh_from_settings(self, settings: MutableMapping[str, Any]) -> None:
        """Adopt a reloaded settings document without losing runtime leases."""
        self.settings = settings
        self.snapshot.revision += 1
        self.snapshot.manual_paused = self._manual_pause_from_settings(settings, self.clock.now_utc())
        self.snapshot.snooze_until_utc = str(settings.get("snooze_until_utc", "") or "")

    def _safe_snapshot(self, snapshot: RuntimeSnapshot | None = None) -> dict:
        current = snapshot or self.snapshot
        return {
            "revision": current.revision,
            "manual_paused": current.manual_paused,
            "snooze_active": current.snooze_active(self.clock.now_utc()),
            "guard_count": len(current.guard_reasons),
            "prompt_active": current.prompt_active,
            "intervention_active": current.intervention_active,
            "shutdown_requested": current.shutdown_requested,
        }

    def _record(self, event: str, outcome: str, snapshot: RuntimeSnapshot | None = None) -> None:
        if self._transition_sink is None:
            return
        payload = self._safe_snapshot(snapshot)
        payload.update({"event": event, "outcome": outcome})
        try:
            self._transition_sink(payload)
        except Exception:
            pass

    def _commit(self, mutate: Callable[[], None], event: str) -> bool:
        before_settings = deepcopy(dict(self.settings))
        before_snapshot = deepcopy(self.snapshot)
        mutate()
        self.snapshot.revision = before_snapshot.revision + 1
        self.settings["paused"] = (
            self.snapshot.manual_paused
            or self.snapshot.snooze_active(self.clock.now_utc())
        )
        self.settings["manual_paused"] = self.snapshot.manual_paused
        self.settings["snooze_until_utc"] = self.snapshot.snooze_until_utc
        if self._persist is not None:
            try:
                if not self._persist(self.settings):
                    self.settings.clear()
                    self.settings.update(before_settings)
                    self.snapshot = before_snapshot
                    self._record(event, "rolled_back", before_snapshot)
                    return False
            except Exception:
                self.settings.clear()
                self.settings.update(before_settings)
                self.snapshot = before_snapshot
                self._record(event, "rolled_back", before_snapshot)
                return False
        self._record(event, "committed")
        return True

    def snapshot_view(self, now: datetime | None = None) -> RuntimeStateView:
        """Return an immutable point-in-time view for diagnostics and adapters."""
        current = self.snapshot
        current_time = now or self.clock.now_utc()
        snooze_active = current.snooze_active(current_time)
        guard_reasons = frozenset(str(reason) for reason in current.guard_reasons)
        if current.manual_paused:
            reason = "manual_pause"
        elif snooze_active:
            reason = "snooze"
        elif guard_reasons:
            reason = sorted(guard_reasons)[0]
        else:
            reason = None
        return RuntimeStateView(
            revision=current.revision,
            manual_paused=bool(current.manual_paused),
            snooze_until_utc=str(current.snooze_until_utc or ""),
            snooze_active=bool(snooze_active),
            guard_reasons=guard_reasons,
            prompt_active=bool(current.prompt_active),
            intervention_active=bool(current.intervention_active),
            shutdown_requested=bool(current.shutdown_requested),
            effective_pause=bool(current.manual_paused or snooze_active or guard_reasons),
            effective_pause_reason=reason,
        )

    def set_manual_paused(self, value: bool) -> bool:
        value = bool(value)
        if self.snapshot.manual_paused == value:
            return False
        return self._commit(lambda: setattr(self.snapshot, "manual_paused", value), "manual_pause")

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
        return self._commit(lambda: setattr(self.snapshot, "snooze_until_utc", value), "snooze")

    def clear_snooze(self) -> bool:
        return self.set_snooze_until(None)

    def set_guard_reason(self, reason: str, active: bool) -> None:
        reason = str(reason).strip()
        if not reason:
            return
        was_active = reason in self.snapshot.guard_reasons
        if active:
            self.snapshot.guard_reasons.add(reason)
        else:
            self.snapshot.guard_reasons.discard(reason)
        if was_active != bool(active):
            self.snapshot.revision += 1
            self._record("guard", "committed")

    def begin_prompt(self) -> bool:
        if (
            self.snapshot.shutdown_requested
            or self.snapshot.prompt_active
            or self.snapshot.intervention_active
            or self.is_effectively_paused()
        ):
            self._record("prompt", "denied")
            return False
        self.snapshot.prompt_active = True
        self.snapshot.revision += 1
        self._record("prompt", "begun")
        return True

    def end_prompt(self) -> None:
        self.snapshot.prompt_active = False
        self.snapshot.revision += 1
        self._record("prompt", "ended")

    def begin_intervention(self) -> bool:
        if self.snapshot.shutdown_requested or self.snapshot.intervention_active or self.snapshot.prompt_active:
            return False
        self.snapshot.intervention_active = True
        self.snapshot.revision += 1
        self._record("intervention", "begun")
        return True

    def end_intervention(self) -> None:
        self.snapshot.intervention_active = False
        self.snapshot.revision += 1
        self._record("intervention", "ended")

    def request_shutdown(self) -> bool:
        if self.snapshot.shutdown_requested:
            return False
        self.snapshot.shutdown_requested = True
        self.snapshot.revision += 1
        self._record("shutdown", "requested")
        return True

    def can_start_prompt(self) -> bool:
        return not self.snapshot.shutdown_requested and not self.is_effectively_paused() and not self.snapshot.prompt_active and not self.snapshot.intervention_active

    def is_effectively_paused(self, now=None) -> bool:
        """Evaluate effective pause against the injected or supplied clock."""
        current = self.clock.now_utc() if now is None else now
        return self.snapshot.manual_paused or self.snapshot.snooze_active(current) or bool(self.snapshot.guard_reasons)
