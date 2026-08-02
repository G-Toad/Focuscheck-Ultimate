"""
Settings tab mixins for modular settings window.

Each mixin provides one tab creation method.
The main AdvancedSettingsWindow inherits from all mixins.
"""

from .general_tab import GeneralTabMixin
from .validation_tab import ValidationTabMixin
from .website_flags_tab import WebsiteFlagsTabMixin
from .challenges_tab import ChallengesTabMixin
from .spam_tab import SpamTabMixin
from .alerts_tab import AlertsTabMixin
from .behavior_tab import BehaviorTabMixin

__all__ = [
    'GeneralTabMixin',
    'ValidationTabMixin',
    'WebsiteFlagsTabMixin',
    'ChallengesTabMixin',
    'SpamTabMixin',
    'AlertsTabMixin',
    'BehaviorTabMixin',
]
