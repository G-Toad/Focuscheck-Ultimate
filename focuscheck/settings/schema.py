"""Typed, serializable settings schema derived from the canonical registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .defaults import DEFAULT_SETTINGS
from .registry import SETTINGS_REGISTRY


# User-authored text, destinations, and identity fields must never be treated
# as ordinary diagnostic configuration.
SENSITIVE_SETTING_KEYS = frozenset({
    "webhook_url",
    "spam_banned_words",
    "spam_vague_words",
    "study_phrase_list",
    "study_phrase_override",
    "waste_phrase_list",
    "waste_phrase_override",
    "website_flags",
    "biodata_enabled",
    "biodata_title",
    "biodata_first_name",
    "biodata_last_name",
    "biodata_show_full_name",
    "biodata_birthdate",
    "biodata_age_format",
    "biodata_show_days_lived",
    "biodata_show_lineage",
    "biodata_lineage_text",
    "biodata_show_role",
    "biodata_role_text",
    "biodata_custom_text",
    "biodata_style",
    "biodata_pulse_animation",
    "biodata_font_size",
})


@dataclass(frozen=True)
class SettingDescriptor:
    key: str
    canonical_type: str
    default: Any
    bounds: dict[str, Any] = field(default_factory=dict)
    enum: tuple[str, ...] = ()
    sensitivity: str = "normal"
    ui_section: str = "general"
    runtime_consumer: str = "settings.manager"
    persistence_class: str = "configuration"
    migration_aliases: tuple[str, ...] = ()
    deprecated: bool = False


def _section(key: str) -> str:
    if key.startswith(("pause", "inactive", "force_always")) or key == "paused":
        return "pause"
    if key.startswith(("snooze", "monitoring", "v2_")):
        return "monitoring"
    if key.startswith(("task", "require_active")):
        return "tasks"
    if key.startswith(("biodata", "purpose", "personal")):
        return "privacy"
    if key.startswith(("overdrive", "intensify", "studying")):
        return "prompt"
    return "general"


def _sensitivity(key: str) -> str:
    if key in SENSITIVE_SETTING_KEYS or any(token in key for token in ("password", "token", "secret", "purpose")):
        return "sensitive"
    return "normal"


def get_settings_schema() -> dict[str, SettingDescriptor]:
    descriptors: dict[str, SettingDescriptor] = {}
    for key, default in DEFAULT_SETTINGS.items():
        metadata = SETTINGS_REGISTRY.get(key, {})
        type_name = getattr(metadata.get("type", type(default)), "__name__", "object")
        descriptors[key] = SettingDescriptor(
            key=key,
            canonical_type=type_name,
            default=default,
            bounds=dict(metadata.get("bounds", {})),
            enum=tuple(metadata.get("enum", ())),
            sensitivity=str(metadata.get("sensitivity", _sensitivity(key))),
            ui_section=str(metadata.get("ui_section", _section(key))),
            runtime_consumer=str(metadata.get("runtime_consumer", "settings.manager")),
            persistence_class=str(metadata.get("persistence_class", "configuration")),
            migration_aliases=tuple(metadata.get("migration_aliases", ())),
            deprecated=bool(metadata.get("deprecated", False)),
        )
    return descriptors


def schema_manifest() -> list[dict[str, Any]]:
    """Return deterministic JSON-ready schema data for support and tests."""
    descriptors = get_settings_schema()
    return [asdict(descriptors[key]) for key in sorted(descriptors)]
