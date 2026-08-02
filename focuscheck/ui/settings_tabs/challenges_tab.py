"""Challenges settings tab mixin."""

import tkinter as tk
from tkinter import ttk
from ..modern_widgets import (
    InfoPanel, SectionHeader, SpinboxWithButtons, LabeledSlider,
    ChallengeCard, PresetButton
)


class ChallengesTabMixin:
    """Mixin providing the Challenges tab for settings window."""

    def _create_challenges_tab(self):
        """Create Challenges tab with modern controls."""
        tab = self._create_scrollable_tab(self.notebook, "Challenges")

        # Info panel
        InfoPanel(
            tab,
            "Challenges force genuine reflection through hard validation constraints. " +
            "Customize which challenges appear and how often.",
            panel_type="tip"
        ).pack(fill="x", pady=(0, 15))

        # Presets
        PresetButton(
            tab, self.CHALLENGE_PRESETS, self._apply_preset
        ).pack(fill="x", pady=(0, 15))

        # Master toggle
        SectionHeader(tab, "Challenge System").pack(fill="x")
        self._add_toggle_row(
            tab, "Enable Challenge System", self.challenge_enabled_var,
            "Master toggle - disabling this turns off all challenges"
        )

        # Global Settings with sliders
        SectionHeader(tab, "Global Settings").pack(fill="x")
        InfoPanel(
            tab,
            "These settings control ALL challenges. Minimum length and word count apply when challenges are active.",
            panel_type="info"
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
        ttk.Label(tab, text="Minimum word count required for challenge responses",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        SpinboxWithButtons(tab, "Minimum length:", self.challenge_min_length_var, 5, 100, "chars").pack(fill="x", pady=3)
        ttk.Label(tab, text="Minimum character count - this setting causes '20 character minimum' errors",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        self._add_toggle_row(tab, "Allow skipping", self.challenge_allow_skip_var,
                            "Show cancel button on challenges")
        self._add_toggle_row(tab, "Show hints", self.challenge_show_hints_var,
                            "Display example answers")

        # Studying Challenges
        studying_header = SectionHeader(
            tab, "Studying Challenges",
            actions=[
                ("Enable All", lambda: self._toggle_all_challenges("studying", True)),
                ("Disable All", lambda: self._toggle_all_challenges("studying", False))
            ]
        )
        studying_header.pack(fill="x")

        for challenge_id, name, description in self.STUDYING_CHALLENGES:
            card = ChallengeCard(
                tab, challenge_id, name, description,
                self.studying_challenge_vars[challenge_id]
            )
            card.pack(fill="x", pady=5)

        # Wasting Challenges
        wasting_header = SectionHeader(
            tab, "Wasting Time Challenges",
            actions=[
                ("Enable All", lambda: self._toggle_all_challenges("wasting", True)),
                ("Disable All", lambda: self._toggle_all_challenges("wasting", False))
            ]
        )
        wasting_header.pack(fill="x")

        for challenge_id, name, description in self.WASTING_CHALLENGES:
            card = ChallengeCard(
                tab, challenge_id, name, description,
                self.wasting_challenge_vars[challenge_id]
            )
            card.pack(fill="x", pady=5)
