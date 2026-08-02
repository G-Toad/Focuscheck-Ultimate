# UX Improvements Report

## Summary

Fixed two common-sense design issues in the FocusCheck UI:

1. ✅ **"Wasting time" button now has anti-habit press-and-hold functionality**
2. ✅ **Cancel in waste prompt returns to main dialog instead of closing everything**

---

## Issue #1: Wasting Time Button Missing Anti-Habit Feature

### Problem
The "Wasting time" button was using a simple click handler while the "Studying" button required press-and-hold for anti-habit training. This inconsistency made it too easy to accidentally click "Wasting time".

### Root Cause
**File:** `focuscheck/ui/dialogs.py`

The button was created with `command=self._on_wasting_clicked` (simple click) instead of using `<ButtonPress-1>` and `<ButtonRelease-1>` event bindings like the "Studying" button.

**Before:**
```python
# Line 326-327 (old)
self.btn_waste = tk.Button(self.button_row, text="Wasting time",
                           font=("Segoe UI", 16, "bold"),
                           relief="solid", bd=2, width=14,
                           command=self._on_wasting_clicked)  # Simple click
```

### Solution Applied

#### 1. Removed `command=` parameter and added event bindings

**File:** `focuscheck/ui/dialogs.py:326-335`

```python
# Create button without command parameter
self.btn_waste = tk.Button(self.button_row, text="Wasting time",
                           font=("Segoe UI", 16, "bold"),
                           relief="solid", bd=2, width=14)

# Apply anti-habit to wasting button too
if self.btn_waste is not None:
    self.btn_waste.bind("<ButtonPress-1>", self._waste_hold_start)
    self.btn_waste.bind("<ButtonRelease-1>", self._waste_hold_end)
```

#### 2. Added press-and-hold handlers

**File:** `focuscheck/ui/dialogs.py:720-744`

```python
def _waste_hold_start(self, _evt):
    if not self.settings["anti_habit_enabled"]:
        self._on_wasting_clicked(); return
    self._hold_start = time.monotonic()
    try:
        self._info_lbl.config(text="Hold to confirm you're wasting time…")
    except Exception:
        pass

def _waste_hold_end(self, _evt):
    if not self.settings["anti_habit_enabled"]:
        self._on_wasting_clicked(); return
    if self._hold_start is None:
        return
    held_ms = int((time.monotonic() - self._hold_start) * 1000)
    self._hold_start = None
    need = int(self.settings["studying_hold_ms"])
    if held_ms >= need:
        self._on_wasting_clicked()
    else:
        # Inform user to hold longer
        try:
            self._info_lbl.config(text=f"Too quick ({held_ms}ms). Hold for at least {need}ms.")
        except Exception:
            pass
```

#### 3. Fixed button recreation when toggling hide_wasting_button

**File:** `focuscheck/ui/dialogs.py:1444-1450`

When the button is dynamically created/shown:

```python
# Create button and place it
self.btn_waste = tk.Button(self.button_row, text="Wasting time",
                           font=("Segoe UI", 16, "bold"),
                           relief="solid", bd=2, width=14)
# Apply anti-habit to wasting button too
self.btn_waste.bind("<ButtonPress-1>", self._waste_hold_start)
self.btn_waste.bind("<ButtonRelease-1>", self._waste_hold_end)
```

### Behavior

**With anti_habit_enabled = true:**
- User must press and hold "Wasting time" button for 800ms (default)
- Too-quick releases show: "Too quick (XXXms). Hold for at least 800ms."
- While holding shows: "Hold to confirm you're wasting time…"

**With anti_habit_enabled = false:**
- Button works as simple click (backwards compatible)

---

## Issue #2: Cancel Button Closes Everything

### Problem
When the user clicks "Wasting time" and the waste prompt appears, clicking "Cancel" would close both the waste prompt AND the main dialog, forcing the user to wait for the next reminder.

The expected behavior is: Cancel should just close the waste prompt and return to the main dialog so the user can choose again.

### Root Cause
**File:** `focuscheck/ui/dialogs.py:787-790`

The `_on_cancel` callback was calling `self._finish("Wasting time")` which closes the entire PromptDialog.

**Before:**
```python
def _on_cancel():
    # Ensure _finish is called even when dialog is canceled
    self._finish("Wasting time")  # BUG: Closes everything!
```

### Solution Applied

**File:** `focuscheck/ui/dialogs.py:787-790`

```python
def _on_cancel():
    # Cancel just closes the waste prompt, returns to main dialog
    # Don't call _finish() - let user choose again
    pass  # WastePromptDialog.destroy() is already called automatically
```

### Behavior

**Before:**
1. User clicks "Wasting time" → waste prompt appears
2. User clicks "Cancel" → everything closes (main dialog too)
3. User must wait for next reminder

**After:**
1. User clicks "Wasting time" → waste prompt appears
2. User clicks "Cancel" → only waste prompt closes
3. Main dialog remains open → user can click "Studying" or try again

---

## Testing

### Syntax Verification
✅ File compiles without errors:
```bash
python -m py_compile focuscheck/ui/dialogs.py
```

### Manual Testing Needed

1. **Anti-habit on "Wasting time" button:**
   - [ ] Launch app with `anti_habit_enabled: true`
   - [ ] Click and quickly release "Wasting time" → should show "Too quick"
   - [ ] Press and hold "Wasting time" for 800ms → should proceed
   - [ ] Verify message changes to "Hold to confirm you're wasting time…"

2. **Cancel returns to main dialog:**
   - [ ] Enable `wasting_prompt_enabled: true`
   - [ ] Click "Wasting time" button
   - [ ] Click "Cancel" in waste prompt
   - [ ] Verify main dialog is still open
   - [ ] Verify you can click "Studying" or "Wasting time" again

3. **Anti-habit disabled fallback:**
   - [ ] Set `anti_habit_enabled: false`
   - [ ] Click "Wasting time" → should work as simple click

4. **Dynamic button show/hide:**
   - [ ] Toggle `hide_wasting_button` in settings
   - [ ] When shown, verify press-and-hold works

---

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `focuscheck/ui/dialogs.py` | 326-335 | Added event bindings for wasting button |
| `focuscheck/ui/dialogs.py` | 720-744 | Added `_waste_hold_start` and `_waste_hold_end` handlers |
| `focuscheck/ui/dialogs.py` | 787-790 | Fixed cancel callback to not close main dialog |
| `focuscheck/ui/dialogs.py` | 1444-1450 | Fixed button recreation to use bindings |

**Total Changes:** 4 locations in 1 file

---

## Benefits

### User Experience
✅ **Consistent behavior** - Both buttons now use the same anti-habit mechanism
✅ **Prevents accidental clicks** - Press-and-hold reduces mistakes
✅ **Better flow** - Cancel returns to dialog instead of closing everything
✅ **More forgiving** - Users can change their mind without waiting

### Code Quality
✅ **Consistency** - Both buttons use the same pattern
✅ **Maintainability** - Changes applied in all places where button is created
✅ **Backwards compatible** - Respects `anti_habit_enabled` setting

---

## Settings Involved

| Setting | Default | Description |
|---------|---------|-------------|
| `anti_habit_enabled` | `true` | Enable press-and-hold for both buttons |
| `studying_hold_ms` | `800` | Milliseconds to hold (applies to both buttons) |
| `wasting_prompt_enabled` | `false` | Show waste prompt dialog |
| `hide_wasting_button` | `false` | Hide the wasting button entirely |

---

## Conclusion

Both UX issues have been resolved with minimal, focused changes. The fixes improve consistency, reduce user frustration, and maintain backwards compatibility with existing settings.

**Status:** ✅ Ready for testing
