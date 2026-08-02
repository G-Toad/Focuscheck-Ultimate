# Settings UI Verification Checklist

Run `python main.py` and open Settings from the tray menu.

## Window Behavior

- [ ] **Resizable**: Drag corners/edges to resize - should work smoothly
- [ ] **Minimum Size**: Try to make it smaller than 900x650 - should stop
- [ ] **Opens at Good Size**: Window opens at 950x750 by default

## Scrolling (Test in EACH tab)

- [ ] **General Tab**: Mouse wheel scrolls up/down smoothly
- [ ] **Challenges Tab**: Mouse wheel scrolls (long tab with many cards)
- [ ] **Spam Detection Tab**: Mouse wheel scrolls (expandable cards)
- [ ] **Behavior Tab**: Mouse wheel scrolls

## General Tab Controls

### Core Timing (Spinboxes)
- [ ] **Check interval**: [+] and [-] buttons work, can type value
- [ ] **Intensify after**: [+] and [-] buttons work
- [ ] **Overdrive after**: [+] and [-] buttons work
- [ ] **Max intensity level**: [+] and [-] buttons work

### Window Behavior (Toggle Switches)
- [ ] **Always on top**: Toggle switches from gray to green
- [ ] **Center on show**: Toggle works
- [ ] **Follow cursor**: Toggle works
- [ ] **Auto-focus**: Toggle works

### Anti-Habit System
- [ ] **Enable anti-habit**: Toggle works
- [ ] **Randomize buttons**: Toggle works
- [ ] **Hold time**: Spinbox [+]/[-] works

### Pause Behavior
- [ ] **Force always-on**: Toggle works
- [ ] **Pause on idle**: Toggle works
- [ ] **Idle threshold**: Spinbox works
- [ ] **Pause on lock**: Toggle works
- [ ] **Pause on sleep**: Toggle works
- [ ] **Pause on lid**: Toggle works

### System Tray
- [ ] **Start/Stop button**: Toggle works
- [ ] **Settings button**: Toggle works
- [ ] **Exit button**: Toggle works

## Challenges Tab Controls

### Info & Presets
- [ ] **Info Panel**: Blue panel displays at top
- [ ] **Preset Buttons**: All 5 buttons visible (Off, Gentle, Balanced, Aggressive, Maximum)
- [ ] **Off Preset**: Click disables all challenges
- [ ] **Gentle Preset**: Click sets 10%/20% and enables only soft challenges
- [ ] **Balanced Preset**: Click sets 30%/50% and enables most challenges
- [ ] **Aggressive Preset**: Click sets 60%/80% and enables all
- [ ] **Maximum Preset**: Click sets 100%/100% and enables all

### Master Toggle
- [ ] **Enable Challenge System**: Toggle switch works

### Global Settings (Sliders)
- [ ] **Studying frequency**: Slider moves, shows "X%" live
- [ ] **Wasting frequency**: Slider moves, shows "X%" live
- [ ] **Minimum words**: Spinbox [+]/[-] works
- [ ] **Minimum length**: Spinbox [+]/[-] works
- [ ] **Allow skipping**: Toggle works
- [ ] **Show hints**: Toggle works

### Studying Challenges Section
- [ ] **Section Header**: "Studying Challenges" visible with Enable/Disable All buttons
- [ ] **Enable All Button**: Enables all 4 studying challenges
- [ ] **Disable All Button**: Disables all 4 studying challenges

#### Individual Studying Challenge Cards
- [ ] **Learning Specificity Card**:
  - Toggle switch works
  - Description visible
  - Status shows "✓ Active" when ON or "○ Disabled" when OFF
  - Border changes when toggling

- [ ] **Goal Connection Card**: Same checks as above
- [ ] **Will Commitment Card**: Same checks as above
- [ ] **Output Expectation Card**: Same checks as above

### Wasting Challenges Section
- [ ] **Section Header**: "Wasting Time Challenges" visible with buttons
- [ ] **Enable All Button**: Enables all 7 wasting challenges
- [ ] **Disable All Button**: Disables all 7 wasting challenges

#### Individual Wasting Challenge Cards (7 cards)
- [ ] **Wasting Acknowledgment**: Toggle + status works
- [ ] **Should Gap**: Toggle + status works
- [ ] **Because Reasoning**: Toggle + status works
- [ ] **Hour Projection**: Toggle + status works
- [ ] **Tomorrow Regret**: Toggle + status works
- [ ] **Fear Acknowledgment**: Toggle + status works
- [ ] **Lying Confrontation**: Toggle + status works

## Spam Detection Tab Controls

### Info Panel
- [ ] **Warning Panel**: Orange/yellow panel at top

### Master Toggle
- [ ] **Enable spam detection**: Toggle works

### Expandable Cards

#### Gibberish Detection (Expandable)
- [ ] **Header Click**: Expands/collapses (▼/▶ arrow changes)
- [ ] **Enable toggle**: Works when expanded
- [ ] **Min vowel ratio slider**: Drags, shows percentage
- [ ] **Max vowel ratio slider**: Drags, shows percentage
- [ ] **Min unique chars slider**: Drags, shows percentage

#### Repetition Detection (Expandable)
- [ ] **Expands/Collapses**: Click header
- [ ] **Enable toggle**: Works
- [ ] **Max consecutive**: Spinbox works
- [ ] **Max pattern**: Spinbox works

#### Spacing & Keyboard Patterns (Expandable)
- [ ] **Expands/Collapses**: Click header
- [ ] **Spacing toggle**: Works
- [ ] **Min length spinbox**: Works
- [ ] **Keyboard toggle**: Works
- [ ] **Min sequence spinbox**: Works

#### Dictionary Validation (Expandable)
- [ ] **Expands/Collapses**: Click header
- [ ] **Dictionary toggle**: Works
- [ ] **Min word ratio slider**: Shows percentage
- [ ] **Min word length spinbox**: Works

#### Timing Checks (Expandable)
- [ ] **Expands/Collapses**: Click header
- [ ] **Timing toggle**: Works
- [ ] **Min time spinbox**: Works
- [ ] **Flag time spinbox**: Works

## Behavior Tab Controls

### Prompt Settings
- [ ] **Wasting prompt**: Toggle works
- [ ] **Studying prompt**: Toggle works
- [ ] **Require all fields**: Toggle works
- [ ] **Require task**: Toggle works

### UI Options
- [ ] **Hide wasting button**: Toggle works
- [ ] **Task encouragement**: Toggle works
- [ ] **Task analytics**: Toggle works

## Save/Cancel Buttons

- [ ] **Cancel Button**: Closes window without saving
- [ ] **Save Button**: Saves settings and closes window

## After Saving

- [ ] **Settings Persist**: Close and reopen - settings are remembered
- [ ] **All Values Correct**: Numbers, toggles, sliders all show correct values
- [ ] **Challenge Toggles**: Individual challenge on/off states persist

## Common Issues to Check

- [ ] **No Errors**: No error dialogs appear
- [ ] **Smooth Scrolling**: No jerky or laggy scrolling
- [ ] **Toggle Animation**: Switches animate smoothly
- [ ] **Slider Feedback**: Percentage updates as you drag
- [ ] **Spinbox Response**: Clicks respond immediately
- [ ] **Card Status**: Challenge card status updates instantly when toggling
- [ ] **Preset Effect**: Presets change multiple settings at once correctly

## Performance

- [ ] **Opens Quickly**: Settings window appears in < 2 seconds
- [ ] **Responsive**: No lag when interacting with controls
- [ ] **Saves Quickly**: Save completes in < 1 second

---

## If You Find Issues

1. Note which control/tab has the issue
2. Note what you were doing when it happened
3. Check the terminal/console for error messages
4. Report the specific issue

## Expected Behavior

✅ **All toggles**: Click to switch, turn green when ON, gray when OFF
✅ **All sliders**: Drag smoothly, show live percentage
✅ **All spinboxes**: [+]/[-] increment by 1, can type directly
✅ **All cards**: Toggle changes status text and border
✅ **All expandable**: Click header to expand/collapse
✅ **All presets**: One click changes multiple settings
✅ **All tabs**: Scroll smoothly with mouse wheel
✅ **Window**: Resizes smoothly in all directions
