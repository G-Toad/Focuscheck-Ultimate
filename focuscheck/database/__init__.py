"""
Database and CSV logging module.

Provides:
- TaskDB: SQLite-based task management
- CSV logging for responses and waste tracking
"""

from .task_db import TaskDB
from .csv_logger import (
    ensure_log_header,
    append_log,
    ensure_waste_log_header,
    ensure_focus_log_header,
    append_waste_log,
    append_focus_log,
    append_intervention_reflection,
    iter_jsonl_records,
    configure_paths,
)

__all__ = [
    'TaskDB',
    'ensure_log_header',
    'append_log',
    'ensure_waste_log_header',
    'ensure_focus_log_header',
    'append_waste_log',
    'append_focus_log',
    'append_intervention_reflection',
    'iter_jsonl_records',
    'configure_paths',
]
