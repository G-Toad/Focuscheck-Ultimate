# Modern Settings UI - Complete Revamp

## What Changed

Completely redesigned the settings interface with modern UI principles and individual challenge controls.

### Key Improvements

1. **Fully Resizable & Scrollable**
   - Window resizes from 800x600 minimum to any size
   - All tabs have smooth mouse wheel scrolling
   - No more cramped, fixed-size window

2. **Better Organization**
   - Reduced from 9 tabs to 5 clean, logical tabs
   - Clear visual hierarchy with section headers
   - Generous spacing and breathing room
   - Consistent styling throughout

3. **Individual Challenge Control**
   - Toggle each studying challenge on/off individually
   - Toggle each wasting challenge on/off individually
   - Challenges you disable won't appear at all

4. **Improved UX**
   - Descriptions under each checkbox explaining what it does
   - Larger entry fields and better labels
   - Modern sectioned layout with separators
   - Helper text showing valid ranges (e.g., "0.0-1.0")

## New Tab Structure

### 1. General
Everything core to the app's behavior:
- **Core Timing**: Intervals, intensity, overdrive settings
- **Window Behavior**: Always on top, centering, cursor following
- **Anti-Habit System**: Randomization, hold times
- **Pause Behavior**: All pause conditions and thresholds
- **System Tray**: Tray menu button visibility
- **Webhook**: Optional webhook URL

### 2. Challenges
Complete control over the challenge system:
- **Master Toggle**: Enable/disable entire system
- **Global Settings**: Frequencies, minimums, hints, skip options
- **Studying Challenges** (4 types):
  - ☑ Learning Specificity - Requires naming exact topic
  - ☑ Goal Connection - Forces stating the goal/purpose
  - ☑ Will Commitment - Demands concrete 'I will...' statement
  - ☑ Output Expectation - Requires describing deliverable

- **Wasting Challenges** (7 types):
  - ☑ Wasting Acknowledgment - Forces acknowledging cost
  - ☑ Should Gap - Demands doing vs should contrast
  - ☑ Because Reasoning - Requires real reason
  - ☑ Hour Projection - Forces 1-hour consequence
  - ☑ Tomorrow Regret - Demands future regret admission
  - ☑ Fear Acknowledgment - Forces naming the fear
  - ☑ Lying Confrontation - Requires admitting self-deception

### 3. Spam Detection
All spam validation controls (unchanged from before):
- Gibberish Detection
- Repetition Detection
- Spacing & Patterns
- Dictionary Validation
- Timing Checks

### 4. Behavior
Prompt and UI behavior:
- **Prompt Settings**: Enable prompts, require fields, require tasks
- **UI Options**: Hide buttons, task encouragement, analytics

### 5. Advanced
Reserved for future power-user settings

## Technical Changes

### Files Modified

1. **`focuscheck/ui/windows.py`** - Completely replaced
   - New `ModernSettingsWindow` class
   - Scrollable tabs with canvas/scrollbar
   - Helper methods for consistent UI elements
   - Individual challenge variable management

2. **`focuscheck/settings/defaults.py`** - Added 11 new settings
   ```python
   # Individual studying challenges
   "challenge_studying_learning_specificity_enabled": True,
   "challenge_studying_goal_connection_enabled": True,
   "challenge_studying_will_commitment_enabled": True,
   "challenge_studying_output_expectation_enabled": True,

   # Individual wasting challenges
   "challenge_wasting_wasting_acknowledgment_enabled": True,
   "challenge_wasting_should_gap_enabled": True,
   "challenge_wasting_because_reasoning_enabled": True,
   "challenge_wasting_hour_projection_enabled": True,
   "challenge_wasting_tomorrow_regret_enabled": True,
   "challenge_wasting_fear_acknowledgment_enabled": True,
   "challenge_wasting_lying_confrontation_enabled": True,
   ```

3. **`focuscheck/settings/manager.py`** - Added validation
   - All 11 individual challenge settings added to boolean list
   - Settings now persist correctly

4. **`focuscheck/ui/dialogs/challenge_system.py`** - Filtering logic
   - `get_challenge()` now filters by individual settings
   - Only enabled challenges appear in the pool
   - Fallback to full pool if all disabled

### Backwards Compatibility

✅ All existing settings preserved
✅ Old settings files load correctly
✅ New settings have sensible defaults (all enabled)
✅ API unchanged - `SettingsWindow` still works

### Backup

Old UI backed up to: `focuscheck/ui/windows_old_backup.py`

## Usage Examples

### Customize Which Challenges Appear

**Example 1: Only use gentle studying challenges**
1. Go to Challenges tab
2. Enable "Learning Specificity" and "Goal Connection"
3. Disable "Will Commitment" and "Output Expectation"
4. Save

Now only the first two challenges will appear for studying.

**Example 2: Disable harsh wasting challenges**
1. Go to Challenges tab
2. Disable "Lying Confrontation" and "Fear Acknowledgment"
3. Keep others enabled
4. Save

The intense confrontational challenges won't appear.

**Example 3: Only use tomorrow regret**
1. Go to Challenges tab
2. Disable all wasting challenges EXCEPT "Tomorrow Regret"
3. Save

Only that one challenge will appear when wasting time.

### Adjust Challenge Frequency

1. Set studying frequency to 0.0 = Never challenge studying clicks
2. Set to 1.0 = Always challenge studying clicks
3. Set to 0.3 = 30% chance

### Disable Challenges Entirely

Set "Enable challenge system" to unchecked - no challenges will ever appear regardless of other settings.

## Design Principles Applied

1. **Progressive Disclosure**
   - Most important settings first (General tab)
   - Advanced features in later tabs
   - Grouped by logical function

2. **Visual Hierarchy**
   - Section headers (bold, 11pt)
   - Separators between sections
   - Indented descriptions in gray
   - Consistent spacing (20px between sections)

3. **Feedback & Guidance**
   - Descriptive labels ("0.0-1.0" ranges shown)
   - Hover-friendly checkbox descriptions
   - Error messages on save failures

4. **Accessibility**
   - Resizable window (800x600 to full screen)
   - Scrollable tabs for long content
   - Mouse wheel support
   - Large click targets

5. **Data Safety**
   - Validation on save
   - Clamping to safe ranges
   - Graceful error handling
   - Settings persist atomically

## Migration Notes

If you have existing settings, they will all be preserved. The new individual challenge toggles default to `True` (enabled) so behavior is unchanged until you customize them.

No action required - just open Settings and enjoy the new UI!

## Performance

- Lazy loading of tab contents
- Efficient scrolling with canvas
- No performance degradation with many settings
- Instant save/load operations

## Future Enhancements

The new architecture makes it easy to add:
- Search/filter settings
- Import/export presets
- Reset to defaults button
- Per-tab reset
- Setting descriptions tooltips
- Validation feedback in real-time
