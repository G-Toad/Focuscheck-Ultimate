"""Base class for monitoring engines."""


class BaseEngine:
    """Base monitoring engine interface."""

    name = "base"

    def __init__(self, app):
        self.app = app

    def on_settings_updated(self, settings):
        """Hook for when settings are refreshed."""
        return None

    def create_prompt(self, settings, slot_info):
        """Create and return the prompt dialog for this engine."""
        raise NotImplementedError

    def shutdown(self):
        """Optional cleanup when engine is replaced."""
        return None
