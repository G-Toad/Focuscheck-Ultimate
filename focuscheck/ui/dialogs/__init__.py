"""
Dialog windows for user interaction.

This package contains dialog classes for task entry, waste tracking, task changes,
and the main check-in prompt dialog (PromptDialog).

The original monolithic dialogs.py has been refactored into:
- prompt_dialog.py: Main PromptDialog class (built from mixins)
- task_entry_dialog.py: TaskEntryDialog for creating new tasks
- focus_prompt_dialog.py: FocusPromptDialog for capturing focus details
- waste_prompt_dialog.py: WastePromptDialog for tracking time waste
- task_change_dialog.py: TaskChangeDialog for changing active tasks
- windows_utils.py: Windows-specific overlay and click-through utilities
- prompt_dialog_mixins/: Mixins that compose the PromptDialog functionality
"""

from .prompt_dialog import PromptDialog
from .task_entry_dialog import TaskEntryDialog
from .focus_prompt_dialog import FocusPromptDialog
from .waste_prompt_dialog import WastePromptDialog
from .task_change_dialog import TaskChangeDialog
from .snooze_reminder_dialog import SnoozeReminderDialog
from .gentle_reminder_dialog import GentleReminderDialog
from .snooze_prompt_dialog import SnoozePromptDialog
from .sentence_list_editor_dialog import SentenceListEditorDialog
from .v2_prompt_dialog import V2PromptDialog
from .v2_subpopup_dialog import V2SubPopupDialog
from .intervention_wizard import InterventionWizard

__all__ = [
    'PromptDialog',
    'TaskEntryDialog',
    'FocusPromptDialog',
    'WastePromptDialog',
    'TaskChangeDialog',
    'SnoozeReminderDialog',
    'GentleReminderDialog',
    'SnoozePromptDialog',
    'SentenceListEditorDialog',
    'V2PromptDialog',
    'V2SubPopupDialog',
    'InterventionWizard',
]
