"""Behavior settings tab mixin - includes prompts, time info, tasks, and camera."""

import tkinter as tk
from tkinter import ttk, messagebox
from ..modern_widgets import InfoPanel, SectionHeader, SpinboxWithButtons, LabeledSlider
from ..camera_test_window import CameraTestWindow
from ...settings.manager import save_settings


class BehaviorTabMixin:
    """Mixin providing the Behavior tab for settings window."""

    def _create_behavior_tab(self):
        """Create Behavior tab."""
        tab = self._create_scrollable_tab(self.notebook, "Behavior")

        InfoPanel(
            tab,
            "Configure which questions are asked in the prompts. To enable/disable prompts entirely, " +
            "go to the Validation tab (Master Controls section).",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        SectionHeader(tab, "Studying Prompt Questions").pack(fill="x")
        ttk.Label(tab, text="Note: The studying prompt must be enabled in the Validation tab for these to work.",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(5, 0), pady=(0, 5))
        self._add_toggle_row(tab, "Ask 'What are you doing?'", self.focus_ask_doing_var,
                            "Ask user what they're studying")
        self._add_toggle_row(tab, "Ask 'What are the benefits?'", self.focus_ask_benefits_var,
                            "Ask user about benefits of studying")

        SectionHeader(tab, "Wasting Time Prompt Questions").pack(fill="x")
        ttk.Label(tab, text="Note: The wasting time prompt must be enabled in the Validation tab for these to work.",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(5, 0), pady=(0, 5))
        self._add_toggle_row(tab, "Ask 'What are you wasting time on?'", self.waste_ask_what_var,
                            "Ask user what they're wasting time on")
        self._add_toggle_row(tab, "Ask 'What are the consequences?'", self.waste_ask_cons_var,
                            "Ask user about consequences of wasting time")
        self._add_toggle_row(tab, "Enforce validation on Wasting prompt", self.waste_validation_var,
                            "Disable to skip gibberish/challenge checks when clicking Wasting time")

        # (Snooze Confirmation UI moved to Alerts tab for alignment)

        SectionHeader(tab, "Phrase Acronym Challenge (Alternative)").pack(fill="x")
        ttk.Label(tab, text="Enable acronym challenge instead of reflection questions (mutually exclusive).",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(5, 0), pady=(0, 5))

        self._add_toggle_row(tab, "Enable Phrase Acronym Challenge", self.phrase_acronym_enabled_var,
                            "Show acronym challenge instead of reflection questions")

        SectionHeader(tab, "Button Labels").pack(fill="x", pady=(10, 0))
        InfoPanel(
            tab,
            "Turn this off to keep the buttons labeled simply as 'Studying' and 'Wasting time'. "
            "Turn it on to use the custom/random phrases below.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 8))
        self._add_toggle_row(tab, "Use custom button phrases", self.custom_button_phrases_var,
                            "Disable to restore the classic labels")

        # Study phrases section
        study_phrase_frame = ttk.Frame(tab)
        study_phrase_frame.pack(fill="x", pady=5, padx=(20, 0))

        ttk.Label(study_phrase_frame, text="Study Button:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5, 2))
        ttk.Label(study_phrase_frame, text="Only used when custom button phrases are enabled above.",
                 foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))

        # Mode selection for study
        study_mode_frame = ttk.Frame(study_phrase_frame)
        study_mode_frame.pack(fill="x", pady=2)
        ttk.Label(study_mode_frame, text="Mode:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
        ttk.Radiobutton(study_mode_frame, text="Random", variable=self.study_phrase_mode_var,
                       value="random").pack(side="left", padx=5)
        ttk.Radiobutton(study_mode_frame, text="Sequential", variable=self.study_phrase_mode_var,
                       value="sequential").pack(side="left", padx=5)
        ttk.Radiobutton(study_mode_frame, text="Override (single phrase)", variable=self.study_phrase_mode_var,
                       value="override").pack(side="left", padx=5)

        # Edit phrases button
        study_btn_frame = ttk.Frame(study_phrase_frame)
        study_btn_frame.pack(fill="x", pady=2)
        ttk.Button(study_btn_frame, text="Edit Study Phrases...",
                  command=lambda: self._edit_phrase_list("study")).pack(side="left", padx=(0, 10))
        ttk.Label(study_btn_frame, text=f"({len(self.study_phrase_list)} phrases)",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left")

        # Override entry
        study_override_frame = ttk.Frame(study_phrase_frame)
        study_override_frame.pack(fill="x", pady=2)
        ttk.Label(study_override_frame, text="Override phrase:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
        ttk.Entry(study_override_frame, textvariable=self.study_phrase_override_var, width=40).pack(side="left", fill="x", expand=True)

        # Waste phrases section
        waste_phrase_frame = ttk.Frame(tab)
        waste_phrase_frame.pack(fill="x", pady=5, padx=(20, 0))

        ttk.Label(waste_phrase_frame, text="Wasting Time Button:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5, 2))
        ttk.Label(waste_phrase_frame, text="Only used when custom button phrases are enabled above.",
                 foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))

        # Mode selection for waste
        waste_mode_frame = ttk.Frame(waste_phrase_frame)
        waste_mode_frame.pack(fill="x", pady=2)
        ttk.Label(waste_mode_frame, text="Mode:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
        ttk.Radiobutton(waste_mode_frame, text="Random", variable=self.waste_phrase_mode_var,
                       value="random").pack(side="left", padx=5)
        ttk.Radiobutton(waste_mode_frame, text="Sequential", variable=self.waste_phrase_mode_var,
                       value="sequential").pack(side="left", padx=5)
        ttk.Radiobutton(waste_mode_frame, text="Override (single phrase)", variable=self.waste_phrase_mode_var,
                       value="override").pack(side="left", padx=5)

        # Edit phrases button
        waste_btn_frame = ttk.Frame(waste_phrase_frame)
        waste_btn_frame.pack(fill="x", pady=2)
        ttk.Button(waste_btn_frame, text="Edit Wasting Time Phrases...",
                  command=lambda: self._edit_phrase_list("waste")).pack(side="left", padx=(0, 10))
        ttk.Label(waste_btn_frame, text=f"({len(self.waste_phrase_list)} phrases)",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left")

        # Override entry
        waste_override_frame = ttk.Frame(waste_phrase_frame)
        waste_override_frame.pack(fill="x", pady=2)
        ttk.Label(waste_override_frame, text="Override phrase:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
        ttk.Entry(waste_override_frame, textvariable=self.waste_phrase_override_var, width=40).pack(side="left", fill="x", expand=True)

        SectionHeader(tab, "Prompt Behavior").pack(fill="x")
        self._add_toggle_row(tab, "Require all fields", self.require_all_prompt_fields_var,
                            "Must answer all follow-up questions")
        self._add_toggle_row(tab, "Require active task", self.require_task_var,
                            "Must have a task to close prompt")

        SectionHeader(tab, "Version 2 Prompt").pack(fill="x")
        self._add_toggle_row(
            tab,
            "Include window title in V2 question",
            self.v2_question_use_window_title_var,
            "Use the active window title in 'Why are you on this application?'"
        )
        self._add_toggle_row(
            tab,
            "Require Enter to focus V2 answer box",
            self.v2_focus_requires_enter_var,
            "Popup opens without focus until you press Enter"
        )
        self._add_toggle_row(
            tab,
            "Hide V2 prompt during intervention",
            self.v2_hide_prompt_during_intervention_var,
            "Hide the main V2 popup while the intervention overlay is active"
        )

        SectionHeader(tab, "UI Options").pack(fill="x")
        self._add_toggle_row(tab, "Hide wasting button", self.hide_waste_var,
                            "Remove 'Wasting Time' button from main dialog")
        self._add_toggle_row(tab, "Show task encouragement", self.encourage_var)
        self._add_toggle_row(tab, "Show task analytics", self.show_analytics_var)

        # ===== TIME INFO DISPLAY =====
        SectionHeader(tab, "Time Info Display").pack(fill="x", pady=(15, 5))

        InfoPanel(
            tab,
            "Show time information below buttons in the prompt dialog to help track progress.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        self._add_toggle_row(tab, "Show time info", self.show_time_info_var,
                            "Display time info label under buttons in prompt dialog")

        # Time info mode
        mode_frame = ttk.Frame(tab)
        mode_frame.pack(fill="x", pady=5)
        ttk.Label(mode_frame, text="Display mode:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.time_info_mode_var,
                                  values=["hour", "day", "anchor", "launch"], state="readonly", width=15)
        mode_combo.pack(side="left")
        ttk.Label(mode_frame, text="What time to display: current hour/day, custom anchor time, or time since launch",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        # Anchor time (only shown when mode is "anchor")
        anchor_frame = ttk.Frame(tab)
        anchor_frame.pack(fill="x", pady=5)
        ttk.Label(anchor_frame, text="Anchor time (HH:MM):", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        anchor_entry = ttk.Entry(anchor_frame, textvariable=self.time_info_anchor_var, width=10)
        anchor_entry.pack(side="left")
        ttk.Label(anchor_frame, text="Used when mode='anchor' (e.g., '09:00' to show hours since 9 AM)",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        self._add_toggle_row(tab, "12-hour format", self.time_info_12h_var,
                            "Use 12-hour time (AM/PM) instead of 24-hour")
        self._add_toggle_row(tab, "Show seconds", self.time_info_show_seconds_var,
                            "Include seconds in time display")
        self._add_toggle_row(tab, "Show task remaining time", self.time_info_show_task_remaining_var,
                            "Also show time remaining until current task is due")

        SpinboxWithButtons(tab, "Refresh interval:", self.time_info_refresh_var, 250, 5000, "milliseconds").pack(fill="x", pady=3)
        ttk.Label(tab, text="How often to update the time display",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # ===== TASK ANALYTICS & DECISIONS =====
        SectionHeader(tab, "Task Analytics & Decision Prompts").pack(fill="x", pady=(15, 5))

        InfoPanel(
            tab,
            "Configure task deadline evaluation and analytics tracking for tasks.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        # Analytics timescale
        timescale_frame = ttk.Frame(tab)
        timescale_frame.pack(fill="x", pady=5)
        ttk.Label(timescale_frame, text="Analytics timescale:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        timescale_combo = ttk.Combobox(timescale_frame, textvariable=self.tasks_analytics_timescale_var,
                                       values=["lifetime", "today", "7d", "30d"], state="readonly", width=15)
        timescale_combo.pack(side="left")
        ttk.Label(timescale_frame, text="Time period for task analytics display",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        self._add_toggle_row(tab, "Task change counts as failure", self.tasks_change_counts_as_fail_var,
                            "Switching tasks counts as failing the previous task in analytics")
        self._add_toggle_row(tab, "Enable decision prompt", self.tasks_decision_prompt_enabled_var,
                            "Ask for task evaluation when deadline approaches or passes")
        self._add_toggle_row(tab, "Studying implies fail on decision", self.tasks_study_implies_fail_var,
                            "If you're studying when task deadline decision appears, auto-mark task as failed")

        # Evaluation mode
        eval_frame = ttk.Frame(tab)
        eval_frame.pack(fill="x", pady=5)
        ttk.Label(eval_frame, text="Evaluation mode:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        eval_combo = ttk.Combobox(eval_frame, textvariable=self.tasks_evaluation_mode_var,
                                  values=["before", "after"], state="readonly", width=15)
        eval_combo.pack(side="left")
        ttk.Label(eval_frame, text="When to prompt for task evaluation: before deadline or after it passes",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        SpinboxWithButtons(tab, "Decision window:", self.tasks_decision_window_var, 0, 60, "minutes").pack(fill="x", pady=3)
        ttk.Label(tab, text="Time window before/after deadline to show decision prompt (based on evaluation mode)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # ===== CAMERA FEED =====
        SectionHeader(tab, "Camera Feed Reflection").pack(fill="x", pady=(15, 5))

        InfoPanel(
            tab,
            "Display your webcam in the popup for self-reflection and accountability. " +
            "Requires: pip install opencv-python pillow",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        self._add_toggle_row(tab, "Enable camera feed", self.camera_feed_enabled_var,
                            "Show webcam feed in popup window for self-reflection")

        # Camera mode (live/static)
        mode_frame = ttk.Frame(tab)
        mode_frame.pack(fill="x", pady=5)
        ttk.Label(mode_frame, text="Display mode:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        self.camera_mode_combo = ttk.Combobox(mode_frame, textvariable=self.camera_feed_mode_var,
                                         values=["live", "static"], state="readonly", width=15)
        self.camera_mode_combo.pack(side="left")
        ttk.Label(mode_frame, text="live = continuous feed | static = snapshot when popup appears",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        self._add_toggle_row(tab, "Capture photo on button click", self.camera_capture_on_click_var,
                            "Save photo to logs when you click Studying or Wasting time (for accountability)")

        self._add_toggle_row(tab, "Flip camera horizontally (mirror)", self.camera_flip_horizontal_var,
                            "Mirror the camera display so it looks like a reflection (recommended)")

        # Camera sizing mode dropdown
        sizing_mode_frame = ttk.Frame(tab)
        sizing_mode_frame.pack(fill="x", pady=(8, 5))
        ttk.Label(sizing_mode_frame, text="Sizing mode:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
        self.camera_sizing_combo = ttk.Combobox(sizing_mode_frame, textvariable=self.camera_sizing_mode_var,
                                                 values=["aspect_ratio", "fixed_size", "face_tracking", "manual_crop"],
                                                 state="readonly", width=20)
        self.camera_sizing_combo.pack(side="left")

        # Adjust Crop button (for manual_crop mode)
        crop_adjust_btn = ttk.Button(sizing_mode_frame, text="Adjust Crop...",
                                     command=self._open_crop_adjustment_window)
        crop_adjust_btn.pack(side="left", padx=(10, 0))

        ttk.Label(sizing_mode_frame, text="← Configure manual crop with live preview",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(5, 0))

        # Store widgets that need to be greyed out based on sizing mode
        self._camera_fixed_size_widgets = []
        self._camera_face_tracking_widgets = []

        # --- FIXED SIZE / ASPECT RATIO MODE SETTINGS ---
        fixed_size_label = ttk.Label(tab, text="Size Settings (fixed_size mode: fills exactly | aspect_ratio mode: max dimensions):",
                                     foreground="#555", font=("Segoe UI", 9, "italic"))
        fixed_size_label.pack(fill="x", pady=(10, 3), padx=(10, 0))
        self._camera_fixed_size_widgets.append(fixed_size_label)

        width_spinbox = SpinboxWithButtons(tab, "Width:", self.camera_feed_width_var, 160, 1920, "pixels")
        width_spinbox.pack(fill="x", pady=3)
        self._camera_fixed_size_widgets.append(width_spinbox)

        height_spinbox = SpinboxWithButtons(tab, "Height:", self.camera_feed_height_var, 120, 1080, "pixels")
        height_spinbox.pack(fill="x", pady=3)
        self._camera_fixed_size_widgets.append(height_spinbox)

        # --- FACE TRACKING MODE SETTINGS ---
        face_track_label = ttk.Label(tab, text="Face Tracking Settings (zooms/crops to your face):",
                                     foreground="#555", font=("Segoe UI", 9, "italic"))
        face_track_label.pack(fill="x", pady=(10, 3), padx=(10, 0))
        self._camera_face_tracking_widgets.append(face_track_label)

        max_width_spinbox = SpinboxWithButtons(tab, "Max width:", self.camera_face_max_width_var, 160, 1920, "pixels")
        max_width_spinbox.pack(fill="x", pady=3)
        self._camera_face_tracking_widgets.append(max_width_spinbox)
        max_width_note = ttk.Label(tab, text="Recommended: 400 for good presence without overwhelming the popup",
                                   foreground="gray", font=("Segoe UI", 8))
        max_width_note.pack(fill="x", padx=(30, 0), pady=(0, 3))
        self._camera_face_tracking_widgets.append(max_width_note)

        max_height_spinbox = SpinboxWithButtons(tab, "Max height:", self.camera_face_max_height_var, 120, 1080, "pixels")
        max_height_spinbox.pack(fill="x", pady=3)
        self._camera_face_tracking_widgets.append(max_height_spinbox)
        max_height_note = ttk.Label(tab, text="Recommended: 300 to maintain reasonable popup size",
                                    foreground="gray", font=("Segoe UI", 8))
        max_height_note.pack(fill="x", padx=(30, 0), pady=(0, 3))
        self._camera_face_tracking_widgets.append(max_height_note)

        # Zoom factor slider
        zoom_slider = LabeledSlider(tab, "Zoom factor:", self.camera_face_zoom_factor_var, 1.0, 3.0)
        zoom_slider.pack(fill="x", pady=3)
        self._camera_face_tracking_widgets.append(zoom_slider)
        zoom_note = ttk.Label(tab, text="1.0 = just face, 1.5 = face + context (recommended), 3.0 = wide view",
                             foreground="gray", font=("Segoe UI", 8))
        zoom_note.pack(fill="x", padx=(30, 0), pady=(0, 3))
        self._camera_face_tracking_widgets.append(zoom_note)

        # Maximize face in display
        maximize_row = self._add_toggle_row(tab, "Maximize face in display box", self.camera_face_maximize_in_display_var,
                            "Scale face-tracked output to fill display area (maintains aspect ratio, adds minimal padding)")
        self._camera_face_tracking_widgets.append(maximize_row)

        # Fallback mode when no face detected
        fallback_frame = ttk.Frame(tab)
        fallback_frame.pack(fill="x", pady=5)
        self._camera_face_tracking_widgets.append(fallback_frame)
        ttk.Label(fallback_frame, text="Fallback (no face):", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        fallback_combo = ttk.Combobox(fallback_frame, textvariable=self.camera_face_fallback_mode_var,
                                      values=["aspect_ratio", "fixed_size"], state="readonly", width=15)
        fallback_combo.pack(side="left")
        ttk.Label(fallback_frame, text="What to show when face not detected",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        # --- FACE CENTERING FINE-TUNING (Advanced) ---
        centering_label = ttk.Label(tab, text="Face Centering Fine-Tuning (Advanced):",
                                    foreground="#555", font=("Segoe UI", 9, "italic", "bold"))
        centering_label.pack(fill="x", pady=(10, 3), padx=(10, 0))
        self._camera_face_tracking_widgets.append(centering_label)

        InfoPanel(
            tab,
            "⚙️ Advanced controls for perfect face framing. Adjust if your chin is cut off or face isn't centered.\n" +
            "• Vertical Bias: Higher = more chin/neck visible (0.5=middle, 0.65=recommended, 1.0=bottom)\n" +
            "• Width Multiplier: How wide the crop is (1.0=tight, 1.4=recommended, 2.0=very wide)\n" +
            "• Height Multiplier: How tall the crop is (1.0=tight, 1.6=recommended for full chin, 2.0=very tall)",
            panel_type="info"
        ).pack(fill="x", pady=(0, 5))

        # Vertical bias slider
        vbias_slider = LabeledSlider(tab, "Vertical bias:", self.camera_face_center_vertical_bias_var, 0.5, 1.0)
        vbias_slider.pack(fill="x", pady=3)
        self._camera_face_tracking_widgets.append(vbias_slider)
        vbias_note = ttk.Label(tab, text="0.5 = center of face, 0.65 = includes chin (recommended), 1.0 = bottom of face",
                              foreground="gray", font=("Segoe UI", 8))
        vbias_note.pack(fill="x", padx=(30, 0), pady=(0, 3))
        self._camera_face_tracking_widgets.append(vbias_note)

        # Width multiplier slider
        width_mult_slider = LabeledSlider(tab, "Crop width multiplier:", self.camera_face_crop_width_multiplier_var, 1.0, 2.5)
        width_mult_slider.pack(fill="x", pady=3)
        self._camera_face_tracking_widgets.append(width_mult_slider)
        width_mult_note = ttk.Label(tab, text="1.0 = exact face width, 1.4 = 40% wider (recommended), 2.5 = very wide",
                                   foreground="gray", font=("Segoe UI", 8))
        width_mult_note.pack(fill="x", padx=(30, 0), pady=(0, 3))
        self._camera_face_tracking_widgets.append(width_mult_note)

        # Height multiplier slider
        height_mult_slider = LabeledSlider(tab, "Crop height multiplier:", self.camera_face_crop_height_multiplier_var, 1.0, 2.5)
        height_mult_slider.pack(fill="x", pady=3)
        self._camera_face_tracking_widgets.append(height_mult_slider)
        height_mult_note = ttk.Label(tab, text="1.0 = exact face height, 1.6 = 60% taller for chin (recommended), 2.5 = very tall",
                                    foreground="gray", font=("Segoe UI", 8))
        height_mult_note.pack(fill="x", padx=(30, 0), pady=(0, 3))
        self._camera_face_tracking_widgets.append(height_mult_note)

        # --- EDGE-AWARE ZOOM ---
        edge_label = ttk.Label(tab, text="Edge-Aware Zoom (Prevents Edge Cutoff):",
                               foreground="#555", font=("Segoe UI", 9, "italic", "bold"))
        edge_label.pack(fill="x", pady=(10, 3), padx=(10, 0))
        self._camera_face_tracking_widgets.append(edge_label)

        InfoPanel(
            tab,
            "🎯 Automatically zooms out when your face approaches the edge of the frame.\n" +
            "Prevents awkward half-face cutoffs when you move around!\n" +
            "• Enable this to keep your full face visible even at edges\n" +
            "• Edge Threshold: How close to edge before it zooms out (0.15 = 15% from edge)\n" +
            "• Zoom Multiplier: How much extra area to show (1.3 = 30% more)",
            panel_type="info"
        ).pack(fill="x", pady=(0, 5))

        # Edge-aware zoom toggle
        edge_toggle = self._add_toggle_row(tab, "Enable edge-aware zoom", self.camera_face_edge_aware_zoom_var,
                                          "Automatically zoom out when face is near frame edges (recommended!)")
        self._camera_face_tracking_widgets.append(edge_toggle)

        # Edge threshold slider
        edge_threshold_slider = LabeledSlider(tab, "Edge threshold:", self.camera_face_edge_threshold_var, 0.05, 0.3)
        edge_threshold_slider.pack(fill="x", pady=3)
        self._camera_face_tracking_widgets.append(edge_threshold_slider)
        edge_threshold_note = ttk.Label(tab, text="0.05 = trigger very close to edge, 0.15 = medium (recommended), 0.3 = trigger far from edge",
                                       foreground="gray", font=("Segoe UI", 8))
        edge_threshold_note.pack(fill="x", padx=(30, 0), pady=(0, 3))
        self._camera_face_tracking_widgets.append(edge_threshold_note)

        # Edge zoom multiplier slider
        edge_zoom_slider = LabeledSlider(tab, "Edge zoom multiplier:", self.camera_face_edge_zoom_multiplier_var, 1.1, 2.0)
        edge_zoom_slider.pack(fill="x", pady=3)
        self._camera_face_tracking_widgets.append(edge_zoom_slider)
        edge_zoom_note = ttk.Label(tab, text="1.1 = slight zoom out, 1.3 = moderate (recommended), 2.0 = wide view",
                                  foreground="gray", font=("Segoe UI", 8))
        edge_zoom_note.pack(fill="x", padx=(30, 0), pady=(0, 3))
        self._camera_face_tracking_widgets.append(edge_zoom_note)

        # --- FACE DETECTION ALGORITHM ---
        detection_label = ttk.Label(tab, text="Face Detection Algorithm:",
                                    foreground="#555", font=("Segoe UI", 9, "italic", "bold"))
        detection_label.pack(fill="x", pady=(10, 3), padx=(10, 0))
        self._camera_face_tracking_widgets.append(detection_label)

        InfoPanel(
            tab,
            "🧠 Choose face detection algorithm:\n" +
            "• Haar Cascade: Fast, low CPU usage, good accuracy (RECOMMENDED)\n" +
            "• DNN (Deep Neural Network): Higher accuracy, more CPU usage, better for difficult angles",
            panel_type="info"
        ).pack(fill="x", pady=(0, 5))

        detection_frame = ttk.Frame(tab)
        detection_frame.pack(fill="x", pady=5)
        self._camera_face_tracking_widgets.append(detection_frame)
        ttk.Label(detection_frame, text="Detection method:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        detection_combo = ttk.Combobox(detection_frame, textvariable=self.camera_face_detection_method_var,
                                       values=["haar", "dnn"], state="readonly", width=15)
        detection_combo.pack(side="left", padx=(0, 10))
        ttk.Label(detection_frame, text="haar = fast (recommended) | dnn = more accurate but slower",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left")

        # Face detection polling interval
        detection_interval_widget = SpinboxWithButtons(tab, "Face detection polling interval:", self.camera_face_detection_interval_var, 1, 60, "frames")
        detection_interval_widget.pack(fill="x", pady=3)
        self._camera_face_tracking_widgets.append(detection_interval_widget)
        ttk.Label(tab, text="Run face detection every N frames (lower = more frequent detection, higher = better performance)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # --- MANUAL CROP MODE SETTINGS ---
        self._camera_manual_crop_widgets = []

        manual_crop_label = ttk.Label(tab, text="Manual Crop Settings (custom crop/zoom configuration):",
                                      foreground="#555", font=("Segoe UI", 9, "italic"))
        manual_crop_label.pack(fill="x", pady=(10, 3), padx=(10, 0))
        self._camera_manual_crop_widgets.append(manual_crop_label)

        InfoPanel(
            tab,
            "📐 Configure custom camera crop and zoom with live preview.\n\n"
            "Click 'Adjust Crop...' above to open the interactive crop editor with:\n"
            "• Live camera preview with crop overlay\n"
            "• Multiple anchor modes (center, edge, corner)\n"
            "• Zoom control (0.5x - 5.0x)\n"
            "• Grid overlays for composition\n"
            "• Save/load crop presets\n"
            "• Real-time statistics\n"
            "• Auto-detect face feature",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        # Current crop configuration summary
        crop_summary_frame = ttk.Frame(tab, relief=tk.RIDGE, borderwidth=1, padding=5)
        crop_summary_frame.pack(fill="x", pady=5)
        self._camera_manual_crop_widgets.append(crop_summary_frame)

        self.crop_summary_label = ttk.Label(crop_summary_frame,
                                           text=self._get_crop_summary_text(),
                                           foreground="#00aaff", font=("Segoe UI", 9))
        self.crop_summary_label.pack(anchor="w")

        ttk.Label(crop_summary_frame,
                 text="Click 'Adjust Crop...' above to modify settings with live preview",
                 foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(5, 0))

        # --- COMMON SETTINGS (always active) ---
        common_label = ttk.Label(tab, text="Common Settings:",
                                foreground="#555", font=("Segoe UI", 9, "italic"))
        common_label.pack(fill="x", pady=(10, 3), padx=(10, 0))

        # Camera device
        SpinboxWithButtons(tab, "Camera device index:", self.camera_device_index_var, 0, 5, "0=default").pack(fill="x", pady=3)
        ttk.Label(tab, text="Select which camera to use (0 = default, 1+ = additional cameras if available)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # FPS (only for live mode)
        SpinboxWithButtons(tab, "Frame rate (live mode):", self.camera_fps_var, 1, 60, "FPS").pack(fill="x", pady=3)
        ttk.Label(tab, text="Frames per second for live feed (higher = smoother but more CPU usage)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # Set up callbacks to grey out irrelevant settings
        self.camera_sizing_combo.bind("<<ComboboxSelected>>", self._update_camera_sizing_ui)
        # Initial update
        self._update_camera_sizing_ui()

        # ===== CAMERA VISUAL EFFECTS =====
        SectionHeader(tab, "Camera Visual Effects & Enhancements").pack(fill="x", pady=(15, 5))

        InfoPanel(
            tab,
            "Add visual overlays and automatic brightness adjustments to improve camera feed visibility",
            panel_type="tip"
        ).pack(fill="x", pady=(0, 10))

        # Face detection visualization
        self._add_toggle_row(tab, "Show face detection markers", self.camera_show_face_detection_var,
                            "Draw rectangles, center points, and crop regions showing face tracking in action")

        # Color inversion
        self._add_toggle_row(tab, "Invert colors (B&W negative)", self.camera_invert_colors_var,
                            "Flip all colors to negative - white becomes black, black becomes white")

        # Adaptive brightness section header
        adaptive_label = ttk.Label(tab, text="Adaptive Brightness Correction:",
                                  foreground="#555", font=("Segoe UI", 9, "bold"))
        adaptive_label.pack(fill="x", pady=(10, 3), padx=(10, 0))

        # Manual adjustments section
        InfoPanel(
            tab,
            "NEW! Use the live adjustment window to dial in your perfect camera settings with side-by-side preview.",
            panel_type="success"
        ).pack(fill="x", pady=(0, 10))

        # Button to open adjustment window
        adjustment_btn_frame = ttk.Frame(tab)
        adjustment_btn_frame.pack(fill="x", pady=(0, 10))

        adjustment_btn = ttk.Button(
            adjustment_btn_frame,
            text="🎨 Open Live Adjustment Window",
            command=self._open_camera_adjustment_window
        )
        adjustment_btn.pack(side="left", padx=(0, 10))

        ttk.Label(adjustment_btn_frame,
                 text="Side-by-side preview with manual sliders (brightness, contrast, saturation, sharpness, gamma, tint)",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left")

        # ===== CAMERA SETTINGS ACTION BUTTONS =====
        action_buttons_frame = ttk.Frame(tab)
        action_buttons_frame.pack(fill="x", pady=(15, 5))

        # Reset to Defaults button
        reset_btn = ttk.Button(action_buttons_frame, text="🔄 Reset Camera to Defaults",
                               command=self._reset_camera_to_defaults)
        reset_btn.pack(side="left", padx=(0, 10))

        # Save & Test button
        test_btn = ttk.Button(action_buttons_frame, text="💾 Save & Test Camera",
                              command=self._save_and_test_camera)
        test_btn.pack(side="left")

        ttk.Label(action_buttons_frame, text="← Reset all camera settings | Test camera in live preview window →",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        # ===== BIODATA IDENTITY DISPLAY =====
        SectionHeader(tab, "Identity Biodata Display").pack(fill="x", pady=(15, 5))

        InfoPanel(
            tab,
            "Display identity-reinforcing biodata below the camera feed in bold red font. " +
            "Helps strengthen self-awareness and personal accountability during focus checks.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        self._add_toggle_row(tab, "Enable biodata display", self.biodata_enabled_var,
                            "Show personalized identity information below camera feed")

        # Name fields
        name_frame = ttk.Frame(tab)
        name_frame.pack(fill="x", pady=5)
        ttk.Label(name_frame, text="Title:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        title_entry = ttk.Entry(name_frame, textvariable=self.biodata_title_var, width=10)
        title_entry.pack(side="left", padx=(0, 15))
        ttk.Label(name_frame, text="First name:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        first_entry = ttk.Entry(name_frame, textvariable=self.biodata_first_name_var, width=15)
        first_entry.pack(side="left", padx=(0, 15))
        ttk.Label(name_frame, text="Last name:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        last_entry = ttk.Entry(name_frame, textvariable=self.biodata_last_name_var, width=15)
        last_entry.pack(side="left")

        self._add_toggle_row(tab, "Show full name in popup", self.biodata_show_full_name_var,
                            "Display title + first name + last name (e.g., 'Mr. Akaash Singh')")

        # Birthdate
        birthdate_frame = ttk.Frame(tab)
        birthdate_frame.pack(fill="x", pady=5)
        ttk.Label(birthdate_frame, text="Birth date:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        birthdate_entry = ttk.Entry(birthdate_frame, textvariable=self.biodata_birthdate_var, width=12)
        birthdate_entry.pack(side="left", padx=(0, 10))
        ttk.Label(birthdate_frame, text="Format: YYYY-MM-DD (e.g., 2005-06-15)",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left")

        # Age format
        age_format_frame = ttk.Frame(tab)
        age_format_frame.pack(fill="x", pady=5)
        ttk.Label(age_format_frame, text="Age format:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        age_format_combo = ttk.Combobox(age_format_frame, textvariable=self.biodata_age_format_var,
                                        values=["simple", "precise", "decimal"], state="readonly", width=12)
        age_format_combo.pack(side="left", padx=(0, 10))
        ttk.Label(age_format_frame, text="simple='19 years old' | precise='19 years, 4 months, 4 days' | decimal='19.5 years'",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left")

        self._add_toggle_row(tab, "Show days lived", self.biodata_show_days_lived_var,
                            "Display total days lived (e.g., '7,120 days lived')")

        # Lineage
        self._add_toggle_row(tab, "Show lineage/heritage", self.biodata_show_lineage_var,
                            "Display family lineage or heritage information")

        lineage_frame = ttk.Frame(tab)
        lineage_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(lineage_frame, text="Lineage text:", font=("Segoe UI", 9)).pack(side="left", padx=(30, 10))
        lineage_entry = ttk.Entry(lineage_frame, textvariable=self.biodata_lineage_text_var, width=50)
        lineage_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Role
        self._add_toggle_row(tab, "Show role/phase", self.biodata_show_role_var,
                            "Display current role or life phase")

        role_frame = ttk.Frame(tab)
        role_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(role_frame, text="Role text:", font=("Segoe UI", 9)).pack(side="left", padx=(30, 10))
        role_entry = ttk.Entry(role_frame, textvariable=self.biodata_role_text_var, width=50)
        role_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Custom text
        custom_frame = ttk.Frame(tab)
        custom_frame.pack(fill="x", pady=5)
        ttk.Label(custom_frame, text="Custom statement:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        custom_entry = ttk.Entry(custom_frame, textvariable=self.biodata_custom_text_var, width=50)
        custom_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(custom_frame, text="Additional custom text (e.g., 'Guardian of your legacy')",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left")

        # Visual style section
        style_header = ttk.Label(tab, text="Visual Style:", foreground="#555", font=("Segoe UI", 9, "bold"))
        style_header.pack(fill="x", pady=(10, 3), padx=(10, 0))

        # Style dropdown
        style_frame = ttk.Frame(tab)
        style_frame.pack(fill="x", pady=5)
        ttk.Label(style_frame, text="Display style:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        style_combo = ttk.Combobox(style_frame, textvariable=self.biodata_style_var,
                                   values=["dramatic", "simple", "minimal"], state="readonly", width=12)
        style_combo.pack(side="left", padx=(0, 10))
        ttk.Label(style_frame, text="dramatic=red border+animation | simple=clean box | minimal=text only",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left")

        # Pulse animation toggle
        self._add_toggle_row(tab, "Enable pulsing animation", self.biodata_pulse_animation_var,
                            "Animate warning icons for maximum attention (dramatic style only)")

        # Font size slider
        font_size_slider = LabeledSlider(tab, "Font size:",
                                        self.biodata_font_size_var,
                                        8, 24, show_percentage=False, resolution=1)
        font_size_slider.pack(fill="x", pady=3)
        ttk.Label(tab, text="Size of biodata text (8=small, 14=default, 24=large)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))


    def _edit_phrase_list(self, button_type):
        """Open phrase list editor dialog."""
        from ..dialogs.phrase_list_editor_dialog import PhraseListEditorDialog

        current_list = self.study_phrase_list if button_type == "study" else self.waste_phrase_list

        def on_save(new_list):
            if button_type == "study":
                self.study_phrase_list = new_list
            else:
                self.waste_phrase_list = new_list

        PhraseListEditorDialog(self, button_type, current_list, on_save)

    def _edit_snooze_sentences(self):
        """Open list editor for snooze exact-typing sentences."""
        from ..dialogs.sentence_list_editor_dialog import SentenceListEditorDialog

        def on_save(new_list):
            self.snooze_sentence_list = list(new_list or [])
            self._update_snooze_sentence_count_label()

        SentenceListEditorDialog(self, "Edit Snooze Confirmation Sentences", getattr(self, 'snooze_sentence_list', []), on_save)

    def _update_snooze_sentence_count_label(self):
        try:
            n = len(getattr(self, 'snooze_sentence_list', []) or [])
        except Exception:
            n = 0
        label = getattr(self, '_snooze_sent_count_lbl', None)
        try:
            if label and label.winfo_exists():
                label.config(text=f"({n} sentence{'s' if n != 1 else ''})")
        except Exception:
            pass

    def _reset_camera_to_defaults(self):
        """Reset all camera settings to their default values."""
        from focuscheck.settings.defaults import DEFAULT_SETTINGS

        if not messagebox.askyesno("Reset Camera Settings", "Reset all camera settings to defaults?"):
            return

        self.camera_feed_enabled_var.set(DEFAULT_SETTINGS["camera_feed_enabled"])
        self.camera_feed_mode_var.set(DEFAULT_SETTINGS["camera_feed_mode"])
        self.camera_capture_on_click_var.set(DEFAULT_SETTINGS["camera_capture_on_click"])
        self.camera_flip_horizontal_var.set(DEFAULT_SETTINGS["camera_flip_horizontal"])
        self.camera_device_index_var.set(str(DEFAULT_SETTINGS["camera_device_index"]))
        self.camera_fps_var.set(str(DEFAULT_SETTINGS["camera_fps"]))
        self.camera_sizing_mode_var.set(DEFAULT_SETTINGS["camera_sizing_mode"])
        self.camera_feed_width_var.set(str(DEFAULT_SETTINGS["camera_feed_width"]))
        self.camera_feed_height_var.set(str(DEFAULT_SETTINGS["camera_feed_height"]))
        self.camera_face_max_width_var.set(str(DEFAULT_SETTINGS["camera_face_max_width"]))
        self.camera_face_max_height_var.set(str(DEFAULT_SETTINGS["camera_face_max_height"]))
        self.camera_face_zoom_factor_var.set(DEFAULT_SETTINGS["camera_face_zoom_factor"])
        self.camera_face_maximize_in_display_var.set(DEFAULT_SETTINGS["camera_face_maximize_in_display"])
        self.camera_face_fallback_mode_var.set(DEFAULT_SETTINGS["camera_face_fallback_mode"])
        self.camera_face_center_vertical_bias_var.set(DEFAULT_SETTINGS["camera_face_center_vertical_bias"])
        self.camera_face_crop_width_multiplier_var.set(DEFAULT_SETTINGS["camera_face_crop_width_multiplier"])
        self.camera_face_crop_height_multiplier_var.set(DEFAULT_SETTINGS["camera_face_crop_height_multiplier"])
        self.camera_face_edge_aware_zoom_var.set(DEFAULT_SETTINGS["camera_face_edge_aware_zoom"])
        self.camera_face_edge_threshold_var.set(DEFAULT_SETTINGS["camera_face_edge_threshold"])
        self.camera_face_edge_zoom_multiplier_var.set(DEFAULT_SETTINGS["camera_face_edge_zoom_multiplier"])
        self.camera_face_detection_method_var.set(DEFAULT_SETTINGS["camera_face_detection_method"])
        self.camera_face_detection_interval_var.set(str(DEFAULT_SETTINGS["camera_face_detection_interval"]))
        self.camera_show_face_detection_var.set(DEFAULT_SETTINGS.get("camera_show_face_detection", False))
        self.camera_invert_colors_var.set(DEFAULT_SETTINGS.get("camera_invert_colors", False))
        messagebox.showinfo("Reset Complete", "Camera settings reset to defaults!")

    def _save_and_test_camera(self):
        """Save current camera settings and open test preview window."""
        camera_settings = {
            "camera_feed_enabled": True,
            "camera_feed_mode": str(self.camera_feed_mode_var.get()).strip().lower(),
            "camera_flip_horizontal": bool(self.camera_flip_horizontal_var.get()),
            "camera_device_index": max(0, self._safe_int(self.camera_device_index_var, 0)),
            "camera_fps": min(60, max(1, self._safe_int(self.camera_fps_var, 30))),
            "camera_sizing_mode": str(self.camera_sizing_mode_var.get()).strip().lower(),
            "camera_feed_width": min(1920, max(160, self._safe_int(self.camera_feed_width_var, 320))),
            "camera_feed_height": min(1080, max(120, self._safe_int(self.camera_feed_height_var, 240))),
            "camera_face_max_width": min(1920, max(160, self._safe_int(self.camera_face_max_width_var, 400))),
            "camera_face_max_height": min(1080, max(120, self._safe_int(self.camera_face_max_height_var, 300))),
            "camera_face_zoom_factor": self._safe_float(self.camera_face_zoom_factor_var, 1.5, 1.0, 3.0),
            "camera_face_maximize_in_display": bool(self.camera_face_maximize_in_display_var.get()),
            "camera_face_fallback_mode": str(self.camera_face_fallback_mode_var.get()).strip().lower(),
            "camera_face_center_vertical_bias": self._safe_float(self.camera_face_center_vertical_bias_var, 0.65, 0.5, 1.0),
            "camera_face_crop_width_multiplier": self._safe_float(self.camera_face_crop_width_multiplier_var, 1.4, 1.0, 2.5),
            "camera_face_crop_height_multiplier": self._safe_float(self.camera_face_crop_height_multiplier_var, 1.6, 1.0, 2.5),
            "camera_face_edge_aware_zoom": bool(self.camera_face_edge_aware_zoom_var.get()),
            "camera_face_edge_threshold": self._safe_float(self.camera_face_edge_threshold_var, 0.15, 0.05, 0.3),
            "camera_face_edge_zoom_multiplier": self._safe_float(self.camera_face_edge_zoom_multiplier_var, 1.3, 1.1, 2.0),
            "camera_face_detection_method": str(self.camera_face_detection_method_var.get()).strip().lower(),
            "camera_face_detection_interval": min(60, max(1, self._safe_int(self.camera_face_detection_interval_var, 10))),
            "camera_show_face_detection": bool(self.camera_show_face_detection_var.get()),
            "camera_invert_colors": bool(self.camera_invert_colors_var.get()),
            "ui_scale_percent": 100,
        }
        CameraTestWindow(self, camera_settings)

    def _open_camera_adjustment_window(self):
        """Open the live camera adjustment window."""
        try:
            from ..camera_adjustment_window import CameraAdjustmentWindow
            current_settings = self.settings.copy() if hasattr(self, 'settings') else {}
            camera_index = max(0, self._safe_int(self.camera_device_index_var, 0))
            CameraAdjustmentWindow(self, camera_index, current_settings)
        except ImportError as e:
            messagebox.showerror("Error", f"Could not load camera adjustment window: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open camera adjustment window: {e}")

    def _save_camera_adjustment_settings(self, new_settings):
        """Persist camera adjustment settings from the adjustment window."""
        try:
            # Merge into live settings dict so the rest of the app sees updates
            for key, value in new_settings.items():
                self.settings[key] = value

            # Save to disk
            save_settings(self.settings)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save camera settings: {e}")
            return

        messagebox.showinfo("Saved", "Camera adjustments saved and applied.")

    def _open_crop_adjustment_window(self):
        """Open the crop adjustment window with live preview."""
        try:
            from ..crop_adjustment_window import CropAdjustmentWindow
            from ...settings.manager import save_settings

            def on_settings_updated(new_settings):
                """Callback when crop settings are updated."""
                # Update settings in memory
                for key, value in new_settings.items():
                    self.settings[key] = value

                # ACTUALLY SAVE TO DISK
                try:
                    save_settings(self.settings)
                except Exception as e:
                    messagebox.showerror("Save Error", f"Failed to save settings to disk: {e}")
                    return

                # Update summary display
                if hasattr(self, 'crop_summary_label'):
                    self.crop_summary_label.config(text=self._get_crop_summary_text())

            CropAdjustmentWindow(self, self.settings, on_settings_updated)

        except ImportError as e:
            messagebox.showerror("Error", f"Could not load crop adjustment window: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open crop adjustment window: {e}")

    def _get_crop_summary_text(self):
        """Get summary text for current crop configuration."""
        mode = self.settings.get("manual_crop_anchor_mode", "center")
        zoom = self.settings.get("manual_crop_zoom", 1.0)
        box_w = self.settings.get("manual_crop_box_width", 400)
        box_h = self.settings.get("manual_crop_box_height", 300)

        if mode == "center":
            offset_x = self.settings.get("manual_crop_center_offset_x", 0.0)
            offset_y = self.settings.get("manual_crop_center_offset_y", 0.0)
            return f"Center-based: {box_w}×{box_h} @ {zoom:.1f}x zoom, offset ({offset_x:+.1%}, {offset_y:+.1%})"
        elif mode == "edge":
            edge = self.settings.get("manual_crop_edge", "top")
            offset = self.settings.get("manual_crop_edge_offset", 0.0)
            return f"Edge-anchored: {edge.upper()} edge, {box_w}×{box_h} @ {zoom:.1f}x, offset {offset:+.1%}"
        else:  # corner
            corner = self.settings.get("manual_crop_corner", "top_left")
            return f"Corner-anchored: {corner.replace('_', ' ').upper()}, {box_w}×{box_h} @ {zoom:.1f}x"

    def _update_camera_sizing_ui(self, event=None):
        """Update camera settings UI based on selected sizing mode."""
        sizing_mode = self.camera_sizing_mode_var.get()

        fixed_state = "normal" if sizing_mode in ["fixed_size", "aspect_ratio"] else "disabled"
        for widget in getattr(self, '_camera_fixed_size_widgets', []):
            try:
                self._set_widget_state_recursive(widget, fixed_state)
            except Exception:
                pass

        face_state = "normal" if sizing_mode == "face_tracking" else "disabled"
        for widget in getattr(self, '_camera_face_tracking_widgets', []):
            try:
                self._set_widget_state_recursive(widget, face_state)
            except Exception:
                pass

        manual_state = "normal" if sizing_mode == "manual_crop" else "disabled"
        for widget in getattr(self, '_camera_manual_crop_widgets', []):
            try:
                self._set_widget_state_recursive(widget, manual_state)
            except Exception:
                pass

    def _set_widget_state_recursive(self, widget, state):
        """Recursively set widget state."""
        try:
            if hasattr(widget, 'configure'):
                widget.configure(state=state)
        except tk.TclError:
            pass
        try:
            for child in widget.winfo_children():
                self._set_widget_state_recursive(child, state)
        except Exception:
            pass
