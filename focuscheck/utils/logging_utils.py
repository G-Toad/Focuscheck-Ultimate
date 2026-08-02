"""
Logging utilities for the FocusCheck application.

Provides centralized logging configuration with rotation support.
"""

import os
import logging
import hashlib
from logging.handlers import RotatingFileHandler


_logger = None
_configured_log_path = None


class SafeRotatingFileHandler(RotatingFileHandler):
    """Keep logging usable when another FocusCheck process owns rotation."""

    def doRollover(self):
        try:
            super().doRollover()
        except OSError:
            # Windows cannot rename a file held by another process. Keep the
            # current stream and continue appending rather than raising a
            # logging-internal error from application code.
            if self.stream is None:
                try:
                    self.stream = self._open()
                except OSError:
                    self.stream = None


def privacy_summary(value):
    """Describe user-provided text without copying it into diagnostics."""
    if value is None:
        return {"type": "none", "length": 0, "sha256": None}
    text = str(value)
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]
    return {"type": type(value).__name__, "length": len(text), "sha256": digest}


def configure_log_path(path):
    """Bind the application log to the composition root before first use."""
    global _configured_log_path
    if _logger is not None:
        return False
    if path:
        _configured_log_path = os.fspath(path)
    return True


def get_logger():
    """
    Get or create the application logger.
    
    Sets up a rotating file handler with automatic log rotation
    and a fallback to stderr if file logging fails.
    
    Returns:
        Logger instance for the application
    """
    global _logger
    if _logger is not None:
        return _logger
    
    # Import here to avoid circular dependency
    from ..utils.paths import choose_path
    
    APP_LOG_PATH = _configured_log_path or choose_path("focus_app.log")
    
    try:
        os.makedirs(os.path.dirname(APP_LOG_PATH), exist_ok=True)
    except Exception:
        pass
    
    logger = logging.getLogger("focuscheck")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        try:
            handler = SafeRotatingFileHandler(
                APP_LOG_PATH,
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            logger.addHandler(handler)
        except Exception:
            # Fallback to stderr-only
            sh = logging.StreamHandler()
            sh.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            logger.addHandler(sh)
    
    _logger = logger
    return logger


def log_exception(msg):
    """
    Log an exception with the given message.
    
    Args:
        msg: Message to log with the exception
    """
    try:
        get_logger().exception(msg)
    except Exception:
        pass


def log_doctor_mode(category, message, details=None):
    """Log a message in doctor mode."""
    # Import here to avoid circular dependency
    from ..doctor import DOCTOR_MODE_ENABLED, log_anomaly
    if DOCTOR_MODE_ENABLED:
        log_anomaly(category, message, details)


def rotate_log_if_needed():
    """
    Rotate the log file if it exceeds the size limit.
    
    This is a maintenance function to ensure logs don't grow indefinitely.
    """
    try:
        logger = get_logger()
        for handler in logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                # RotatingFileHandler automatically rotates on write
                # This is a no-op but can be extended if needed
                pass
    except Exception:
        pass

