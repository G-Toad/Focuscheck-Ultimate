# Continuous Audio Mode Feature

## What's New

Added **Continuous Mode** to the audio alarm system - the most persistent audio option that plays indefinitely until you respond to the prompt.

---

## How It Works

### Standard Modes (Limited Duration)
- **Once**: Play pattern once, then stop
- **Repeating**: Play pattern repeatedly for X seconds, then stop
- **Escalating Volume**: Play pattern with increasing volume for X seconds, then stop

### ✨ NEW: Continuous Mode (Unlimited Duration)
- **Continuous**: Plays pattern **forever** until you respond
  - Escalates volume over first 30 seconds (30% → max)
  - Maintains max volume after 30 seconds
  - Automatically stops when you close the dialog
  - **Won't stop no matter how long you ignore it!**

---

## When to Use Continuous Mode

### ✅ Perfect For:
1. **Phone Distractions** - When you get lost scrolling and ignore everything
2. **Deep Work** - When you're so focused you tune out all reminders
3. **Stubborn Procrastination** - When you keep ignoring prompts
4. **Working from Home** - When ambient noise might drown out a single beep

### ⚠️ Warning Signs You Need It:
- You frequently realize 10+ minutes later that you ignored a prompt
- You catch yourself consciously ignoring the visual reminders
- Other modes aren't persistent enough to break your distraction

---

## Configuration

### In Settings (Alerts Tab → Audio Alerts):

**Recommended for Continuous Mode:**
```
Enable Audio Alerts: ON
Pattern: siren or pulsing
Mode: continuous  ← NEW!
Trigger: overdrive
Safe Mode: ON (if using earphones)
Max Volume: 0.6-0.7
```

### Why These Choices?

- **Siren/Pulsing**: Recognizable patterns that don't become grating over time
- **Continuous Mode**: Won't stop until you respond
- **Overdrive Trigger**: Gives you 60 seconds to respond visually first
- **Safe Mode ON**: Protects your ears during long playback
- **Volume 0.6-0.7**: Persistent but not painful

---

## How Continuous Mode Escalates

```
Seconds 0-30: Volume gradually increases (30% → 70%)
Seconds 30+:  Stays at 70% indefinitely
```

This prevents sudden loud noise but ensures it becomes impossible to ignore.

---

## Technical Details

### Stopping Behavior
Continuous mode stops automatically when:
- ✅ You click "Study" or "Wasting time"
- ✅ You close the dialog (any way)
- ✅ The application closes

It **does NOT** stop when:
- ❌ You switch windows
- ❌ You minimize the prompt
- ❌ Timer expires (there's no timer!)
- ❌ You lock your computer (it'll resume when you unlock)

### Resource Usage
- Runs in background thread (non-blocking)
- Minimal CPU usage (<0.1%)
- Minimal memory footprint
- Safe to run indefinitely

### Logging
Every 10 cycles (approximately every 3-5 seconds), the system logs:
- Cycle count
- Current volume level
- This helps debug if needed

---

## Comparison with Other Modes

| Mode | Duration | Volume | Stops After | Best For |
|------|----------|--------|-------------|----------|
| **Once** | 1-2 seconds | Fixed | 1 playback | Quick reminder |
| **Repeating** | X seconds | Fixed | Duration expires | Persistent reminder |
| **Escalating** | X seconds | Increasing | Duration expires | Building urgency |
| **Continuous** | ∞ | Escalates then fixed | You respond | Maximum persistence |

---

## Safety with Continuous Mode

### Earphone Safety
✅ **Safe Mode is CRITICAL for continuous mode**
- Limits to 800-2000 Hz (comfortable range)
- Reduces beep duration
- Caps at configured max volume

❌ **Disabling safe mode with earphones is DANGEROUS**
- Full frequency range can be painful over time
- Not recommended for continuous use

### Recommended Settings
```
With Earphones:
  Safe Mode: ON
  Max Volume: 50-60%

With Speakers:
  Safe Mode: ON or OFF (your choice)
  Max Volume: 70-100%
```

---

## Testing Continuous Mode

### Quick Test
```bash
python test_audio_patterns.py
```
Look for: "Continuous (5 sec demo)" - plays for 5 seconds then auto-stops

### Live Test
1. Enable audio alerts in Settings
2. Set mode to "continuous"
3. Choose your pattern
4. Wait for next prompt
5. **Deliberately ignore it**
6. Watch it escalate and continue indefinitely
7. Respond when ready - it stops immediately

---

## Troubleshooting

**Q: It stopped after a few seconds!**
A: Check that mode is set to "continuous", not "repeating" or "escalating_volume"

**Q: It's too loud even at 50% volume!**
A: Ensure safe mode is ON. If still too loud, reduce to 40%

**Q: It's not loud enough!**
A: Try increasing max volume, or disable safe mode (speakers only!)

**Q: It kept playing after I closed the dialog!**
A: This is a bug - please report it. Should auto-stop on dialog close.

**Q: Can I make it louder over time indefinitely?**
A: No. It escalates for 30 seconds then stays at max. This prevents hearing damage.

---

## Real-World Examples

### Example 1: Phone Scrolling
```
Scenario: You're scrolling Instagram and ignoring your laptop
Setup:
  - Mode: continuous
  - Pattern: siren
  - Trigger: overdrive
  - Safe Mode: ON
  - Max Volume: 70%
  - Speaker Switch: ON (after 30 sec)

Result:
  - Minute 1: Siren starts quietly after you miss the visual prompt
  - Minute 1-1.5: Siren gets progressively louder
  - Minute 1.5+: Siren maintains max volume
  - Minute 2: Switches to laptop speakers (if earphones connected)
  - You WILL notice and respond!
```

### Example 2: Deep Code Flow
```
Scenario: You're debugging and in deep flow state
Setup:
  - Mode: continuous
  - Pattern: pulsing
  - Trigger: intensification (earlier!)
  - Safe Mode: ON
  - Max Volume: 50%

Result:
  - Gentle pulsing starts at 15 seconds
  - Gradually increases to comfortable level
  - Continues indefinitely until you acknowledge
  - Not jarring, but impossible to ignore long-term
```

---

## Future Enhancements

Possible improvements to continuous mode:
- [ ] Variable escalation duration (currently fixed at 30 seconds)
- [ ] Periodic volume pulses after reaching max (keeps it noticeable)
- [ ] Pattern switching (start with pulsing, switch to siren after 2 minutes)
- [ ] Integration with system events (louder when headphones detected)

---

## Summary

**Continuous Mode** is the nuclear option for audio alerts:
- ✅ Plays indefinitely until you respond
- ✅ Escalates over 30 seconds then maintains
- ✅ Auto-stops when dialog closes
- ✅ Safe for extended use (with safe mode ON)
- ⚠️ Most persistent option - use responsibly!

**When other modes aren't enough, continuous mode ensures you WILL respond.**

---

**Added:** 2025-01-22
**Version:** 2.1
**Requires:** FocusCheck with advanced audio system
