"""Typed, serializable settings schema derived from the canonical registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .defaults import DEFAULT_SETTINGS
from .registry import SETTINGS_REGISTRY


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
    if any(token in key for token in ("password", "token", "secret", "biodata", "purpose")):
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
