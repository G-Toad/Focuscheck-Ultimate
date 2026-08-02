# Settings UI Guide

## How to Access Settings

1. Right-click the FocusCheck system tray icon
2. Click "Settings"
3. The Settings window will open with multiple tabs

## New Tabs Added

### Challenges Tab

Controls the challenge-based reflection system that forces genuine engagement:

```
┌─ Challenge-Based Reflection System ──────────────────┐
│ Forces genuine reflection through hard validation    │
│ constraints.                                         │
├──────────────────────────────────────────────────────┤
│ ☑ Enable challenge system                           │
│                                                      │
│ Studying challenge frequency:  [0.3  ] 0.0-1.0      │
│ Wasting challenge frequency:   [0.5  ] 0.0-1.0      │
│ Minimum words required:        [5    ] words        │
│ Minimum response length:       [20   ] characters   │
│                                                      │
│ ☐ Allow skipping challenges (cancel button)         │
│ ☑ Show example hints for challenges                 │
├──────────────────────────────────────────────────────┤
│ Challenge Types:                                     │
│ Studying: Learning Specificity, Goal Connection,    │
│          Will Commitment, Output Expectation         │
│ Wasting: Acknowledgment, Should Gap, Reasoning,     │
│         Hour Projection, Tomorrow Regret, Fear,      │
│         Lying                                        │
└──────────────────────────────────────────────────────┘
```

**Settings:**
- **Enable challenge system**: Turn the entire system on/off
- **Studying frequency**: Probability of challenge (0.3 = 30% chance)
- **Wasting frequency**: Probability for wasting prompts (0.5 = 50%)
- **Min words**: Minimum word count for responses
- **Min length**: Minimum character count
- **Allow skip**: Let users cancel challenges
- **Show hints**: Display example answers

### Spam Detection Tab

Controls validation rules to prevent gaming the system:

```
┌─ Spam Detection System ──────────────────────────────┐
│ Validates responses to prevent low-effort spam and   │
│ gaming.                                              │
├──────────────────────────────────────────────────────┤
│ ☑ Enable spam detection                             │
│                                                      │
│ Gibberish Detection                                  │
│ ☑ Enable gibberish detection                        │
│ Min vowel ratio:        [0.2  ] 0.0-1.0             │
│ Max vowel ratio:        [0.7  ] 0.0-1.0             │
│ Min unique char ratio:  [0.4  ] 0.0-1.0             │
│                                                      │
│ Repetition Detection                                 │
│ ☑ Enable repetition check                           │
│ Max consecutive chars:  [2    ] count               │
│ Max pattern repetition: [3    ] count               │
│                                                      │
│ Spacing & Keyboard Patterns                          │
│ ☑ Enable spacing check                              │
│ Min length for spaces:  [15   ] characters          │
│ ☑ Enable keyboard pattern check                     │
│ Min keyboard sequence:  [4    ] characters          │
│                                                      │
│ Dictionary Validation                                │
│ ☑ Enable dictionary check                           │
│ Min real word ratio:    [0.6  ] 0.0-1.0             │
│ Min word length:        [2    ] characters          │
│                                                      │
│ Timing Validation                                    │
│ ☑ Enable timing check                               │
│ Min time to submit:     [3    ] seconds             │
│ Flag if submitted under:[2    ] seconds             │
└──────────────────────────────────────────────────────┘
```

**Gibberish Detection:**
- Checks vowel ratios to detect random characters
- Ensures minimum character diversity

**Repetition Detection:**
- Prevents "aaaa" or "asdfasdfasdf" spam
- Limits consecutive identical characters and patterns

**Spacing & Keyboard:**
- Requires spaces in longer responses
- Detects keyboard row patterns (qwerty, asdf, etc.)

**Dictionary Validation:**
- Requires minimum percentage of real words
- Sets minimum word length

**Timing Validation:**
- Prevents instant submissions
- Flags suspiciously fast responses

## Existing Tabs

The following tabs were already present and remain unchanged:

1. **General** - Core timings, intervals, webhook
2. **Tray** - Tray menu button visibility
3. **Anti-Habit** - Button randomization, hold times
4. **Pause** - Pause conditions and behavior
5. **Overdrive** - Intensity and stage settings
6. **Time Info** - Time display options
7. **Tasks** - Task management and prompts

## How Settings Are Saved

1. Modify any settings in any tab
2. Click "Save" button at bottom
3. Settings are validated and clamped to safe ranges
4. Settings are saved to `focus_settings.json`
5. Changes take effect immediately

## Settings File Location

Settings are stored in:
- Windows: `%APPDATA%/FocusCheck/focus_settings.json`
- Others: `~/.config/FocusCheck/focus_settings.json`

## Troubleshooting

**If settings aren't saving:**
1. Check file permissions on the settings directory
2. Look for errors in the application logs
3. Try deleting `focus_settings.json` to reset to defaults

**If challenges aren't appearing:**
1. Go to Challenges tab
2. Ensure "Enable challenge system" is checked
3. Check frequency settings (0.0 = never, 1.0 = always)

**If spam detection is too strict:**
1. Go to Spam Detection tab
2. Disable specific checks that are too aggressive
3. Lower ratio thresholds
4. Reduce minimum requirements
