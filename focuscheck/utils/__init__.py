"""Utilities for FocusCheck."""

from .audio import AudioAlarm, get_audio_alarm
from .colors import parse_rgb_hex
from .file_ops import acquire_single_instance, get_file_lock, release_single_instance
from .due_time import parse_due_time
from .logging_utils import get_logger, log_exception, rotate_log_if_needed
from .paths import (
    AppPaths,
    APP_LOG_PATH,
    HEARTBEAT_PATH,
    LOG_PATH,
    SETTINGS_PATH,
    TASK_DB_PATH,
    WASTE_LOG_PATH,
    choose_path,
    legacy_path,
    get_app_paths,
    get_base_dir,
    get_data_dir,
    migrate_legacy_data,
    resource_path,
)
from .timers import TimerRegistry
from .clock import FakeClock, SystemClock
from .ui_utils import log_window_state
from .data_export import clear_data, export_data, inventory_data
from .data_retention import apply_retention, retention_plan
from .diagnostics import create_bundle, preview_bundle

# Backwards-compatible name used by older callers.
AudioEngine = AudioAlarm

__all__ = [
    "APP_LOG_PATH",
    "AppPaths",
    "AudioAlarm",
    "AudioEngine",
    "HEARTBEAT_PATH",
    "LOG_PATH",
    "SETTINGS_PATH",
    "TASK_DB_PATH",
    "WASTE_LOG_PATH",
    "acquire_single_instance",
    "release_single_instance",
    "choose_path",
    "legacy_path",
    "get_app_paths",
    "TimerRegistry",
    "FakeClock",
    "SystemClock",
    "get_audio_alarm",
    "get_base_dir",
    "get_data_dir",
    "migrate_legacy_data",
    "get_file_lock",
    "export_data",
    "clear_data",
    "inventory_data",
    "apply_retention",
    "retention_plan",
    "create_bundle",
    "preview_bundle",
    "get_logger",
    "log_exception",
    "log_window_state",
    "parse_rgb_hex",
    "parse_due_time",
    "resource_path",
    "rotate_log_if_needed",
]
