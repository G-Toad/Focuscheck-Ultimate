"""CSV logging for responses and waste tracking."""

import csv
import os
import time
import threading
import json
from datetime import datetime, timezone
from ..utils.logging_utils import log_exception, get_logger
from ..utils.paths import choose_path

# CSV file locking
_csv_locks = {}
_csv_locks_mutex = threading.Lock()

LOG_PATH = choose_path("focus_log.csv")
WASTE_LOG_PATH = choose_path("focus_waste_log.csv")
FOCUS_LOG_PATH = choose_path("focus_study_log.csv")
INTERVENTION_REFLECTION_PATH = choose_path("focus_intervention_reflections.jsonl")


def _get_csv_lock(file_path):
    """Get or create a lock for a specific CSV file."""
    with _csv_locks_mutex:
        if file_path not in _csv_locks:
            _csv_locks[file_path] = threading.RLock()
        return _csv_locks[file_path]


def _safe_csv_write(file_path, write_func):
    """Thread-safe CSV writing with file locking."""
    lock = _get_csv_lock(file_path)
    with lock:
        try:
            write_func()
            return True
        except Exception:
            log_exception(f"CSV write failed for {file_path}")
            return False


def _safe_jsonl_write(file_path, write_func):
    lock = _get_csv_lock(file_path)
    with lock:
        try:
            write_func()
            return True
        except Exception:
            log_exception(f"JSONL write failed for {file_path}")
            return False


def _rotate_csv_if_needed(path, max_bytes=5_000_000, backups=2):
    """Rotate CSV file if it exceeds size limit."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass
    try:
        sz = os.path.getsize(path) if os.path.exists(path) else 0
        if sz < max_bytes:
            return
        # rotate: path -> path.1 -> path.2
        for i in range(backups, 0, -1):
            older = f"{path}.{i}"
            newer = f"{path}.{i+1}"
            try:
                if os.path.exists(older):
                    if i == backups:
                        try:
                            os.remove(older)
                        except Exception:
                            pass
                    else:
                        os.replace(older, newer)
            except Exception:
                pass
        try:
            if os.path.exists(path):
                os.replace(path, f"{path}.1")
        except Exception:
            pass
    except Exception:
        log_exception("rotate_csv_if_needed failed")


def ensure_log_header():
    """Ensure CSV log file exists with proper headers."""
    _rotate_csv_if_needed(LOG_PATH)

    def _write_header():
        needs_header = True
        try:
            if os.path.exists(LOG_PATH):
                try:
                    needs_header = os.path.getsize(LOG_PATH) == 0
                except Exception:
                    needs_header = True
            with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if needs_header:
                    w.writerow([
                        "click_timestamp_utc", "click_local_time",
                        "slot_start_utc", "slot_start_local_minute",
                        "response", "on_time", "late_by_ms",
                        "response_latency_ms",
                        "interval_seconds", "intensify_after_seconds", "overdrive_after_seconds",
                        "intensity_level_reached"
                    ])
        except Exception:
            log_exception("ensure_log_header: failed to open/write")

    return _safe_csv_write(LOG_PATH, _write_header)


def append_log(*, response, latency_ms, settings, intensity_level_reached,
               slot_start_dt, overdrive_deadline_s):
    """Append a response to the CSV log."""
    logger = get_logger()
    logger.info("=" * 80)
    logger.info("DATABASE: append_log() CALLED - Logging response to CSV")
    logger.info("  Parameters:")
    logger.info("    - response: '%s'", response)
    logger.info("    - latency_ms: %s", latency_ms)
    logger.info("    - intensity_level_reached: %s", intensity_level_reached)
    logger.info("    - slot_start_dt: %s", slot_start_dt)
    logger.info("    - overdrive_deadline_s: %s", overdrive_deadline_s)

    logger.info("  Calculating timing information...")
    now_utc = datetime.now(timezone.utc)
    logger.info("    Current time (UTC): %s", now_utc)

    elapsed_s = (time.monotonic() - slot_start_dt["mono_start"])
    logger.info("    Elapsed seconds since slot start: %.3f", elapsed_s)

    late_by_ms = max(0, int((elapsed_s - overdrive_deadline_s) * 1000))
    logger.info("    Late by (ms): %d", late_by_ms)

    on_time = "YES" if late_by_ms == 0 else "NO"
    logger.info("    On time: %s", on_time)

    logger.info("  Preparing CSV row data...")
    logger.info("    LOG_PATH: %s", LOG_PATH)

    def _write_log():
        logger.info("    _write_log() called")
        logger.info("      Ensuring log header exists...")
        ensure_log_header()
        logger.info("      Header ensured")

        logger.info("      Opening CSV file for append...")
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            logger.info("      File opened successfully")
            logger.info("      Creating CSV writer...")
            w = csv.writer(f)

            row_data = [
                now_utc.isoformat(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                slot_start_dt["utc_start"].isoformat(),
                slot_start_dt["local_minute"],
                response, on_time, late_by_ms,
                int(latency_ms),
                int(settings["interval_seconds"]),
                int(settings["intensify_after_seconds"]),
                int(settings["overdrive_after_seconds"]),
                int(intensity_level_reached)
            ]

            logger.info("      Writing row to CSV...")
            logger.info("        Row data: %s", row_data)
            w.writerow(row_data)
            logger.info("      Row written successfully")

    logger.info("  Calling _safe_csv_write()...")
    ok = _safe_csv_write(LOG_PATH, _write_log)
    logger.info("  CSV write completed")
    logger.info("DATABASE: append_log() COMPLETED")
    logger.info("=" * 80)
    return ok


def append_intervention_reflection(record):
    """Append an intervention reflection record as JSONL."""
    logger = get_logger()
    try:
        os.makedirs(os.path.dirname(INTERVENTION_REFLECTION_PATH), exist_ok=True)
    except Exception:
        pass

    def _write():
        with open(INTERVENTION_REFLECTION_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    ok = _safe_jsonl_write(INTERVENTION_REFLECTION_PATH, _write)
    try:
        logger.info("DATABASE: append_intervention_reflection OK")
    except Exception:
        pass
    return ok


def ensure_waste_log_header():
    """Ensure waste log CSV exists with headers."""
    _rotate_csv_if_needed(WASTE_LOG_PATH)

    def _write_header():
        needs_header = True
        try:
            if os.path.exists(WASTE_LOG_PATH):
                try:
                    needs_header = os.path.getsize(WASTE_LOG_PATH) == 0
                except Exception:
                    needs_header = True
            with open(WASTE_LOG_PATH, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if needs_header:
                    w.writerow([
                        "event_utc", "event_local",
                        "slot_start_utc", "response_latency_ms",
                        "what", "consequences",
                        "active_task_id", "active_task_title"
                    ])
        except Exception:
            log_exception("ensure_waste_log_header failed")

    return _safe_csv_write(WASTE_LOG_PATH, _write_header)


def append_waste_log(*, slot_start_dt, latency_ms, what, consequences, active_task):
    """Log wasted time to CSV."""
    now_utc = datetime.now(timezone.utc)
    # Normalize slot_start_utc string from either dict or datetime
    try:
        if isinstance(slot_start_dt, dict):
            us = slot_start_dt.get("utc_start")
        else:
            us = slot_start_dt
        if isinstance(us, datetime):
            slot_start_utc = us.isoformat()
        else:
            slot_start_utc = str(us)
    except Exception:
        slot_start_utc = ""

    def _write_waste_log():
        ensure_waste_log_header()
        with open(WASTE_LOG_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                now_utc.isoformat(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                slot_start_utc,
                int(latency_ms),
                what or "",
                consequences or "",
                (active_task.get("id") if active_task else None),
                (active_task.get("title") if active_task else "")
            ])

    return _safe_csv_write(WASTE_LOG_PATH, _write_waste_log)


def ensure_focus_log_header():
    """Ensure focus confirmation log CSV exists with headers."""
    _rotate_csv_if_needed(FOCUS_LOG_PATH)

    def _write_header():
        needs_header = True
        try:
            if os.path.exists(FOCUS_LOG_PATH):
                try:
                    needs_header = os.path.getsize(FOCUS_LOG_PATH) == 0
                except Exception:
                    needs_header = True
            with open(FOCUS_LOG_PATH, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if needs_header:
                    w.writerow([
                        "event_utc", "event_local",
                        "slot_start_utc", "response_latency_ms",
                        "doing", "benefits",
                        "active_task_id", "active_task_title"
                    ])
        except Exception:
            log_exception("ensure_focus_log_header failed")

    return _safe_csv_write(FOCUS_LOG_PATH, _write_header)


def append_focus_log(*, slot_start_dt, latency_ms, doing, benefits, active_task):
    """Log studying confirmation details to CSV."""
    now_utc = datetime.now(timezone.utc)
    try:
        if isinstance(slot_start_dt, dict):
            us = slot_start_dt.get("utc_start")
        else:
            us = slot_start_dt
        if isinstance(us, datetime):
            slot_start_utc = us.isoformat()
        else:
            slot_start_utc = str(us)
    except Exception:
        slot_start_utc = ""

    def _write_focus_log():
        ensure_focus_log_header()
        with open(FOCUS_LOG_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                now_utc.isoformat(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                slot_start_utc,
                int(latency_ms),
                doing or "",
                benefits or "",
                (active_task.get("id") if active_task else None),
                (active_task.get("title") if active_task else "")
            ])

    return _safe_csv_write(FOCUS_LOG_PATH, _write_focus_log)
