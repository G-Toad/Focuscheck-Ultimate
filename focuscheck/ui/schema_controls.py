"""Schema-backed controls for settings not represented by the primary tabs."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any

from ..settings.schema import SettingDescriptor, get_settings_schema


# These settings are runtime state, migration bookkeeping, or have a dedicated
# editor. They must not be presented as ordinary configuration controls.
SCHEMA_CONTROL_KEYS = (
    "overlays_enabled",
    "phrase_acronym_box_size",
    "phrase_acronym_letter_size",
    "phrase_acronym_font_size",
    "snooze_exact_max_jump_chars",
    "snooze_exact_min_keypress_ratio",
    "snooze_exact_min_time_seconds",
    "snooze_exact_require_focus_during_typing",
    "snooze_exact_time_per_char",
    "spam_banned_words",
    "spam_vague_words",
    "camera_face_max_misses",
    "camera_manual_adjustments_enabled",
    "camera_manual_brightness",
    "camera_manual_contrast",
    "camera_manual_gamma",
    "camera_manual_saturation",
    "camera_manual_sharpness",
    "camera_manual_tint",
    "camera_auto_adapt",
    "gentle_reminder_enabled",
    "gentle_reminder_interval",
    "gentle_reminder_drift_enabled",
    "gentle_reminder_drift_delay",
    "gentle_reminder_drift_speed",
)

# These controls are schema-backed but rendered by the hand-written challenge
# cards through dictionaries and therefore do not appear as literal keys in
# the settings window's save AST.
EXISTING_DYNAMIC_KEYS = tuple(
    [f"challenge_studying_{name}_enabled" for name in (
        "learning_specificity", "goal_connection", "will_commitment",
        "output_expectation",
    )]
    + [f"challenge_wasting_{name}_enabled" for name in (
        "wasting_acknowledgment", "should_gap", "because_reasoning",
        "hour_projection", "tomorrow_regret", "fear_acknowledgment",
        "lying_confrontation",
    )]
)


def _label_for_key(key: str) -> str:
    return key.replace("_", " ").capitalize()


def _initial_value(descriptor: SettingDescriptor, settings: dict[str, Any]) -> Any:
    value = settings.get(descriptor.key, descriptor.default)
    if descriptor.canonical_type in {"list", "dict"}:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return value


class SchemaSettingsBinding:
    """Own Tk variables and conversion for a fixed schema-derived key set."""

    def __init__(self, settings: dict[str, Any], keys=SCHEMA_CONTROL_KEYS):
        schema = get_settings_schema()
        unknown = sorted(set(keys) - set(schema))
        if unknown:
            raise ValueError(f"schema controls reference unknown keys: {unknown}")
        self.settings = dict(settings)
        self.schema = schema
        self.keys = tuple(keys)
        self.variables: dict[str, tk.Variable] = {}
        self._widgets: dict[str, tk.Widget] = {}
        for key in self.keys:
            descriptor = schema[key]
            value = _initial_value(descriptor, self.settings)
            if descriptor.canonical_type == "bool":
                variable: tk.Variable = tk.BooleanVar(value=bool(value))
            elif descriptor.canonical_type == "float":
                variable = tk.DoubleVar(value=float(value))
            elif descriptor.canonical_type == "int":
                variable = tk.IntVar(value=int(value))
            else:
                variable = tk.StringVar(value=str(value))
            self.variables[key] = variable

    def build(self, parent: ttk.Frame) -> None:
        ttk.Label(
            parent,
            text="Additional settings",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 3))
        ttk.Label(
            parent,
            text="These controls are generated from the canonical settings schema. Lists and dictionaries use JSON.",
            foreground="gray",
            wraplength=760,
        ).pack(anchor="w", padx=10, pady=(0, 10))

        for key in self.keys:
            descriptor = self.schema[key]
            row = ttk.Frame(parent)
            row.pack(fill="x", padx=10, pady=4)
            label = ttk.Label(row, text=_label_for_key(key), width=35)
            label.pack(side="left", anchor="n")
            widget = self._make_widget(row, descriptor)
            widget.pack(side="left", fill="x", expand=True)
            self._widgets[key] = widget

    def _make_widget(self, parent: ttk.Frame, descriptor: SettingDescriptor) -> ttk.Widget:
        variable = self.variables[descriptor.key]
        if descriptor.canonical_type == "bool":
            return ttk.Checkbutton(parent, variable=variable)
        enum = descriptor.enum
        if enum:
            return ttk.Combobox(parent, textvariable=variable, values=enum, state="readonly")
        return ttk.Entry(parent, textvariable=variable)

    def values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key in self.keys:
            descriptor = self.schema[key]
            variable = self.variables[key]
            try:
                raw = variable.get()
                if descriptor.canonical_type == "bool":
                    result[key] = bool(raw)
                elif descriptor.canonical_type == "int":
                    result[key] = int(raw)
                elif descriptor.canonical_type == "float":
                    result[key] = float(raw)
                elif descriptor.canonical_type in {"list", "dict"}:
                    parsed = json.loads(str(raw))
                    if not isinstance(parsed, list if descriptor.canonical_type == "list" else dict):
                        raise ValueError("wrong JSON container type")
                    result[key] = parsed
                else:
                    result[key] = str(raw)
            except (TypeError, ValueError, tk.TclError, json.JSONDecodeError):
                # Preserve the loaded value; validation in settings.manager will
                # still normalize it, but an invalid edit must not erase data.
                result[key] = self.settings.get(key, descriptor.default)
        return result


__all__ = ["EXISTING_DYNAMIC_KEYS", "SCHEMA_CONTROL_KEYS", "SchemaSettingsBinding"]
