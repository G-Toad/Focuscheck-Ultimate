"""Test-package isolation bootstrap.

Tests must never default to the operator's live FocusCheck profile. The
verification runner supplies its own root; this fallback protects direct
``unittest`` invocations as well.
"""

from __future__ import annotations

import os
from pathlib import Path


os.environ.setdefault(
    "FOCUS_DATA_DIR",
    str(Path(__file__).resolve().parents[1] / "_qa_runtime" / "unit_data"),
)
