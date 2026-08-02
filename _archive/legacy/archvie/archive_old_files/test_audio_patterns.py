"""
Audio Pattern Test Utility

Test all audio patterns, modes, and configurations to verify the audio alarm system works correctly.
"""

import time
from focuscheck.utils import get_audio_alarm

def test_audio_patterns():
    """Test all available audio patterns."""
    alarm = get_audio_alarm()

    if not alarm.is_available():
        print("[X] Audio not available on this system (requires Windows)")
        return

    print("FocusCheck Audio Pattern Test")
    print("=" * 50)
    print()

    patterns = [
        ("single_beep", "Single Beep"),
        ("rapid_beeps", "Rapid Beeps (3x)"),
        ("escalating", "Escalating Tones"),
        ("pulsing", "Pulsing Pattern"),
        ("siren", "Siren (Up/Down)"),
        ("alternating", "Alternating Tones"),
    ]

    modes = [
        ("once", "Play Once"),
        ("repeating", "Repeating (5 sec)"),
        ("escalating_volume", "Escalating Volume (5 sec)"),
        ("continuous", "Continuous (5 sec demo)"),
    ]

    print("Testing individual patterns in 'once' mode...")
    print()

    for pattern_id, pattern_name in patterns:
        print(f"> {pattern_name}...")
        alarm.play_pattern(
            pattern=pattern_id,
            duration_seconds=5,
            mode="once",
            safe_mode=True,
            max_volume=0.7
        )
        time.sleep(2)  # Wait between patterns
        print()

    print()
    print("Testing behavior modes with 'rapid_beeps' pattern...")
    print()

    for mode_id, mode_name in modes:
        print(f"> {mode_name}...")
        if mode_id == "continuous":
            # For continuous mode, play for 5 seconds then manually stop
            alarm.play_pattern(
                pattern="rapid_beeps",
                duration_seconds=999,  # Ignored for continuous mode
                mode=mode_id,
                safe_mode=True,
                max_volume=0.7
            )
            time.sleep(5)
            alarm.stop()
            print("  (stopped manually after 5 seconds)")
        else:
            alarm.play_pattern(
                pattern="rapid_beeps",
                duration_seconds=5,
                mode=mode_id,
                safe_mode=True,
                max_volume=0.7
            )
            # Wait for pattern to complete
            if mode_id == "once":
                time.sleep(2)
            else:
                time.sleep(6)
        print()

    print()
    print("Testing earphone safety mode...")
    print()

    print("> Earphone Safe Mode ON (limited frequencies)...")
    alarm.play_pattern(
        pattern="siren",
        duration_seconds=3,
        mode="repeating",
        safe_mode=True,
        max_volume=0.5
    )
    time.sleep(4)

    print()
    print("> Earphone Safe Mode OFF (full range)...")
    alarm.play_pattern(
        pattern="siren",
        duration_seconds=3,
        mode="repeating",
        safe_mode=False,
        max_volume=0.5
    )
    time.sleep(4)

    print()
    print("=" * 50)
    print("[OK] Audio pattern testing complete!")
    print()

    # Device switching test
    print("Testing device switching capability...")
    if alarm.can_switch_devices():
        print("[OK] Device switching is available (pycaw installed)")
        print("  Note: Device switching will be tested automatically during overdrive")
    else:
        print("[INFO] Device switching not available (pycaw not installed)")
        print("  Install with: pip install pycaw")
    print()


if __name__ == "__main__":
    try:
        test_audio_patterns()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\n[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()
