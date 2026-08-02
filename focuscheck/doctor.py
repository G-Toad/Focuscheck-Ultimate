"""
Doctor Mode for debugging and anomaly detection.
"""

import os
from .utils.logging_utils import get_logger

DOCTOR_MODE_ENABLED = os.environ.get("FOCUSCHECK_DOCTOR") == "1"

ANOMALIES = []

def log_anomaly(category, message, details=None):
    """Log a detected anomaly."""
    logger = get_logger()
    logger.warning("DOCTOR MODE: [%s] %s", category, message, extra={"details": details})
    ANOMALIES.append({"category": category, "message": message, "details": details})

if DOCTOR_MODE_ENABLED:
    log_anomaly("Startup", "Doctor Mode is enabled.")
