"""
Doctor Mode for debugging and anomaly detection.
"""

import os
from .utils.logging_utils import get_logger, privacy_summary, sanitize_log_message

DOCTOR_MODE_ENABLED = os.environ.get("FOCUSCHECK_DOCTOR") == "1"

ANOMALIES = []
MAX_ANOMALIES = 200

def log_anomaly(category, message, details=None):
    """Log a detected anomaly without retaining user-provided values."""
    safe_category = sanitize_log_message(str(category))[:80]
    safe_message = sanitize_log_message(str(message))[:512]
    safe_details = None if details is None else privacy_summary(details)
    logger = get_logger()
    logger.warning("DOCTOR MODE: [%s] %s", safe_category, safe_message, extra={"details": safe_details})
    ANOMALIES.append({"category": safe_category, "message": safe_message, "details": safe_details})
    if len(ANOMALIES) > MAX_ANOMALIES:
        del ANOMALIES[:-MAX_ANOMALIES]


def get_anomalies():
    """Return a detached, bounded diagnostic snapshot."""
    return list(ANOMALIES)

if DOCTOR_MODE_ENABLED:
    log_anomaly("Startup", "Doctor Mode is enabled.")
