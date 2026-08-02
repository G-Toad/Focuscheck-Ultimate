"""Validation settings tab mixin (combines Challenges and Spam Detection)."""

import tkinter as tk
from tkinter import ttk
from ..modern_widgets import (
    InfoPanel, SectionHeader, SpinboxWithButtons, LabeledSlider,
    ExpandableCard, ChallengeCard, PresetButton
)


class ValidationTabMixin:
    """Mixin providing the Validation tab for settings window."""

    def _create_validation_tab(self):
        """Create unified Validation tab combining Challenges and Spam Detection."""
        tab = self._create_scrollable_tab(self.notebook, "Validation")

        # ===== VERSION 2 ALIGNMENT =====
        SectionHeader(tab, "Version 2 Alignment").pack(fill="x", pady=(10, 5))
        InfoPanel(
            tab,
            "When enabled, Version 2 uses every validation rule regardless of the toggles below.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 6))
        self._add_toggle_row(
            tab,
            "Force all validations in Version 2",
            self.v2_force_all_validations_var,
            "Overrides per-rule toggles for the Version 2 prompt engine",
        )

        # ===== CHALLENGE SYSTEM SECTION =====
        SectionHeader(tab, "Challenge System").pack(fill="x", pady=(15, 5))

        # Master toggle
        self._add_toggle_row(
            tab, "Enable Challenge System", self.challenge_enabled_var,
            "Master toggle - disabling this turns off all challenges"
        )

        # Presets
        PresetButton(
            tab, self.CHALLENGE_PRESETS, self._apply_preset
        ).pack(fill="x", pady=(10, 15))

        InfoPanel(
            tab,
            "Set both frequencies to 0% or turn the master toggle off to guarantee no challenges appear.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        # Challenge frequency and requirements
        SectionHeader(tab, "Challenge Frequency & Requirements").pack(fill="x")

        # PROMINENT WARNING about minimums
        InfoPanel(
            tab,
            "⚠️ IMPORTANT: The minimum word and character counts below apply to ALL responses when challenges are active, " +
            "even if you disable spam detection! These are the main source of '10 character minimum' / 'Need at least 3 words' errors.",
            panel_type="warning"
        ).pack(fill="x", pady=(0, 10))

        LabeledSlider(
            tab, "Studying frequency:",
            self.challenge_studying_freq_var, 0.0, 1.0, show_percentage=True
        ).pack(fill="x", pady=5)

        LabeledSlider(
            tab, "Wasting frequency:",
            self.challenge_wasting_freq_var, 0.0, 1.0, show_percentage=True
        ).pack(fill="x", pady=5)

        SpinboxWithButtons(tab, "Minimum words:", self.challenge_min_words_var, 1, 20, "words").pack(fill="x", pady=3)
        ttk.Label(tab, text="Minimum word count required when a challenge is shown (applies regardless of spam settings)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        SpinboxWithButtons(tab, "Minimum characters:", self.challenge_min_length_var, 5, 100, "chars").pack(fill="x", pady=3)
        ttk.Label(tab, text="Minimum character count when a challenge is shown (causes 'X character minimum' errors)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        self._add_toggle_row(tab, "Allow skipping challenges", self.challenge_allow_skip_var,
                            "Show cancel button on challenge dialogs")
        self._add_toggle_row(tab, "Show challenge hints", self.challenge_show_hints_var,
                            "Display example answers for each challenge")

        # Individual Studying Challenges (Collapsible)
        studying_header = SectionHeader(
            tab, "Individual Studying Challenges",
            actions=[
                ("Enable All", lambda: self._toggle_all_challenges("studying", True)),
                ("Disable All", lambda: self._toggle_all_challenges("studying", False))
            ]
        )
        studying_header.pack(fill="x", pady=(10, 5))

        studying_card = ExpandableCard(tab, "Configure Studying Challenges (click to expand)")
        studying_card.pack(fill="x", pady=5)

        for challenge_id, name, description in self.STUDYING_CHALLENGES:
            card = ChallengeCard(
                studying_card.content, challenge_id, name, description,
                self.studying_challenge_vars[challenge_id]
            )
            studying_card.add_content(card)

        # Individual Wasting Challenges (Collapsible)
        wasting_header = SectionHeader(
            tab, "Individual Wasting Time Challenges",
            actions=[
                ("Enable All", lambda: self._toggle_all_challenges("wasting", True)),
                ("Disable All", lambda: self._toggle_all_challenges("wasting", False))
            ]
        )
        wasting_header.pack(fill="x", pady=(10, 5))

        wasting_card = ExpandableCard(tab, "Configure Wasting Time Challenges (click to expand)")
        wasting_card.pack(fill="x", pady=5)

        for challenge_id, name, description in self.WASTING_CHALLENGES:
            card = ChallengeCard(
                wasting_card.content, challenge_id, name, description,
                self.wasting_challenge_vars[challenge_id]
            )
            wasting_card.add_content(card)

        # ===== SPAM DETECTION SECTION =====
        SectionHeader(tab, "Spam Detection System").pack(fill="x", pady=(20, 5))

        InfoPanel(
            tab,
            "Spam detection checks ALL responses for patterns like gibberish, keyboard mashing, and low-effort answers. " +
            "This is SEPARATE from challenge requirements above.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        self._add_toggle_row(tab, "Enable spam detection", self.spam_enabled_var,
                            "Master toggle for all spam pattern checks")

        # Gibberish Detection (Expandable)
        gibberish_card = ExpandableCard(tab, "Gibberish Detection")
        gibberish_card.pack(fill="x", pady=5)

        desc_frame = ttk.Frame(gibberish_card.content)
        desc_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame, text="Detects random characters by analyzing vowel ratio and character diversity",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")

        gibberish_card.add_content(self._add_toggle_row(gibberish_card.content, "Enable gibberish check",
                                              self.spam_gibberish_var,
                                              "Reject responses with unusual character patterns"))
        gibberish_card.add_content(LabeledSlider(gibberish_card.content, "Min vowel ratio:",
                                       self.spam_min_vowel_var, 0.0, 1.0, show_percentage=True))
        gibberish_card.add_content(LabeledSlider(gibberish_card.content, "Max vowel ratio:",
                                       self.spam_max_vowel_var, 0.0, 1.0, show_percentage=True))
        gibberish_card.add_content(LabeledSlider(gibberish_card.content, "Min unique chars:",
                                       self.spam_min_unique_var, 0.0, 1.0, show_percentage=True))

        # Repetition Detection (Expandable)
        repetition_card = ExpandableCard(tab, "Repetition Detection")
        repetition_card.pack(fill="x", pady=5)

        desc_frame2 = ttk.Frame(repetition_card.content)
        desc_frame2.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame2, text="Detects keyboard mashing and repeated patterns (e.g., 'aaa', 'asdfasdfasdf')",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")

        repetition_card.add_content(self._add_toggle_row(repetition_card.content, "Enable repetition check",
                                               self.spam_repetition_var,
                                               "Reject responses with excessive character/pattern repetition"))
        repetition_card.add_content(SpinboxWithButtons(repetition_card.content, "Max consecutive chars:",
                                             self.spam_max_consecutive_var, 1, 10, "count"))
        repetition_card.add_content(SpinboxWithButtons(repetition_card.content, "Max pattern repetition:",
                                             self.spam_max_pattern_var, 1, 10, "count"))

        # Spacing & Keyboard Patterns (Expandable)
        spacing_card = ExpandableCard(tab, "Spacing & Keyboard Patterns")
        spacing_card.pack(fill="x", pady=5)

        desc_frame3 = ttk.Frame(spacing_card.content)
        desc_frame3.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame3, text="Detects missing spaces and keyboard sequences (e.g., 'qwerty', 'asdf')",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")

        spacing_card.add_content(self._add_toggle_row(spacing_card.content, "Enable spacing check",
                                               self.spam_spacing_var,
                                               "Require spaces in longer responses"))
        spacing_card.add_content(SpinboxWithButtons(spacing_card.content, "Min length for spaces:",
                                             self.spam_min_spaces_var, 5, 50, "chars"))
        spacing_card.add_content(self._add_toggle_row(spacing_card.content, "Enable keyboard patterns",
                                               self.spam_keyboard_var,
                                               "Reject keyboard row sequences"))
        spacing_card.add_content(SpinboxWithButtons(spacing_card.content, "Min keyboard sequence:",
                                             self.spam_min_keyboard_var, 3, 10, "chars"))

        # Dictionary Validation (Expandable)
        dictionary_card = ExpandableCard(tab, "Dictionary Validation")
        dictionary_card.pack(fill="x", pady=5)

        desc_frame4 = ttk.Frame(dictionary_card.content)
        desc_frame4.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame4, text="Validates responses contain real English words from a built-in dictionary",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")

        dictionary_card.add_content(self._add_toggle_row(dictionary_card.content, "Enable dictionary check",
                                               self.spam_dictionary_var,
                                               "Require a minimum percentage of real words"))
        dictionary_card.add_content(LabeledSlider(dictionary_card.content, "Min real word ratio:",
                                       self.spam_min_word_ratio_var, 0.0, 1.0, show_percentage=True))
        dictionary_card.add_content(SpinboxWithButtons(dictionary_card.content, "Min word length:",
                                             self.spam_min_word_len_var, 1, 10, "chars"))

        # Timing Checks (Expandable)
        timing_card = ExpandableCard(tab, "Timing Checks")
        timing_card.pack(fill="x", pady=5)

        desc_frame5 = ttk.Frame(timing_card.content)
        desc_frame5.pack(fill="x", pady=(0, 5))
        ttk.Label(desc_frame5, text="Detects suspiciously fast responses that indicate lack of thought",
                 foreground="gray", font=("Segoe UI", 8), wraplength=400).pack(anchor="w")

        timing_card.add_content(self._add_toggle_row(timing_card.content, "Enable timing check",
                                               self.spam_timing_var,
                                               "Flag responses submitted too quickly"))
        timing_card.add_content(SpinboxWithButtons(timing_card.content, "Min time to submit:",
                                             self.spam_min_time_var, 0, 30, "seconds"))
        timing_card.add_content(SpinboxWithButtons(timing_card.content, "Flag if under:",
                                             self.spam_flag_time_var, 0, 10, "seconds"))

        # ===== SNOOZE EXACT INPUT ENFORCEMENT =====
        SectionHeader(tab, "Snooze Input Enforcement").pack(fill="x", pady=(20, 5))
        InfoPanel(
            tab,
            "Optionally force ALL validation heuristics on for the snooze confirmation input, regardless of the toggles above.",
            panel_type="warning"
        ).pack(fill="x", pady=(0, 8))
        self._add_toggle_row(tab, "Force all heuristics for snooze confirmation", self.snooze_force_all_heuristics_var,
                            "Overrides spam settings above specifically for the snooze confirmation dialog")
