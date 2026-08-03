"""Single-owner bookkeeping for one active prompt dialog."""

from __future__ import annotations

from enum import Enum


class PromptOutcome(str, Enum):
    """Durable semantic result for the active prompt lifecycle."""

    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CLOSED_BY_POLICY = "closed_by_policy"
    INTERRUPTED_BY_PAUSE = "interrupted_by_pause"
    INTERRUPTED_BY_SETTINGS = "interrupted_by_settings"
    INTERRUPTED_BY_SHUTDOWN = "interrupted_by_shutdown"
    FAILED = "failed"

class PromptCoordinator:
    """Make prompt completion idempotent across Tk polling and close paths."""

    def __init__(self) -> None:
        self._dialog = None
        self._generation = 0
        self._last_outcome = None

    @property
    def dialog(self):
        return self._dialog

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def last_outcome(self):
        return self._last_outcome

    def open(self, dialog):
        if self._dialog is not None:
            return None
        self._generation += 1
        self._dialog = dialog
        return self._generation

    def is_current(self, dialog, generation=None) -> bool:
        return self._dialog is dialog and (generation is None or generation == self._generation)

    def complete(
        self,
        dialog=None,
        generation=None,
        outcome: PromptOutcome = PromptOutcome.COMPLETED,
    ) -> bool:
        """Release only the current prompt; stale callbacks are harmless."""
        if dialog is not None and not self.is_current(dialog, generation):
            return False
        if self._dialog is None:
            return False
        self._dialog = None
        self._last_outcome = PromptOutcome(outcome)
        return True

    def close(
        self,
        dialog=None,
        outcome: PromptOutcome = PromptOutcome.CANCELLED,
    ) -> bool:
        return self.complete(dialog, outcome=outcome)
