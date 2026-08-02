"""
Doctor Mode for debugging and anomaly detection.
"""

import os
from .utils.logging_utils import get_logger

DOCTOR_MODE_ENABLED = os.environ.get("FOCUSCHECK_DOCTOR") == "1"

ANOMALIES = []
MAX_ANOMALIES = 200

def log_anomaly(category, message, details=None):
    """Log a detected anomaly."""
    logger = get_logger()
    logger.warning("DOCTOR MODE: [%s] %s", category, message, extra={"details": details})
    ANOMALIES.append({"category": str(category), "message": str(message), "details": details})
    if len(ANOMALIES) > MAX_ANOMALIES:
        del ANOMALIES[:-MAX_ANOMALIES]


def get_anomalies():
    """Return a detached, bounded diagnostic snapshot."""
    return list(ANOMALIES)

if DOCTOR_MODE_ENABLED:
    log_anomaly("Startup", "Doctor Mode is enabled.")
