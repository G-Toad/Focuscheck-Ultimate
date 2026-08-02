"""
User interface components.

Provides:
- Dialogs: PromptDialog, TaskEntryDialog, WastePromptDialog, TaskChangeDialog
- Windows: SettingsWindow, TaskHistoryWindow
- Guards: PauseGuard for automatic pause detection
- Overlays: Screen dimming for overdrive mode
"""

from .guards import PauseGuard
from .dialogs import (
    PromptDialog,
    TaskEntryDialog,
    FocusPromptDialog,
    WastePromptDialog,
    TaskChangeDialog,
    SnoozeReminderDialog
)
from .windows import (
    SettingsWindow,
    TaskHistoryWindow
)

__all__ = [
    'PauseGuard',
    'PromptDialog',
    'TaskEntryDialog',
    'FocusPromptDialog',
    'WastePromptDialog',
    'TaskChangeDialog',
    'SnoozeReminderDialog',
    'SettingsWindow',
    'TaskHistoryWindow',
]

