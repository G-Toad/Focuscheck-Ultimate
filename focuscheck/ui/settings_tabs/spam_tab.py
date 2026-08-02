"""Spam detection settings tab mixin."""

import tkinter as tk
from tkinter import ttk
from ..modern_widgets import (
    InfoPanel, SectionHeader, SpinboxWithButtons, LabeledSlider,
    ExpandableCard
)


class SpamTabMixin:
    """Mixin providing the Spam Detection tab for settings window."""

    def _create_spam_tab(self):
        """Create Spam Detection tab."""
        tab = self._create_scrollable_tab(self.notebook, "Spam Detection")

        InfoPanel(
            tab,
            "Spam detection prevents low-effort, automated, or dishonest responses. " +
            "These settings work together with Challenge requirements to ensure thoughtful answers.",
            panel_type="warning"
        ).pack(fill="x", pady=(0, 15))

        SectionHeader(tab, "Spam Detection").pack(fill="x")
        self._add_toggle_row(tab, "Enable spam detection", self.spam_enabled_var,
                            "Master toggle for all spam checks")

        # Gibberish
        card = ExpandableCard(tab, "Gibberish Detection")
        card.pack(fill="x", pady=5)
        desc_frame = ttk.Frame(card.content)
        desc_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame, text="Detects random characters by analyzing vowel ratio and character diversity",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")
        card.add_content(self._add_toggle_row(card.content, "Enable gibberish check",
                                              self.spam_gibberish_var,
                                              "Reject responses with unusual character patterns"))
        card.add_content(LabeledSlider(card.content, "Min vowel ratio:",
                                       self.spam_min_vowel_var, 0.0, 1.0, show_percentage=True))
        card.add_content(LabeledSlider(card.content, "Max vowel ratio:",
                                       self.spam_max_vowel_var, 0.0, 1.0, show_percentage=True))
        card.add_content(LabeledSlider(card.content, "Min unique chars:",
                                       self.spam_min_unique_var, 0.0, 1.0, show_percentage=True))

        # Repetition
        card2 = ExpandableCard(tab, "Repetition Detection")
        card2.pack(fill="x", pady=5)
        desc_frame2 = ttk.Frame(card2.content)
        desc_frame2.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame2, text="Detects keyboard mashing and repeated patterns (e.g., 'aaa', 'asdfasdfasdf')",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")
        card2.add_content(self._add_toggle_row(card2.content, "Enable repetition check",
                                               self.spam_repetition_var,
                                               "Reject responses with excessive character/pattern repetition"))
        card2.add_content(SpinboxWithButtons(card2.content, "Max consecutive chars:",
                                             self.spam_max_consecutive_var, 1, 10, "count"))
        card2.add_content(SpinboxWithButtons(card2.content, "Max pattern repetition:",
                                             self.spam_max_pattern_var, 1, 10, "count"))

        # Spacing & Patterns
        card3 = ExpandableCard(tab, "Spacing & Keyboard Patterns")
        card3.pack(fill="x", pady=5)
        desc_frame3 = ttk.Frame(card3.content)
        desc_frame3.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame3, text="Detects missing spaces and keyboard sequences (e.g., 'qwerty', 'asdf')",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")
        card3.add_content(self._add_toggle_row(card3.content, "Enable spacing check",
                                               self.spam_spacing_var,
                                               "Require spaces in longer responses"))
        card3.add_content(SpinboxWithButtons(card3.content, "Min length for spaces:",
                                             self.spam_min_spaces_var, 5, 50, "chars"))
        card3.add_content(self._add_toggle_row(card3.content, "Enable keyboard patterns",
                                               self.spam_keyboard_var,
                                               "Reject keyboard row sequences"))
        card3.add_content(SpinboxWithButtons(card3.content, "Min keyboard sequence:",
                                             self.spam_min_keyboard_var, 3, 10, "chars"))

        # Dictionary
        card4 = ExpandableCard(tab, "Dictionary Validation")
        card4.pack(fill="x", pady=5)
        desc_frame4 = ttk.Frame(card4.content)
        desc_frame4.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame4, text="Validates responses contain real English words from a built-in dictionary",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")
        card4.add_content(self._add_toggle_row(card4.content, "Enable dictionary check",
                                               self.spam_dictionary_var,
                                               "Require a minimum percentage of real words"))
        card4.add_content(LabeledSlider(card4.content, "Min real word ratio:",
                                       self.spam_min_word_ratio_var, 0.0, 1.0, show_percentage=True))
        card4.add_content(SpinboxWithButtons(card4.content, "Min word length:",
                                             self.spam_min_word_len_var, 1, 10, "chars"))

        # Timing
        card5 = ExpandableCard(tab, "Timing Checks")
        card5.pack(fill="x", pady=5)
        desc_frame5 = ttk.Frame(card5.content)
        desc_frame5.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame5, text="Detects suspiciously fast responses that indicate lack of thought",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")
        card5.add_content(self._add_toggle_row(card5.content, "Enable timing check",
                                               self.spam_timing_var,
                                               "Flag responses submitted too quickly"))
        card5.add_content(SpinboxWithButtons(card5.content, "Min time to submit:",
                                             self.spam_min_time_var, 0, 30, "seconds"))
        card5.add_content(SpinboxWithButtons(card5.content, "Flag if under:",
                                             self.spam_flag_time_var, 0, 10, "seconds"))
