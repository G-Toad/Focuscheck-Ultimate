# FocusCheck - 5 Critical Bug Fixes

## Summary
Fixed 5 critical bugs affecting snooze functionality, settings persistence, tray icons, field validation, and button phrase customization.

---

## Bug 1: Snooze Doesn't Actually Pause Reminders ⏰

### Problem
- `app.py:785` called `_set_paused(False, ...)` which **UNPAUSED** instead of pausing
- Result: Reminders fired immediately instead of being snoozed
- Snooze reminder dialog never appeared because `settings["paused"]` was False
- System tray showed "running" instead of "snoozed"

### Fix
**Files Modified:**
- `focuscheck/app.py` (lines 119, 779-844)

**Changes:**
1. Added `self._snooze_unpause_timer_id = None` tracking variable (line 119)
2. Changed line 788 from `_set_paused(False, ...)` to `_set_paused(True, ...)`
3. Added timer cancellation for existing snooze timers (lines 822-828)
4. Added automatic unpause timer that fires after snooze duration (lines 830-843)
5. Timer calls `_set_paused(False, source="snooze_expired_Xm")` when snooze expires

**How It Works Now:**
1. User clicks "Snooze 5 minutes" → `paused=True` is set and saved
2. Snooze reminder loop detects `paused=True` and starts showing reminders
3. After 5 minutes, timer fires → `paused=False` is set
4. Normal reminder schedule resumes

---

## Bug 2: "Require All Fields" Toggle Has No Effect 📝

### Problem
- `focus_prompt_dialog.py:183-190` and `waste_prompt_dialog.py:183-190`
- Comment said "Always require all visible fields"
- Code unconditionally validated all fields were non-empty
- `self.require_all_fields` was set but never consulted
- Users couldn't skip optional fields even when setting was disabled

### Fix
**Files Modified:**
- `focuscheck/ui/dialogs/focus_prompt_dialog.py` (lines 183-201)
- `focuscheck/ui/dialogs/waste_prompt_dialog.py` (lines 183-201)

**Changes:**
```python
# OLD: Always required all fields
if not value:
    messagebox.showerror(...)
    return

# NEW: Respect require_all_fields setting
has_challenge = bool(ctrl.get("challenge"))
should_require = has_challenge or self.require_all_fields

if should_require and not value:
    messagebox.showerror(...)
    return

# Skip remaining validation if field is empty and not required
if not value:
    continue
```

**Logic:**
- Fields with challenges are ALWAYS required (security)
- Other fields only required if `require_all_fields=True`
- Empty optional fields skip spam detection and other validation

---

## Bug 3: Tray Icon Path is Wrong 🖼️

### Problem
- `app.py:252` built path: `get_base_dir() + '/focuscheck/assets'`
- But `get_base_dir()` returned `<project>/focuscheck/utils` (where paths.py lives)
- Result: Looked for icon at `focuscheck/utils/focuscheck/assets/tray_icon.png` ❌
- Correct path is: `<project>/focuscheck/assets/tray_icon.png` ✅
- Custom tray icons never loaded

### Fix
**Files Modified:**
- `focuscheck/utils/paths.py` (lines 13-20)

**Changes:**
```python
# OLD: Returned utils folder
def get_base_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()

# NEW: Returns focuscheck package root
def get_base_dir():
    """Get the base directory of the application (focuscheck package root)."""
    try:
        # Return focuscheck package root, not utils folder
        # __file__ is in focuscheck/utils/paths.py, so go up one level
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        return os.getcwd()
```

**Result:**
- `get_base_dir()` now returns `<project>/focuscheck`
- `app.py:252` correctly finds `<project>/focuscheck/assets/tray_icon.png`

---

## Bug 4: validate_settings Drops Unknown Keys 🗝️

### Problem
- `settings/manager.py:14-20` promised to "preserve unknown keys" but didn't
- Only looped over `DEFAULT_SETTINGS` keys
- `save_settings()` calls `validate_settings()` before writing (line 455)
- Result: Plugin settings or newer-version keys deleted on save
- Breaking forward compatibility

### Fix
**Files Modified:**
- `focuscheck/settings/manager.py` (lines 14-27)

**Changes:**
```python
# OLD: Only copied known keys
s = DEFAULT_SETTINGS.copy()
for k in DEFAULT_SETTINGS:
    if k in data:
        s[k] = data[k]

# NEW: Preserve ALL keys, then apply defaults
s = DEFAULT_SETTINGS.copy()

# FIRST: Merge ALL keys from data (including unknown ones)
for k, v in data.items():
    s[k] = v

# SECOND: Apply defaults for any missing keys
for k, v in DEFAULT_SETTINGS.items():
    if k not in s:
        s[k] = v

# THIRD: Coercions and clamps for known settings
```

**Result:**
- Unknown keys (from plugins, future versions) are preserved
- Saves maintain all custom settings
- Forward compatibility maintained

---

## Bug 5: Study/Wasting Button Phrases Are Dead Code 🔘

### Problem
- Settings UI exposed `study_phrase_list`, `waste_phrase_list`, `*_phrase_mode`, `*_phrase_override`
- `prompt_dialog.py:337-342` hardcoded `text="Studying"` and `text="Wasting time"`
- No code referenced phrase settings outside settings UI
- Users edited phrase lists thinking it worked - it didn't

### Fix
**Files Modified:**
- `focuscheck/ui/dialogs/prompt_dialog.py` (lines 12, 109-111, 337-388)

**Changes:**
1. Added `import random` (line 12)
2. Added phrase tracking variables in `__init__` (lines 109-111):
   ```python
   self._study_phrase_index = 0
   self._waste_phrase_index = 0
   ```
3. Added `_get_button_phrase(button_type)` method (lines 337-372)
4. Modified `_create_buttons()` to use dynamic text (lines 379-388)

**How It Works:**

```python
def _get_button_phrase(self, button_type):
    mode = self.settings.get(f"{button_type}_phrase_mode", "random")
    override = self.settings.get(f"{button_type}_phrase_override", "")
    phrase_list = self.settings.get(f"{button_type}_phrase_list", [])

    # Override mode - use single phrase
    if mode == "override" and override:
        return override

    # Empty list fallback
    if not phrase_list:
        return "Studying" if button_type == "study" else "Wasting time"

    # Random mode - different phrase each dialog
    if mode == "random":
        return random.choice(phrase_list)

    # Sequential mode - cycle through list
    # (index tracked per dialog instance)
    return phrase_list[index % len(phrase_list)]
```

**Modes:**
- **Override:** Single custom phrase (e.g., "Working")
- **Random:** Different random phrase from list each time
- **Sequential:** Cycles through list in order (prevents habituation)
- **Empty list:** Falls back to defaults ("Studying", "Wasting time")

---

## Testing

### Bug 1 (Snooze):
```bash
# Test snooze sets paused=True
1. Click "Snooze 5 minutes" in system tray
2. Check settings file: "paused": true
3. Wait - snooze reminder should appear
4. After 5 minutes, paused automatically clears
5. Normal reminders resume
```

### Bug 2 (Require fields):
```bash
# Test with require_all_fields=False
1. Settings → Behavior → Uncheck "Require all prompt fields"
2. Trigger reminder dialog
3. Leave optional field empty
4. Should be able to submit ✓

# Test with challenge (always required)
1. Enable phrase acronym challenge
2. Leave field empty
3. Should be blocked even if require_all_fields=False
```

### Bug 3 (Tray icon):
```bash
# Test custom tray icon loads
1. Place tray_icon.png in focuscheck/assets/
2. Launch app
3. Check logs: "Using custom tray icon: .../focuscheck/assets/tray_icon.png"
4. Tray icon should display custom image
```

### Bug 4 (Unknown keys):
```bash
# Test unknown keys preserved
1. Manually add to settings.json: {"plugin_custom": "test"}
2. Change any setting via UI and save
3. Reload settings.json
4. Verify "plugin_custom": "test" still exists ✓
```

### Bug 5 (Button phrases):
```bash
# Test override mode
1. Settings → Behavior → Study Phrase Mode: Override
2. Study Phrase Override: "Deep Work"
3. Trigger reminder → button should say "Deep Work" ✓

# Test random mode
1. Settings → Behavior → Study Phrase Mode: Random
2. Study Phrase List: ["Working", "Coding", "Learning"]
3. Trigger multiple reminders → different phrases each time

# Test sequential mode
1. Settings → Behavior → Study Phrase Mode: Sequential
2. Study Phrase List: ["First", "Second", "Third"]
3. Trigger 3 reminders → should see "First", "Second", "Third" in order
```

---

## Impact

### Before Fixes:
❌ Snooze didn't work - reminders fired immediately
❌ "Require all fields" toggle had no effect
❌ Custom tray icons never loaded
❌ Plugin settings deleted on save
❌ Button phrase customization was fake

### After Fixes:
✅ Snooze actually pauses reminders for X minutes
✅ Optional fields can be skipped when setting disabled
✅ Custom tray icons load from correct path
✅ Unknown settings preserved across saves
✅ Button phrases fully customizable with 3 modes

---

## Files Changed

1. `focuscheck/app.py` - Snooze timer management
2. `focuscheck/utils/paths.py` - Fixed get_base_dir() path
3. `focuscheck/settings/manager.py` - Preserve unknown keys
4. `focuscheck/ui/dialogs/focus_prompt_dialog.py` - Honor require_all_fields
5. `focuscheck/ui/dialogs/waste_prompt_dialog.py` - Honor require_all_fields
6. `focuscheck/ui/dialogs/prompt_dialog.py` - Implement button phrases

## Backward Compatibility

✅ All changes are backward compatible
✅ Default behavior unchanged (falls back to hardcoded phrases if no list)
✅ Existing settings files continue to work
✅ No breaking API changes
