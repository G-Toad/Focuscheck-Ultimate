"""
Canonical feature gates.
"""

from ..utils.logging_utils import log_doctor_mode

def is_spam_detection_enabled(settings):
    """Check if spam detection is enabled."""
    enabled = settings.get("spam_detection_enabled") is True
    log_doctor_mode("FeatureGate", "is_spam_detection_enabled", {"enabled": enabled, "reason": "master_switch"})
    return enabled

def is_start_stop_enabled(settings):
    """Check if the start/stop tray menu item is enabled."""
    enabled = settings.get("tray_start_stop_enabled", True)
    log_doctor_mode("FeatureGate", "is_start_stop_enabled", {"enabled": enabled})
    return enabled

def is_settings_enabled(settings):
    """Check if the settings tray menu item is enabled."""
    enabled = settings.get("tray_settings_button_enabled", True)
    log_doctor_mode("FeatureGate", "is_settings_enabled", {"enabled": enabled})
    return enabled

def is_pause_enabled(settings):
    """Check if automatic pause detection is enabled."""
    if settings.get("force_always_on", True):
        enabled = False
        reason = "force_always_on"
    else:
        enabled = bool(settings.get("pause_when_inactive_or_lid_closed", False)) or any(
            bool(settings.get(key, False))
            for key in ("pause_on_idle", "pause_on_lid_closed", "pause_on_lock", "pause_on_sleep")
        )
        reason = "master_or_granular_switch"
    log_doctor_mode("FeatureGate", "is_pause_enabled", {"enabled": enabled, "reason": reason})
    return enabled

def is_exit_enabled(settings):
    """Check if the exit tray menu item is enabled."""
    enabled = settings.get("tray_exit_button_enabled", True)
    log_doctor_mode("FeatureGate", "is_exit_enabled", {"enabled": enabled})
    return enabled

def are_overlays_enabled(settings):
    """Check if overlays are enabled."""
    enabled = settings.get("overlays_enabled", True)
    log_doctor_mode("FeatureGate", "are_overlays_enabled", {"enabled": enabled})
    return enabled
