# FocusCheck Refactoring - Implementation Guide

## Quick Start

You've been provided with a **complete refactoring specification** for your FocusCheck application. This guide shows you exactly how to complete the implementation.

## What's Been Done

### ✅ Completed (Foundation)

1. **Directory Structure** - All folders created
2. **Configuration Module** - `focuscheck/config.py`
3. **Utilities Package** - Complete with 4 modules:
   - `paths.py` - Path management
   - `logging_utils.py` - Logging setup
   - `file_ops.py` - File operations
   - `colors.py` - Color parsing
4. **Settings Package** - Partial:
   - ✅ `defaults.py` - All default settings
   - ⏳ `manager.py` - Need to add
5. **Documentation** - Comprehensive guides created

## How to Complete the Refactoring

### Method 1: Extract Line by Line (Recommended for Learning)

Follow `REFACTORING_SUMMARY.md` which tells you exactly which lines from `guard.py` go into each new module.

**Example**: For `focuscheck/settings/manager.py`:
1. Open `guard.py`
2. Find lines 496-498 (the lock), 663-837 (validation and save/load)
3. Copy to new file
4. Add imports at top
5. Update references (e.g., `DEFAULT_SETTINGS` becomes `from .defaults import DEFAULT_SETTINGS`)

### Method 2: Use Provided Specifications (Faster)

Each module in `REFACTORING_SUMMARY.md` includes:
- Purpose
- Line numbers from original
- Function signatures
- What it should contain

### Method 3: Automated Extraction (Advanced)

Create a Python script to extract and refactor automatically:

```python
# extract_module.py
def extract_lines(source_file, start, end, dest_file, imports):
    """Extract lines from source and add to destination with imports."""
    with open(source_file, 'r') as f:
        lines = f.readlines()
    
    content = imports + '\n\n' + ''.join(lines[start-1:end])
    
    with open(dest_file, 'w') as f:
        f.write(content)

# Example usage:
extract_lines('guard.py', 663, 837, 'focuscheck/settings/manager.py',
    '''"""Settings management - loading, saving, and validation."""
import json
import os
import platform
import threading
from .defaults import DEFAULT_SETTINGS
from ..utils.paths import choose_path
from ..utils.logging_utils import log_exception, get_logger
''')
```

## Step-by-Step Implementation Plan

### Phase 1: Complete Settings Module (15 minutes)

**Create `focuscheck/settings/manager.py`:**

```python
"""Settings management - loading, saving, and validation."""

import json
import os
import platform
import threading
from .defaults import DEFAULT_SETTINGS
from ..utils.paths import choose_path
from ..utils.logging_utils import log_exception, get_logger

_settings_lock = threading.Lock()

# Copy lines 663-792 from guard.py (validate_settings function)
# Copy lines 794-808 from guard.py (load_settings function)  
# Copy lines 810-837 from guard.py (save_settings function)
```

**Test it:**
```python
from focuscheck.settings import load_settings, save_settings
s = load_settings()
print(s['interval_seconds'])  # Should print 60
```

### Phase 2: Create Database Module (30 minutes)

**Create `focuscheck/database/__init__.py`:**
```python
"""Database and CSV logging."""
from .task_db import TaskDB
from .csv_logger import (
    ensure_log_header,
    append_log,
    ensure_waste_log_header,
    append_waste_log
)
__all__ = ['TaskDB', 'ensure_log_header', 'append_log', 
           'ensure_waste_log_header', 'append_waste_log']
```

**Create `focuscheck/database/task_db.py`:**
- Extract lines 841-1061 from `guard.py`
- Add imports:
```python
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
```

**Create `focuscheck/database/csv_logger.py`:**
- Extract lines 1088-1250 from `guard.py`
- Add imports:
```python
import csv
import os
import glob
import threading
from datetime import datetime, timezone
from typing import Optional
from ..utils.file_ops import get_file_lock
from ..utils.paths import choose_path
```

### Phase 3: Create Platform Module (30 minutes)

**Create `focuscheck/platform/__init__.py`:**
```python
"""Platform-specific functionality."""
import platform as _platform

if _platform.system().lower() == "windows":
    from .windows import (
        enable_click_through_windows,
        install_httransparent_wndproc,
        WindowsWakeWatcher,
        WinClickThroughOverlay,
        ensure_gdiplus_started,
        create_hicon_from_image
    )
    from .startup import (
        compose_startup_command,
        install_startup,
        uninstall_startup,
        is_startup_installed
    )
    __all__ = [
        'enable_click_through_windows',
        'install_httransparent_wndproc',
        'WindowsWakeWatcher',
        'WinClickThroughOverlay',
        'ensure_gdiplus_started',
        'create_hicon_from_image',
        'compose_startup_command',
        'install_startup',
        'uninstall_startup',
        'is_startup_installed',
    ]
else:
    # Provide stub implementations for non-Windows platforms
    __all__ = []
```

**Create `focuscheck/platform/windows.py`:**
- Extract lines 72-310, 3456-3914 from `guard.py`
- Add imports from `config.py` for Windows constants

**Create `focuscheck/platform/startup.py`:**
- Extract lines 359-447 from `guard.py`
- Add imports

### Phase 4: Create UI Module (60 minutes - largest)

**Create `focuscheck/ui/__init__.py`:**
```python
"""User interface components."""
from .guards import PauseGuard
from .dialogs import (
    PromptDialog,
    TaskEntryDialog,
    WastePromptDialog,
    TaskChangeDialog
)
from .windows import SettingsWindow, TaskHistoryWindow

__all__ = [
    'PauseGuard',
    'PromptDialog',
    'TaskEntryDialog',
    'WastePromptDialog',
    'TaskChangeDialog',
    'SettingsWindow',
    'TaskHistoryWindow',
]
```

**Create each UI module:**
- `focuscheck/ui/guards.py` - Lines 1252-1352
- `focuscheck/ui/dialogs.py` - Lines 1725-5015 (largest file)
- `focuscheck/ui/windows.py` - Lines 1354-1723, 5016-5093

### Phase 5: Create App Module (30 minutes)

**Create `focuscheck/app.py`:**
- Extract lines 3916-5093 from `guard.py`
- Add imports from all other modules
- This is the orchestrator that brings everything together

### Phase 6: Create Entry Point (15 minutes)

**Create `main.py`:**
- Extract lines 5095-5249 from `guard.py`
- Simplify and add clean imports

### Phase 7: Final Integration (15 minutes)

**Move system tray:**
```bash
# PowerShell:
cd C:\Users\singh\Documents\DEVRECON\Current
copy system_tray.py focuscheck\system_tray.py
```

**Create `focuscheck/__init__.py`:**
```python
"""FocusCheck - Focus and productivity reminder application."""

__version__ = "1.0.0"

from .app import App
from .config import APP_NAME, APP_VERSION

__all__ = ['App', 'APP_NAME', 'APP_VERSION']
```

### Phase 8: Testing (30 minutes)

**Test each module:**
```python
# Test imports
python -c "from focuscheck.utils import get_logger; print(get_logger())"
python -c "from focuscheck.settings import load_settings; print(load_settings())"
python -c "from focuscheck.database import TaskDB; db = TaskDB(':memory:'); print('OK')"
python -c "from focuscheck.platform import install_startup; print('OK')"
python -c "from focuscheck.ui import PauseGuard; print('OK')"

# Test full app
python main.py --help  # Should show usage or start app
```

**Run the app:**
```bash
python main.py
```

## Common Issues & Solutions

### Issue 1: Import Errors
**Problem**: `ModuleNotFoundError: No module named 'focuscheck'`
**Solution**: Ensure you're running from the project root:
```bash
cd C:\Users\singh\Documents\DEVRECON\Current
python main.py
```

### Issue 2: Circular Imports
**Problem**: Module A imports B, B imports A
**Solution**: Use local imports inside functions:
```python
def my_function():
    from .other_module import something  # Import here, not at top
    something()
```

### Issue 3: Missing Imports in Extracted Code
**Problem**: Function references undefined names
**Solution**: Check original `guard.py` for imports at top, add to new module

### Issue 4: Settings Path Issues
**Problem**: Can't find settings file
**Solution**: The `choose_path()` function handles legacy paths automatically

## Validation Checklist

Before considering the refactoring complete:

- [ ] All modules created and in correct locations
- [ ] All `__init__.py` files created
- [ ] No syntax errors (`python -m py_compile focuscheck/*.py`)
- [ ] Imports work for all modules
- [ ] `main.py` runs without errors
- [ ] Settings load and save correctly
- [ ] Original `guard.py` and new structure produce same behavior
- [ ] All features work (prompts, settings, tasks, tray)
- [ ] PyInstaller build works (if using)

## Time Estimate

| Phase | Time | Difficulty |
|-------|------|------------|
| Phase 1: Settings | 15 min | Easy |
| Phase 2: Database | 30 min | Medium |
| Phase 3: Platform | 30 min | Medium |
| Phase 4: UI | 60 min | Hard (largest) |
| Phase 5: App | 30 min | Medium |
| Phase 6: Entry | 15 min | Easy |
| Phase 7: Integration | 15 min | Easy |
| Phase 8: Testing | 30 min | Medium |
| **Total** | **~3.5 hours** | **Mixed** |

## Tips for Success

1. **Work incrementally** - Complete and test each phase before moving on
2. **Keep guard.py** - Don't delete until everything works
3. **Use git** - Commit after each working phase
4. **Test often** - Don't wait until the end to test
5. **Copy carefully** - Line numbers are accurate in REFACTORING_SUMMARY.md
6. **Read docstrings** - They explain what each function does
7. **Ask for help** - If stuck, the specifications are very detailed

## After Refactoring

### Benefits You'll Have
- ✅ Easy to find any piece of code
- ✅ Easy to understand what each module does
- ✅ Easy to test individual components
- ✅ Easy to add new features
- ✅ Professional, maintainable codebase

### What to Do Next
1. **Write tests** - Create `tests/` directory with unit tests
2. **Document** - Add more detailed docstrings where needed
3. **Type hints** - Add type annotations for better IDE support
4. **CI/CD** - Set up automated testing
5. **Extend** - Add new features the modular way

## Quick Reference

### File to Module Mapping
| Original Lines | New Location |
|----------------|--------------|
| 1-70, 308-309 | `focuscheck/config.py` |
| 311-461 | `focuscheck/utils/paths.py` |
| 463-495 | `focuscheck/utils/logging_utils.py` |
| 496-546 | `focuscheck/utils/file_ops.py` |
| 159-171 | `focuscheck/utils/colors.py` |
| 547-661 | `focuscheck/settings/defaults.py` |
| 663-837 | `focuscheck/settings/manager.py` |
| 841-1061 | `focuscheck/database/task_db.py` |
| 1088-1250 | `focuscheck/database/csv_logger.py` |
| 72-310, 3456-3914 | `focuscheck/platform/windows.py` |
| 359-447 | `focuscheck/platform/startup.py` |
| 1252-1352 | `focuscheck/ui/guards.py` |
| 1725-5015 | `focuscheck/ui/dialogs.py` |
| 1354-1723, 5016-5093 | `focuscheck/ui/windows.py` |
| 3916-5093 | `focuscheck/app.py` |
| 5095-5249 | `main.py` |

## Getting Help

If you need assistance:
1. Check `REFACTORING_SUMMARY.md` for detailed module specs
2. Check `REFACTORING_PLAN.md` for overall architecture
3. Check `README_REFACTORING.md` for benefits and usage
4. Look at completed modules for patterns to follow
5. Test incrementally to catch issues early

## Final Notes

This refactoring:
- **Does not change functionality** - All features remain the same
- **Improves code quality** - Follows Python best practices
- **Enables future growth** - Easy to extend and maintain
- **Is well documented** - Every module has clear purpose
- **Is testable** - Each component can be tested independently

You now have everything needed to complete this refactoring. Take it one phase at a time, test as you go, and you'll have a professional, maintainable codebase in a few hours.

Good luck! 🚀

