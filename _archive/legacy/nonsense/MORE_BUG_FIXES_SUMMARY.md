# FocusCheck - 5 More Critical Bug Fixes

## Summary
Fixed 5 additional critical bugs affecting single-instance checking, sequential phrase rotation, task analytics, error logging, and tray action feedback.

---

## Bug 1: Single-Instance Guard is Ineffective 🔒

### Problem
**Location:** `file_ops.py:59-73`

The mutex loop tried to create mutexes in order:
1. `Global\FocusCheck_Mutex` - if already exists (ERROR_ALREADY_EXISTS)
2. Loop **continues** instead of stopping
3. Creates `Local\FocusCheck_Mutex` and returns True
4. Result: **Multiple instances run simultaneously**

**Code Issue:**
```python
for name in names:
    handle = k32.CreateMutexW(None, True, ctypes.c_wchar_p(name))
    if handle:
        last = k32.GetLastError()
        if last == ERROR_ALREADY_EXISTS:
            k32.CloseHandle(handle)
            continue  # ❌ WRONG: tries next mutex instead of stopping!
```

**Scenario:**
- Instance 1: Acquires `Global\FocusCheck_Mutex` → Returns True ✓
- Instance 2: Tries `Global\FocusCheck_Mutex` → EXISTS → Continues
- Instance 2: Tries `Local\FocusCheck_Mutex` → Acquires it → Returns True ❌
- Result: **Both instances running!**

### Fix
```python
for name in names:
    handle = k32.CreateMutexW(None, True, ctypes.c_wchar_p(name))
    if handle:
        last = k32.GetLastError()
        if last == ERROR_ALREADY_EXISTS:
            # Another instance detected - STOP immediately
            k32.CloseHandle(handle)
            get_logger().warning("single-instance: another instance detected via '%s'; exiting", name)
            return False  # ✅ Return False immediately

        # Successfully acquired mutex
        _single_instance_handle = handle
        get_logger().info("single-instance acquired via mutex '%s'", name)
        return True
```

**Files Modified:**
- `focuscheck/utils/file_ops.py` (lines 59-85)

**Result:**
✅ Second instance immediately exits when mutex already held
✅ Only one FocusCheck instance can run at a time

---

## Bug 2: Sequential Phrase Acronym Mode Never Advances 🔄

### Problem
**Location:** `anti_habit.py:305-329`

Sequential mode incremented index in memory but never persisted it:
1. Updates `self.settings["study_phrase_index"]` in memory
2. Tries to persist via `self.app.save_settings()`
3. **But:** PromptDialog only has `app_ref`, not `app`
4. **And:** App class has no `save_settings` method
5. Settings reloaded on each new dialog → index resets to 0
6. Result: **Always shows first phrase**

**Code Issue:**
```python
# Line 322: Update in memory
self.settings[f"{prefix}_phrase_index"] = (index + 1) % len(phrase_list)

# Lines 325-329: Try to save (FAILS)
try:
    if hasattr(self, 'app') and hasattr(self.app, 'save_settings'):
        self.app.save_settings()  # ❌ self.app doesn't exist!
except Exception:
    pass
```

**Scenario:**
- User sets: Sequential, List = ["Work", "Study", "Code"]
- Dialog 1: Shows "Work", increments to 1 in memory
- Dialog closes, index lost
- Dialog 2: Loads settings from disk → index=0 → Shows "Work" again ❌

### Fix
```python
# Line 18: Add import
from ....settings.manager import save_settings

# Lines 326-334: Use module function to persist
self.settings[f"{prefix}_phrase_index"] = (index + 1) % len(phrase_list)

# Persist the updated index to disk so it advances on next dialog
try:
    if save_settings:  # Use imported module function
        save_settings(self.settings)
except Exception:
    pass
```

**Files Modified:**
- `focuscheck/ui/dialogs/prompt_dialog_mixins/anti_habit.py` (lines 17-20, 329-334)

**Result:**
✅ Index persists to disk after each dialog
✅ Sequential mode cycles through all phrases
✅ Phrases advance: "Work" → "Study" → "Code" → "Work" → ...

---

## Bug 3: Overdue Task Completions Don't Set timed_out Flag ⏰

### Problem
**Location:** `task_management.py:335-349`

When user marks overdue task as "Done":
1. Code checks if `datetime.now() > due_dt`
2. If overdue, calls `self.taskdb.mark_failed(task_id)`
3. **Missing:** `timed_out=True` parameter
4. Database column `timed_out` remains 0
5. Analytics can't distinguish manual fails from deadline expirations
6. "Timed Out" count always shows 0

**Code Issue:**
```python
if is_overdue:
    self.taskdb.mark_failed(task_id)  # ❌ Missing timed_out=True
else:
    self.taskdb.mark_completed(task_id)
```

**Database Method:**
```python
def mark_failed(self, task_id, when_utc=None, timed_out=False):
    # Updates: SET timed_out=1 WHERE timed_out=True
```

**Scenario:**
- Task due: 2:00 PM
- User marks "Done": 3:00 PM (1 hour late)
- Recorded as "failed" but timed_out=0
- Analytics show: Completed=0, Failed=1, **Timed Out=0** ❌
- User can't tell if they gave up or just ran out of time

### Fix
```python
if is_overdue:
    # Mark as failed with timed_out=True to distinguish from manual fails
    self.taskdb.mark_failed(task_id, timed_out=True)
else:
    self.taskdb.mark_completed(task_id)
```

**Files Modified:**
- `focuscheck/ui/dialogs/prompt_dialog_mixins/task_management.py` (line 340-341)

**Result:**
✅ Overdue completions set timed_out=1 in database
✅ Analytics accurately show "Timed Out" count
✅ Users can distinguish:
- **Completed:** Finished on time
- **Failed (timed_out=0):** Manually gave up
- **Failed (timed_out=1):** Ran out of time

---

## Bug 4: TaskHistoryWindow Imports Non-Existent Module 📦

### Problem
**Location:** `windows.py:846-849` (and 3 backup files)

Tried to import from non-existent module:
```python
from focuscheck.core.logging import log_exception  # ❌ Doesn't exist!
```

**Directory structure:**
```
focuscheck/
├── utils/
│   └── logging_utils.py  ← Actual location
├── core/  ← DOESN'T EXIST
└── ui/
    └── windows.py
```

**Result:**
- Import fails silently
- Falls back to no-op `log_exception`
- All errors in history window disappear
- No way to debug issues

**Code Issue:**
```python
try:
    from focuscheck.core.logging import log_exception  # ❌ Wrong path
except ImportError:
    def log_exception(msg):
        pass  # ❌ Errors disappear
```

### Fix
```python
try:
    from focuscheck.utils.logging_utils import log_exception  # ✅ Correct path
except ImportError:
    # Fallback if logging not available
    def log_exception(msg):
        pass
```

**Files Modified:**
- `focuscheck/ui/windows.py` (line 846)
- `focuscheck/ui/windows_modern_backup.py` (line 511)
- `focuscheck/ui/windows_new.py` (line ~511)
- `focuscheck/ui/windows_old_backup.py` (line ~511)

**Result:**
✅ Exceptions properly logged
✅ Developers can debug history window issues
✅ Error tracebacks appear in logs

---

## Bug 5: Tray Actions Return None, Triggering Fallback Logic 🪟

### Problem
**Location:** `app.py:852-886, 963-967` + `system_tray.py:368-413`

Tray menu expects app hooks to return boolean indicating success/failure.
These methods returned `None`:
- `_tray_open_data_folder`
- `_tray_open_logs_folder`
- `_tray_install_startup`
- `_tray_uninstall_startup`
- `_open_task_dialog_from_tray`

**Result 1: Duplicate Folder Opens**
```python
# system_tray.py:381-385
def _open_data(self, icon: Any, item: Any) -> None:
    if self._call_app('_tray_open_data_folder'):  # Returns None → False
        return
    # ❌ Falls through to fallback even though folder already opened
    if self._config_path and os.path.exists(self._config_path):
        self._open_path_in_os(os.path.dirname(self._config_path))
```

**Scenario:**
- User clicks "Open data folder"
- `_tray_open_data_folder` runs `os.startfile(path)` → Opens Explorer ✓
- Returns `None` (implicit)
- Tray interprets as False → Falls through to fallback
- Fallback runs `_open_path_in_os()` → Opens second Explorer ❌

**Result 2: False Warnings**
```python
# system_tray.py:407-413
def _toggle_startup(self, icon: Any, item: Any) -> None:
    if self._startup_checked():
        if not self._call_app('_tray_uninstall_startup'):  # Returns None → False
            logger.warning('SystemTray: disable startup unavailable')  # ❌ False warning
```

**Scenario:**
- User clicks "Run on startup" → Enable
- `_tray_install_startup` runs successfully, shows messagebox ✓
- Returns `None` (implicit)
- Tray logs: "enable startup unavailable" ❌ (even though it worked!)

### Fix

**Add explicit returns to all 5 methods:**

```python
def _tray_open_data_folder(self):
    try:
        path = get_data_dir()
        if platform.system().lower() == 'windows':
            os.startfile(path)
        else:
            subprocess.Popen(['xdg-open', path])
        return True  # ✅ Successfully opened
    except Exception:
        return False  # ✅ Failed

def _tray_open_logs_folder(self):
    try:
        path = os.path.dirname(APP_LOG_PATH)
        if platform.system().lower() == 'windows':
            os.startfile(path)
        else:
            subprocess.Popen(['xdg-open', path])
        return True  # ✅ Successfully opened
    except Exception:
        return False  # ✅ Failed

def _tray_install_startup(self):
    try:
        ok = install_startup(APP_NAME)
        if ok:
            messagebox.showinfo("Startup", "Enabled run on startup.")
        return bool(ok)  # ✅ Return actual result
    except Exception:
        return False  # ✅ Failed

def _tray_uninstall_startup(self):
    try:
        ok = uninstall_startup(APP_NAME)
        if ok:
            messagebox.showinfo("Startup", "Disabled run on startup.")
        return bool(ok)  # ✅ Return actual result
    except Exception:
        return False  # ✅ Failed

def _open_task_dialog_from_tray(self):
    if getattr(self, "taskdb", None) is None:
        messagebox.showerror("Unavailable", "Task database not available.")
        return False  # ✅ Failed - no database
    try:
        TaskEntryDialog(self.root, on_submit=self._on_new_task_from_tray)
        return True  # ✅ Successfully opened
    except Exception:
        return False  # ✅ Failed
```

**Files Modified:**
- `focuscheck/app.py` (lines 852-890, 967-975)

**Result:**
✅ "Open folder" actions open ONE window (not two)
✅ No false "unavailable" warnings in logs
✅ Tray knows when actions succeed or fail
✅ Proper error handling when actions fail

---

## Testing

### Bug 1 (Single-instance):
```bash
# Should block second instance
1. Launch FocusCheck.exe
2. Launch FocusCheck.exe again
3. Check logs: "single-instance: another instance detected via 'Global\FocusCheck_Mutex'; exiting"
4. Only ONE tray icon appears
```

### Bug 2 (Sequential phrases):
```bash
# Should cycle through all phrases
1. Settings → Study Phrase Mode: Sequential
2. Study Phrase List: ["Alpha", "Beta", "Gamma"]
3. Trigger dialog 1 → "Alpha"
4. Trigger dialog 2 → "Beta" (NOT "Alpha" again!)
5. Trigger dialog 3 → "Gamma"
6. Trigger dialog 4 → "Alpha" (wraps around)
7. Check settings.json: "study_phrase_index": 1 (persisted!)
```

### Bug 3 (timed_out flag):
```bash
# Should set timed_out=1 for overdue completions
1. Create task due at 2:00 PM
2. Wait until 2:05 PM (past due)
3. Mark task "Done" in dialog
4. Query: SELECT id, status, timed_out FROM tasks WHERE id=X
5. Should show: status='failed', timed_out=1
6. Task History window: Shows in "Timed Out" column
```

### Bug 4 (Import error):
```bash
# Should log exceptions
1. Open Task History window
2. Corrupt database or trigger error
3. Check logs: Should see full traceback
4. Before fix: Silent, no logs
```

### Bug 5 (Tray returns):
```bash
# Should open ONE folder, no false warnings
1. Right-click tray → "Open data folder"
2. Result: ONE Explorer window opens (not two)
3. Right-click tray → "Run on startup" → Check
4. Result: Messagebox appears, NO warning in logs
5. Check logs: Should NOT see "enable startup unavailable"
```

---

## Impact

### Before Fixes:
❌ Multiple app instances could run simultaneously
❌ Sequential phrase mode stuck on first phrase
❌ Task analytics missing "Timed Out" data
❌ History window errors disappeared silently
❌ Tray actions opened duplicate windows & logged false warnings

### After Fixes:
✅ Single-instance guard works correctly
✅ Sequential phrases advance and cycle through list
✅ Task analytics accurately track timeouts
✅ All errors properly logged and debuggable
✅ Tray actions work cleanly with no duplicates

---

## Files Changed

1. `focuscheck/utils/file_ops.py` - Fixed mutex guard logic
2. `focuscheck/ui/dialogs/prompt_dialog_mixins/anti_habit.py` - Fixed sequential phrase persistence
3. `focuscheck/ui/dialogs/prompt_dialog_mixins/task_management.py` - Added timed_out flag
4. `focuscheck/ui/windows.py` + 3 backups - Fixed import path
5. `focuscheck/app.py` - Added return values to 5 tray methods

## Backward Compatibility

✅ All changes backward compatible
✅ No breaking API changes
✅ Existing behavior preserved except for bug fixes
✅ Database schema unchanged (timed_out column already existed)
