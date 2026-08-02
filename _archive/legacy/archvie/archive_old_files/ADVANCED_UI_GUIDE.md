# Advanced Settings UI - Complete Guide

## What's New

Completely redesigned settings interface with modern, intuitive visual controls replacing the checkbox-heavy old design.

## New Visual Controls

### 1. Toggle Switches (Instead of Checkboxes)
iOS-style toggle switches for all enable/disable settings.

**Visual:**
```
 ⚪ ← Off          ⚪ ← On (green)
━━━━━━━           ━━━━━━━

Easier to see at a glance whether something is on or off.
```

**Benefits:**
- Immediately obvious what's on/off
- Satisfying to use
- Color-coded (green = on, gray = off)
- Modern, professional look

### 2. Sliders with Live Feedback
Interactive sliders for frequency and ratio settings showing live percentage.

**Example:**
```
Studying frequency: |━━━━━━━●━━━━━━━━━━| 30%

Drag to adjust, see immediate feedback
```

**Benefits:**
- Visual representation of values
- See exactly what percentage you're setting
- Easier than typing decimal numbers
- Intuitive adjustment

### 3. Spinboxes with +/- Buttons
Number inputs with increment/decrement buttons for precise control.

**Example:**
```
Check interval:  [ - ] [  60  ] [ + ]  seconds
```

**Benefits:**
- No typing needed
- One-click adjustments
- Can't enter invalid values
- Clear visual feedback

### 4. Challenge Cards
Beautiful cards for each challenge with toggle, description, and live status.

**Visual:**
```
┌─────────────────────────────────────────┐
│ ⚪ Learning Specificity                 │
│                                         │
│ Requires naming the exact topic being  │
│ learned (e.g., 'learning calculus')    │
│                                         │
│ ✓ Active - will appear randomly        │
└─────────────────────────────────────────┘
```

**Features:**
- Toggle switch at top
- Full description of what it does
- Live status indicator
- Color-coded border (green=active, gray=disabled)

### 5. Expandable Cards
Collapsible sections to reduce clutter.

**Example:**
```
▼ Gibberish Detection ───────────────────
  ⚪ Enable gibberish check
  Min vowel ratio: |━━●━━━━━━━━| 20%
  Max vowel ratio: |━━━━━━━●━━| 70%

▶ Repetition Detection ──────────────────
  (collapsed - click to expand)
```

**Benefits:**
- Hide complexity until needed
- Clean, organized interface
- Easy to scan

### 6. Info Panels
Color-coded informational banners.

**Types:**
- 🔵 **Info** - Blue background, general information
- 🟡 **Warning** - Orange background, important notices
- 🟢 **Success** - Green background, confirmations
- 🟣 **Tip** - Purple background, helpful hints

### 7. Preset Buttons
One-click configuration presets.

**Available Presets:**
```
[  Off  ] [ Gentle ] [ Balanced ] [ Aggressive ] [ Maximum ]
```

**What They Do:**
- **Off**: Disables all challenges
- **Gentle**: 10% studying, 20% wasting, soft challenges only
- **Balanced**: 30% studying, 50% wasting, most challenges (default)
- **Aggressive**: 60% studying, 80% wasting, all challenges
- **Maximum**: 100% studying, 100% wasting, all challenges

### 8. Section Headers with Actions
Headers with quick-action buttons.

**Example:**
```
Studying Challenges ──────── [Enable All] [Disable All]
```

## Tab Organization

### General Tab
Core application settings with info panel at top.

**Sections:**
- Core Timing (spinboxes)
- Window Behavior (toggles with descriptions)
- Anti-Habit System (toggles + spinbox)
- Pause Behavior (toggles + spinbox)
- System Tray (toggles)

### Challenges Tab
Complete challenge control with modern UX.

**Features:**
- Info panel explaining challenges
- Preset buttons for quick config
- Master toggle switch
- Sliders for frequencies (with % display)
- Spinboxes for minimums
- Individual challenge cards with:
  - Toggle switch
  - Full description
  - Live status indicator
- Enable/Disable All buttons per section

### Spam Detection Tab
All spam validation controls in expandable cards.

**Sections (all expandable):**
- Gibberish Detection (sliders for ratios)
- Repetition Detection (spinboxes)
- Spacing & Keyboard Patterns (mixed controls)
- Dictionary Validation (slider + spinbox)
- Timing Checks (spinboxes)

### Behavior Tab
Prompt and UI settings with toggle switches.

**Sections:**
- Prompt Settings
- UI Options

## Feature Comparison

| Control Type | Old UI | New UI |
|--------------|--------|--------|
| **Enable/Disable** | ☐ Checkbox | ⚪ Toggle Switch |
| **Frequencies (0.0-1.0)** | Text entry "0.3" | Slider ━━━●━ 30% |
| **Numbers** | Text entry "60" | Spinbox [-][60][+] |
| **Challenges** | Simple checkbox list | Rich cards with description |
| **Spam sections** | All visible, crowded | Expandable cards |
| **Presets** | None | One-click buttons |
| **Visual feedback** | None | Live status, colors, icons |
| **Descriptions** | None | Inline help text |

## Usage Examples

### Example 1: Set Gentle Challenges
1. Open Settings → Challenges tab
2. Click **"Gentle"** preset button
3. Done! Automatically sets:
   - Challenge system: ON
   - Studying freq: 10%
   - Wasting freq: 20%
   - Enables only: Learning Specificity, Goal Connection, Should Gap, Tomorrow Regret

### Example 2: Custom Frequency
1. Go to Challenges tab
2. Drag "Studying frequency" slider to 50%
3. See live update: "50%"
4. Drag "Wasting frequency" slider to 75%
5. See live update: "75%"
6. Click Save

### Example 3: Disable One Challenge
1. Go to Challenges tab
2. Scroll to "Lying Confrontation" card
3. Click toggle switch (turns gray)
4. See status change to "○ Disabled - will never appear"
5. Click Save

### Example 4: Adjust Timing with Spinbox
1. Go to General tab
2. Find "Check interval"
3. Click [+] button repeatedly to increase
4. Or click [-] to decrease
5. See value update instantly

### Example 5: Explore Spam Settings
1. Go to Spam Detection tab
2. Click "▶ Gibberish Detection" to expand
3. See all gibberish settings
4. Adjust sliders for min/max vowel ratios
5. Click header again to collapse

## Visual Hierarchy

The new UI follows clear visual hierarchy:

```
Tab Level
├─ Info Panel (what this tab does)
├─ Preset Buttons (if applicable)
├─ Section Header (bold, blue, with separator)
│  ├─ Action Buttons (right-aligned)
│  ├─ Control 1 (toggle/slider/spinbox)
│  ├─ Control 2
│  └─ Control 3
├─ Section Header 2
│  └─ ...
└─ Save/Cancel Buttons (bottom right)
```

## Color Coding

- **Green**: Active/Enabled
- **Gray**: Inactive/Disabled
- **Blue**: Section headers, info panels
- **Orange**: Warnings
- **Purple**: Tips
- **Red**: Errors (if any)

## Keyboard Navigation

All controls support standard keyboard navigation:
- **Tab**: Move between controls
- **Space/Enter**: Toggle switches and buttons
- **Arrow keys**: Adjust sliders and spinboxes
- **Mouse wheel**: Scroll in tabs

## Accessibility Features

- **Large click targets**: All toggles and buttons are easy to hit
- **Clear labels**: Every control has a descriptive label
- **Inline help**: Descriptions explain what each setting does
- **Visual feedback**: Immediate response to all interactions
- **Organized sections**: Related settings grouped logically
- **Collapsible sections**: Hide complexity when not needed

## Technical Details

### Custom Widgets

All new widgets are in `focuscheck/ui/modern_widgets.py`:

1. **ToggleSwitch** - iOS-style toggle
   - Canvas-based custom widget
   - Animated transition
   - Color-coded states

2. **LabeledSlider** - Slider with value display
   - Auto-converts 0.0-1.0 to percentage
   - Live value updates
   - Configurable range

3. **SpinboxWithButtons** - Enhanced spinbox
   - +/- buttons for easier adjustment
   - Prevents invalid input
   - Supports any range

4. **ChallengeCard** - Rich challenge display
   - Toggle + title + description
   - Live status indicator
   - Color-coded border

5. **ExpandableCard** - Collapsible panel
   - Click header to expand/collapse
   - Smooth animation
   - Saves screen space

6. **PresetButton** - Quick configuration
   - Applies preset config
   - One-click operation
   - Multiple presets supported

7. **SectionHeader** - Visual section divider
   - Bold title with separator
   - Optional action buttons
   - Clear hierarchy

8. **InfoPanel** - Informational banner
   - Color-coded by type
   - Icon + text
   - Wrapping text support

### Responsive Design

- Window resizes from 900x650 to any size
- All controls scale appropriately
- Scrolling works smoothly
- Mouse wheel supported throughout

## Migration from Old UI

No action required! All your existing settings are automatically:
- Loaded correctly
- Displayed in new controls
- Saved when you click Save

The old UI is backed up to:
- `windows_old_backup.py` - Original cramped version
- `windows_modern_backup.py` - First modern version with basic controls

## Tips for Best Experience

1. **Use Presets First**: Start with a preset, then customize
2. **Expand Only What You Need**: Keep unused sections collapsed
3. **Try the Sliders**: Much easier than typing decimals
4. **Read Descriptions**: Inline help explains everything
5. **Use Enable/Disable All**: Quick bulk operations
6. **Watch Live Status**: Challenge cards show immediate feedback

## Known Limitations

- Preset buttons don't have tooltips yet (coming soon)
- Can't reorder challenges by dragging (coming soon)
- No search/filter yet (coming soon)
- No import/export presets yet (coming soon)

## Future Enhancements

Planned improvements:
- Drag-to-reorder challenges
- Custom preset saving
- Settings search/filter
- Tooltips on hover
- Real-time validation feedback
- Reset individual sections
- Keyboard shortcuts
- Dark mode support

##Conclusion

The new advanced UI provides:
- ✅ Better visual feedback
- ✅ Easier interaction
- ✅ More intuitive controls
- ✅ Professional appearance
- ✅ Organized information
- ✅ Quick presets
- ✅ Individual challenge control
- ✅ Modern user experience

Enjoy your new, user-friendly settings interface! 🎉
