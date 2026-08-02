# FocusCheck Advanced Audio Alarm System

## Overview

The FocusCheck audio alarm system provides sophisticated audio alerts to help you stay focused when visual reminders aren't enough. With multiple patterns, configurable triggers, safety features, and optional device switching, you can customize the audio experience to match your needs and environment.

---

## Features

### 🎵 **6 Audio Patterns**

1. **Single Beep** - A simple attention-grabbing beep
2. **Rapid Beeps** - 3 quick beeps in succession
3. **Escalating** - Tones that increase in frequency (800 Hz → 2000 Hz)
4. **Pulsing** - Rhythmic pulsing pattern
5. **Siren** - Alternating up/down tones
6. **Alternating** - High-low tone alternation

### 🎭 **4 Behavior Modes**

1. **Once** - Play the pattern once and stop
2. **Repeating** - Continuously repeat the pattern for the configured duration
3. **Escalating Volume** - Start quiet and gradually get louder over time
4. **Continuous** - Play indefinitely until you respond to the prompt ⚠️ *Most persistent*

### 🎯 **4 Trigger Points**

Choose when audio alerts start playing:

1. **Intensification** - After 15 seconds (earliest warning)
2. **Overdrive** - After 60 seconds (missed the minute)
3. **Overdrive Stage 4** - After 72 seconds (ultra-fast flashing)
4. **Overdrive Stage 5** - After 132 seconds (screen dimming)

### 🛡️ **Safety Features**

#### Earphone Safe Mode
- **Enabled by default** for your protection
- Limits frequencies to 800-2000 Hz range (safe for earphones)
- Reduces duration to prevent discomfort
- Recommended max volume: **0.5-0.7** (50-70%)

#### Without Safe Mode
- Full frequency range: 37-32767 Hz
- Longer beep durations allowed
- Recommended max volume: **0.7-1.0** (70-100%)
- ⚠️ Use carefully with earphones!

### 🔊 **Device Switching (Advanced)**

If you're wearing earphones and still not responding, the system can attempt to switch audio output to your laptop's built-in speakers.

**Requirements:**
- Windows only
- Requires `pycaw` library: `pip install pycaw`

**How it works:**
1. Audio plays through current device (earphones)
2. After configured delay (default: 30 seconds), tries to switch to speakers
3. Replays the alarm on speakers
4. Only attempts once per overdrive session

---

## Configuration

### Quick Setup

1. **Enable Audio Alerts**
   - Go to Settings → Alerts tab
   - Toggle "Enable audio alerts" ON

2. **Choose a Pattern**
   - Recommended: `rapid_beeps` (attention-grabbing but not overwhelming)
   - Alternative: `siren` (more urgent)

3. **Set Trigger Point**
   - Recommended: `overdrive` (gives you time to respond visually first)
   - For immediate audio: `intensification`

4. **Configure Behavior**
   - For single alert: `once`
   - For persistent reminder: `repeating`
   - For gradual escalation: `escalating_volume`
   - For maximum persistence: `continuous` ⚠️ *Won't stop until you respond!*

5. **Safety Settings**
   - Keep "Earphone safe mode" ON if using earphones
   - Set max volume to 0.5-0.7 for earphones
   - Set max volume to 0.7-1.0 for speakers

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `audio_alerts_enabled` | `False` | Master toggle for audio alerts |
| `audio_alarm_pattern` | `rapid_beeps` | Which sound pattern to play |
| `audio_alarm_mode` | `once` | How to play the pattern (once/repeating/escalating_volume/continuous) |
| `audio_alarm_trigger` | `overdrive` | When to start playing |
| `audio_alarm_duration_seconds` | `5` | Duration for repeating/escalating modes (ignored for continuous) |
| `audio_earphone_safe_mode` | `True` | Enable earphone safety limits |
| `audio_max_volume` | `0.7` | Maximum volume (0.0-1.0) |
| `audio_try_speaker_switch` | `False` | Attempt device switching |
| `audio_speaker_switch_after_seconds` | `30` | Delay before switching devices |

---

## Usage Scenarios

### Scenario 1: Working with Earphones
**Problem:** You're focused with earphones in and miss visual reminders.

**Solution:**
```
Pattern: rapid_beeps
Mode: once
Trigger: overdrive
Safe Mode: ON
Max Volume: 0.6
Speaker Switch: OFF
```

This gives you a quick audio reminder after you've missed the visual cues, without being too jarring through earphones.

---

### Scenario 2: Prone to Distraction on Phone
**Problem:** You get distracted by your phone and ignore both visual and initial audio reminders.

**Solution:**
```
Pattern: siren
Mode: continuous
Trigger: overdrive
Safe Mode: ON
Max Volume: 0.7
Speaker Switch: ON (after 30 sec)
```

Plays continuously, escalating over first 30 seconds, then maintains max volume until you respond. If still ignored after 30 seconds, switches to laptop speakers to break through phone distraction.

---

### Scenario 3: Deep Focus Sessions
**Problem:** You get into deep flow states and completely miss reminders.

**Solution:**
```
Pattern: escalating
Mode: repeating
Trigger: intensification
Duration: 15 seconds
Safe Mode: ON
Max Volume: 0.5
```

Gentle but persistent escalating tones that start early (intensification) and repeat, gradually breaking through your focus without being disruptive.

---

### Scenario 4: Working Without Earphones
**Problem:** Visual reminders aren't enough; you need immediate audio feedback.

**Solution:**
```
Pattern: pulsing
Mode: once
Trigger: overdrive
Safe Mode: OFF
Max Volume: 0.8
```

Clear, room-filling audio that gets your attention immediately when you miss the minute.

---

## Testing the Audio System

Run the test utility to hear all patterns and modes:

```bash
python test_audio_patterns.py
```

This will play:
- All 6 patterns in "once" mode
- All 3 behavior modes with "rapid_beeps"
- Safe mode comparison (ON vs OFF)
- Device switching capability check

---

## Pattern Characteristics

### Best for Quick Attention
- **rapid_beeps** - Quick, attention-grabbing, not overwhelming
- **single_beep** - Minimal, subtle reminder

### Best for Persistent Reminder
- **pulsing** - Rhythmic, easy to recognize, not annoying
- **alternating** - Distinctive pattern

### Best for Escalation
- **escalating** - Builds urgency naturally
- **siren** - Clear urgency signal

### Best for Continuous Mode
- **pulsing** - Rhythmic and recognizable without being grating
- **siren** - Creates sense of urgency
- **rapid_beeps** - Clear but not overwhelming over time
- ❌ **Avoid single_beep** - Too sparse for continuous mode

---

## Safety Guidelines

### ✅ Safe Practices
- Always enable "Earphone safe mode" when using earphones
- Start with max volume at 0.5-0.6 and adjust up if needed
- Use "once" mode initially to test volume levels
- Take breaks if audio becomes uncomfortable

### ⚠️ Warnings
- High frequencies at high volume through earphones can cause hearing damage
- Never exceed volume 0.8 with earphones
- If you experience discomfort, reduce volume immediately
- Consider using speakers instead of earphones for higher volumes

---

## Troubleshooting

### No Sound Playing
1. Check that "Enable audio alerts" is ON in settings
2. Verify Windows system volume is not muted
3. Ensure you've reached the configured trigger point
4. Check if audio is playing through correct device

### Sound is Too Quiet
1. Increase `audio_max_volume` setting
2. Check Windows system volume
3. Verify earphone safe mode isn't limiting you too much
4. Try disabling safe mode (carefully!) for speakers

### Sound is Too Loud/Jarring
1. Enable earphone safe mode
2. Reduce `audio_max_volume` to 0.5 or lower
3. Switch to gentler pattern (single_beep, pulsing)
4. Use "once" mode instead of "repeating"

### Device Switching Not Working
1. Install pycaw: `pip install pycaw`
2. Verify you're on Windows
3. Check that both devices (earphones + speakers) are connected
4. Enable `audio_try_speaker_switch` in settings

---

## Advanced Configuration

### Custom Timing
Adjust when each stage triggers by modifying these settings:
- `intensify_after_seconds` (default: 15)
- `overdrive_after_seconds` (default: 60)
- `overdrive_stage4_after_seconds` (default: 12 after overdrive)
- `overdrive_stage5_after_seconds` (default: 60 after stage 4)

### Multiple Alerts
The system triggers audio based on your chosen trigger point. If you want audio at multiple stages, the most effective approach is:
1. Set trigger to earliest desired point (e.g., `intensification`)
2. Use `escalating_volume` mode with longer duration
3. This creates progressive escalation throughout

---

## Technical Details

### Audio Implementation
- Uses Windows `winsound.Beep()` API
- Runs in background thread (non-blocking)
- Frequency range: 800-2000 Hz (safe mode) or 37-32767 Hz (full range)
- Duration range: 50-500 ms per beep
- Volume control via duration modulation (winsound limitation)

### Device Switching
- Uses `pycaw` library for audio device enumeration
- Attempts to identify built-in speakers vs external devices
- Single attempt per overdrive session
- Fallback: continues on current device if switch fails

---

## FAQ

**Q: Why isn't audio working?**
A: Audio requires Windows OS and is disabled by default. Enable it in Settings → Alerts tab.

**Q: Can I use custom sound files (MP3, WAV)?**
A: Not currently. The system uses programmatic beeps for reliability and low overhead.

**Q: Will audio alerts wake my computer from sleep?**
A: No. The system pauses when your computer is asleep or locked.

**Q: Can I have different patterns for different trigger points?**
A: Not currently. You choose one pattern that plays at your selected trigger point.

**Q: How long does continuous mode play?**
A: Continuous mode plays indefinitely until you respond to the prompt. It escalates volume over the first 30 seconds, then maintains max volume.

**Q: Will continuous mode drain my battery or hurt my computer?**
A: No. The audio system is lightweight and uses minimal CPU. It's designed to run safely in the background.

**Q: Is device switching reliable?**
A: It's experimental. Windows audio routing is complex. It works best with simple setups (built-in speakers + one external device).

---

## Support

If you encounter issues:
1. Run `python test_audio_patterns.py` to verify basic functionality
2. Check logs in `focuscheck_data/focus_check.log`
3. Report issues with audio device details and system info

---

## Future Enhancements

Potential future additions:
- Custom sound file support
- Multiple trigger points with different patterns
- Volume ramping within a single playback
- Cross-platform audio support (Mac, Linux)
- Spatial audio / panning effects
- Integration with smart home speakers (Google Home, Alexa)

---

**Version:** 2.0
**Last Updated:** 2025-01-22
**Compatibility:** Windows 10/11, Python 3.8+
