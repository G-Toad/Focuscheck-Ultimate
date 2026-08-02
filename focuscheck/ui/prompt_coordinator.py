"""Single-owner bookkeeping for one active prompt dialog."""

from __future__ import annotations


class PromptCoordinator:
    """Make prompt completion idempotent across Tk polling and close paths."""

    def __init__(self) -> None:
        self._dialog = None
        self._generation = 0

    @property
    def dialog(self):
        return self._dialog

    @property
    def generation(self) -> int:
        return self._generation

    def open(self, dialog):
        if self._dialog is not None:
            return None
        self._generation += 1
        self._dialog = dialog
        return self._generation

    def is_current(self, dialog, generation=None) -> bool:
        return self._dialog is dialog and (generation is None or generation == self._generation)

    def complete(self, dialog=None, generation=None) -> bool:
        """Release only the current prompt; stale callbacks are harmless."""
        if dialog is not None and not self.is_current(dialog, generation):
            return False
        if self._dialog is None:
            return False
        self._dialog = None
        return True

    def close(self, dialog=None) -> bool:
        return self.complete(dialog)
