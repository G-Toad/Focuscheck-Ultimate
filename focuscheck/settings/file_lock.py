"""Cross-process lock for the settings repository."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def settings_file_lock(settings_path: str, timeout: float = 5.0):
    """Lock one sidecar byte so separate FocusCheck processes serialize saves."""
    lock_path = Path(f"{settings_path}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    acquired = False
    deadline = time.monotonic() + max(0.1, float(timeout))
    try:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        while time.monotonic() < deadline:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except (BlockingIOError, OSError):
                time.sleep(0.05)
        if not acquired:
            raise TimeoutError(f"settings lock timeout: {lock_path}")
        yield
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()
