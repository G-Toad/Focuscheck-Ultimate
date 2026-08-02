"""Monitoring engine wrapper for Version 1 prompts."""

from .base import BaseEngine
from ..ui.dialogs.prompt_dialog import PromptDialog


class EngineV1(BaseEngine):
    """Classic monitoring engine (Version 1)."""

    name = "v1"

    def create_prompt(self, settings, slot_info):
        return PromptDialog(
            self.app.root,
            settings,
            on_submit=self.app._on_prompt_done,
            slot_start_dt=slot_info,
            taskdb=getattr(self.app, "taskdb", None),
            app_ref=self.app,
        )
