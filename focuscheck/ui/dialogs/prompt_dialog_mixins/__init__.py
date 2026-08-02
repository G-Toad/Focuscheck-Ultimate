"""
Mixins for PromptDialog class.

This package contains functional mixins that organize the PromptDialog
class into separate, focused modules.
"""

from .button_handling import ButtonHandlingMixin
from .window_placement import WindowPlacementMixin
from .time_display import TimeDisplayMixin
from .anti_habit import AntiHabitMixin
from .intensification import IntensificationMixin
from .task_management import TaskManagementMixin
from .windows_integration import WindowsIntegrationMixin
from .camera_feed import CameraFeedMixin

__all__ = [
    'ButtonHandlingMixin',
    'WindowPlacementMixin',
    'TimeDisplayMixin',
    'AntiHabitMixin',
    'IntensificationMixin',
    'TaskManagementMixin',
    'WindowsIntegrationMixin',
    'CameraFeedMixin',
]
