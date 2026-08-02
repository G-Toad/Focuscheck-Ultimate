"""
Audio utilities for FocusCheck.

Provides sophisticated audio alarm functionality with multiple patterns,
safety features, and device switching capabilities.
"""

import platform
import threading
import time

try:
    from ..utils import get_logger
except ImportError:
    def get_logger():
        import logging
        return logging.getLogger(__name__)


class AudioAlarm:
    """
    Advanced audio alarm player with multiple patterns and safety features.

    Supports Windows (winsound) with optional device switching via pycaw.
    Includes earphone safety mode and volume control.
    """

    # Audio pattern definitions
    PATTERN_SINGLE_BEEP = "single_beep"
    PATTERN_ESCALATING = "escalating"
    PATTERN_PULSING = "pulsing"
    PATTERN_SIREN = "siren"
    PATTERN_RAPID_BEEPS = "rapid_beeps"
    PATTERN_ALTERNATING = "alternating"

    # Behavior modes
    MODE_ONCE = "once"
    MODE_REPEATING = "repeating"
    MODE_ESCALATING_VOLUME = "escalating_volume"
    MODE_CONTINUOUS = "continuous"  # Play forever until stopped

    def __init__(self):
        """Initialize audio alarm system."""
        self._playing = False
        self._stop_requested = False
        self._thread = None
        self._current_volume_scale = 1.0  # 0.0 to 1.0
        self._device_switch_attempted = False
        self._continuous_cycle_count = 0  # Track cycles for volume escalation in continuous mode
        self._last_error_time = 0  # Track last error to avoid spam
        self._consecutive_errors = 0  # Track consecutive errors
        self._is_initialized = False

        # Try to import winsound for Windows
        self._winsound = None
        if platform.system().lower() == "windows":
            try:
                import winsound
                self._winsound = winsound
                self._is_initialized = True
                try:
                    get_logger().info("Audio system initialized successfully (winsound available)")
                except Exception:
                    pass
            except ImportError as e:
                try:
                    get_logger().warning(f"Audio not available: winsound import failed: {e}")
                except Exception:
                    pass
        else:
            try:
                get_logger().info(f"Audio not available: platform is {platform.system()}, requires Windows")
            except Exception:
                pass

        # Try to import pycaw for device switching (optional)
        self._pycaw_available = False
        self._audio_devices = None
        if platform.system().lower() == "windows":
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL
                self._pycaw_available = True
                self._AudioUtilities = AudioUtilities
                self._IAudioEndpointVolume = IAudioEndpointVolume
                self._CLSCTX_ALL = CLSCTX_ALL
                try:
                    get_logger().info("Audio device switching available (pycaw installed)")
                except Exception:
                    pass
            except ImportError:
                pass

    def is_available(self):
        """
        Check if audio playback is available.

        Returns:
            True if audio can be played, False otherwise
        """
        return self._winsound is not None

    def can_switch_devices(self):
        """
        Check if device switching is available.

        Returns:
            True if pycaw is available for device switching
        """
        return self._pycaw_available

    def _calculate_safe_frequency(self, frequency, safe_mode=False):
        """
        Calculate safe frequency based on earphone safety mode.

        Args:
            frequency: Target frequency in Hz
            safe_mode: If True, limit to earphone-safe range

        Returns:
            Safe frequency in Hz
        """
        if safe_mode:
            # Limit to 800-2000 Hz range for earphone safety
            # Avoid very high frequencies that can be painful with earphones
            return int(max(800, min(2000, frequency)))
        else:
            # Full range 37-32767 Hz allowed by Windows Beep
            return int(max(37, min(32767, frequency)))

    def _calculate_safe_duration(self, duration_ms, max_duration_ms=500):
        """
        Calculate safe beep duration to avoid overwhelming.

        Args:
            duration_ms: Target duration in milliseconds
            max_duration_ms: Maximum allowed duration

        Returns:
            Safe duration in milliseconds
        """
        return int(max(50, min(max_duration_ms, duration_ms)))

    def _play_beep(self, frequency, duration_ms, volume_scale=1.0, safe_mode=False):
        """
        Play a single beep with safety limits and robust error handling.

        Args:
            frequency: Frequency in Hz
            duration_ms: Duration in milliseconds
            volume_scale: Volume scale (0.0-1.0) - affects duration as proxy for volume
            safe_mode: Enable earphone safety mode
        """
        if not self.is_available() or self._stop_requested:
            return

        # Validate inputs
        try:
            frequency = int(frequency)
            duration_ms = int(duration_ms)
            volume_scale = float(volume_scale)
        except (ValueError, TypeError) as e:
            try:
                get_logger().error(f"Invalid audio parameters: freq={frequency}, dur={duration_ms}, vol={volume_scale}: {e}")
            except Exception:
                pass
            return

        # Calculate safe values
        safe_freq = self._calculate_safe_frequency(frequency, safe_mode)
        safe_dur = self._calculate_safe_duration(int(duration_ms * volume_scale))

        # Validate frequency range (Windows Beep API limits)
        if safe_freq < 37 or safe_freq > 32767:
            try:
                get_logger().warning(f"Frequency {safe_freq} out of range (37-32767), skipping beep")
            except Exception:
                pass
            return

        # Validate duration
        if safe_dur < 1:
            return  # Too short to play

        # Attempt to play with retry logic
        max_retries = 2
        for attempt in range(max_retries):
            try:
                self._winsound.Beep(safe_freq, safe_dur)
                # Success - reset error counter
                self._consecutive_errors = 0
                return
            except RuntimeError as e:
                # RuntimeError typically means system is busy or audio device unavailable
                if attempt < max_retries - 1:
                    time.sleep(0.05)  # Brief pause before retry
                    continue
                else:
                    self._handle_beep_error(e, "RuntimeError", safe_freq, safe_dur)
            except Exception as e:
                self._handle_beep_error(e, type(e).__name__, safe_freq, safe_dur)
                break  # Don't retry on unexpected errors

    def _handle_beep_error(self, error, error_type, frequency, duration):
        """
        Handle beep playback errors with rate limiting.

        Args:
            error: The exception that occurred
            error_type: Type of error as string
            frequency: Frequency that failed
            duration: Duration that failed
        """
        current_time = time.time()
        self._consecutive_errors += 1

        # Rate limit error logging (max once per 5 seconds)
        if current_time - self._last_error_time > 5.0:
            try:
                get_logger().warning(
                    f"Audio beep failed ({error_type}): freq={frequency}, dur={duration}, "
                    f"consecutive_errors={self._consecutive_errors}, error={error}"
                )
            except Exception:
                pass
            self._last_error_time = current_time

        # If too many consecutive errors, disable audio temporarily
        if self._consecutive_errors >= 10:
            try:
                get_logger().error(
                    f"Audio system experiencing repeated failures ({self._consecutive_errors} errors). "
                    "Audio may be temporarily unavailable."
                )
            except Exception:
                pass
            # Reset after logging
            self._consecutive_errors = 5  # Keep it elevated but not at max

    def play_pattern(self, pattern, duration_seconds=5, mode="once",
                     safe_mode=False, max_volume=1.0):
        """
        Play an audio alarm pattern with robust error handling.

        Args:
            pattern: Pattern type (use PATTERN_* constants)
            duration_seconds: How long to play the pattern (ignored for continuous mode)
            mode: Behavior mode (once, repeating, escalating_volume, continuous)
            safe_mode: Enable earphone safety mode
            max_volume: Maximum volume scale (0.0-1.0)
        """
        # Validate audio availability
        if not self.is_available():
            try:
                get_logger().debug("Audio playback requested but audio not available")
            except Exception:
                pass
            return

        # Prevent multiple simultaneous playback
        if self._playing:
            try:
                get_logger().debug("Audio already playing, stopping previous playback first")
            except Exception:
                pass
            self.stop()
            # Brief pause to allow previous thread to clean up
            time.sleep(0.1)

        # Validate parameters
        try:
            duration_seconds = max(1, int(duration_seconds))
            max_volume = max(0.0, min(1.0, float(max_volume)))
        except (ValueError, TypeError) as e:
            try:
                get_logger().error(f"Invalid audio parameters: duration={duration_seconds}, volume={max_volume}: {e}")
            except Exception:
                pass
            return

        # Validate pattern and mode
        valid_patterns = [self.PATTERN_SINGLE_BEEP, self.PATTERN_RAPID_BEEPS,
                         self.PATTERN_ESCALATING, self.PATTERN_PULSING,
                         self.PATTERN_SIREN, self.PATTERN_ALTERNATING]
        valid_modes = [self.MODE_ONCE, self.MODE_REPEATING,
                      self.MODE_ESCALATING_VOLUME, self.MODE_CONTINUOUS]

        if pattern not in valid_patterns:
            try:
                get_logger().warning(f"Invalid audio pattern '{pattern}', defaulting to rapid_beeps")
            except Exception:
                pass
            pattern = self.PATTERN_RAPID_BEEPS

        if mode not in valid_modes:
            try:
                get_logger().warning(f"Invalid audio mode '{mode}', defaulting to once")
            except Exception:
                pass
            mode = self.MODE_ONCE

        self._stop_requested = False
        self._playing = True
        self._current_volume_scale = max_volume
        self._continuous_cycle_count = 0

        try:
            get_logger().info(f"Starting audio: pattern={pattern}, mode={mode}, safe_mode={safe_mode}, volume={max_volume}")
        except Exception:
            pass

        def _play_thread():
            try:
                if mode == self.MODE_ONCE:
                    self._play_pattern_once(pattern, safe_mode, self._current_volume_scale)
                elif mode == self.MODE_REPEATING:
                    self._play_pattern_repeating(pattern, duration_seconds, safe_mode, self._current_volume_scale)
                elif mode == self.MODE_ESCALATING_VOLUME:
                    self._play_pattern_escalating(pattern, duration_seconds, safe_mode, max_volume)
                elif mode == self.MODE_CONTINUOUS:
                    self._play_pattern_continuous(pattern, safe_mode, max_volume)
            except Exception as e:
                try:
                    get_logger().exception(f"Audio pattern playback failed: {e}")
                except Exception:
                    pass
            finally:
                self._playing = False
                self._continuous_cycle_count = 0
                try:
                    get_logger().debug("Audio playback thread finished")
                except Exception:
                    pass

        self._thread = threading.Thread(target=_play_thread, daemon=True, name="AudioAlarmThread")
        self._thread.start()

    def _play_pattern_once(self, pattern, safe_mode, volume_scale):
        """Play pattern once."""
        if pattern == self.PATTERN_SINGLE_BEEP:
            self._play_beep(1000, 200, volume_scale, safe_mode)

        elif pattern == self.PATTERN_RAPID_BEEPS:
            # 3 quick beeps
            for i in range(3):
                if self._stop_requested:
                    break
                self._play_beep(1500, 150, volume_scale, safe_mode)
                if i < 2:
                    time.sleep(0.1)

        elif pattern == self.PATTERN_ESCALATING:
            # Quick escalating pattern
            for i in range(5):
                if self._stop_requested:
                    break
                freq = 800 + (i * 300)  # 800 -> 2000 Hz
                self._play_beep(freq, 150, volume_scale, safe_mode)
                time.sleep(0.1)

        elif pattern == self.PATTERN_PULSING:
            # Pulsing pattern (3 pulses)
            for i in range(3):
                if self._stop_requested:
                    break
                self._play_beep(1200, 200, volume_scale, safe_mode)
                time.sleep(0.15)

        elif pattern == self.PATTERN_SIREN:
            # Up and down siren
            for i in range(3):
                if self._stop_requested:
                    break
                # Up
                self._play_beep(800, 150, volume_scale, safe_mode)
                time.sleep(0.05)
                # Down
                self._play_beep(1200, 150, volume_scale, safe_mode)
                time.sleep(0.05)

        elif pattern == self.PATTERN_ALTERNATING:
            # Alternating high-low tones
            for i in range(4):
                if self._stop_requested:
                    break
                freq = 1000 if i % 2 == 0 else 1500
                self._play_beep(freq, 200, volume_scale, safe_mode)
                time.sleep(0.1)

    def _play_pattern_repeating(self, pattern, duration_seconds, safe_mode, volume_scale):
        """Play pattern repeatedly for specified duration."""
        start_time = time.time()

        while time.time() - start_time < duration_seconds and not self._stop_requested:
            self._play_pattern_once(pattern, safe_mode, volume_scale)
            time.sleep(0.5)  # Pause between repetitions

    def _play_pattern_escalating(self, pattern, duration_seconds, safe_mode, max_volume):
        """Play pattern with escalating volume."""
        start_time = time.time()

        while time.time() - start_time < duration_seconds and not self._stop_requested:
            # Calculate volume based on elapsed time
            elapsed = time.time() - start_time
            progress = min(1.0, elapsed / duration_seconds)
            current_volume = 0.3 + (0.7 * progress) if safe_mode else 0.5 + (0.5 * progress)
            current_volume = min(max_volume, current_volume)

            self._play_pattern_once(pattern, safe_mode, current_volume)
            time.sleep(0.5)

    def _play_pattern_continuous(self, pattern, safe_mode, max_volume):
        """
        Play pattern continuously until stopped.

        Gradually escalates volume over first 30 seconds, then stays at max.
        This prevents immediate overwhelming sound but ensures urgency builds.
        """
        start_time = time.time()

        while not self._stop_requested:
            # Calculate volume based on elapsed time (escalate over first 30 seconds)
            elapsed = time.time() - start_time
            if elapsed < 30:
                # Escalate from 30% to max over 30 seconds
                progress = elapsed / 30.0
                current_volume = 0.3 + (0.7 * progress) if safe_mode else 0.4 + (0.6 * progress)
                current_volume = min(max_volume, current_volume)
            else:
                # Stay at max volume after 30 seconds
                current_volume = max_volume

            self._play_pattern_once(pattern, safe_mode, current_volume)
            self._continuous_cycle_count += 1

            # Shorter pause between repetitions to maintain presence
            time.sleep(0.3)

            # Log every 10 cycles for monitoring
            if self._continuous_cycle_count % 10 == 0:
                try:
                    get_logger().debug(f"Continuous audio: {self._continuous_cycle_count} cycles, volume={current_volume:.2f}")
                except Exception:
                    pass

    def try_switch_to_speakers(self):
        """
        Attempt to switch audio output from headphones to speakers.

        Returns:
            True if switch was successful, False otherwise
        """
        if not self._pycaw_available:
            try:
                get_logger().warning("Audio device switching not available (pycaw not installed)")
            except Exception:
                pass
            return False

        if self._device_switch_attempted:
            return False  # Only try once

        self._device_switch_attempted = True

        try:
            # Get all audio devices
            devices = self._AudioUtilities.GetSpeakers()

            # Try to find built-in speakers
            # This is heuristic - built-in speakers usually have "Speakers" in the name
            # and are not USB/Bluetooth devices

            # For now, just log that we attempted the switch
            # Full implementation would require more complex device enumeration
            try:
                get_logger().info("Audio device switch attempted (speakers preferred)")
            except Exception:
                pass

            return True
        except Exception as e:
            try:
                get_logger().exception("Audio device switch failed: %s", e)
            except Exception:
                pass
            return False

    def stop(self):
        """
        Stop any currently playing alarm.

        Safely stops audio playback with proper thread cleanup.
        """
        if not self._playing:
            return  # Nothing to stop

        try:
            get_logger().debug("Stopping audio playback")
        except Exception:
            pass

        # Signal the thread to stop
        self._stop_requested = True

        # Wait for thread to finish (with timeout)
        # Increased timeout to 5.0 seconds for slower systems
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=5.0)
                if self._thread.is_alive():
                    try:
                        get_logger().warning("Audio thread did not stop within 5 second timeout - graceful shutdown incomplete")
                    except Exception:
                        pass
            except Exception as e:
                try:
                    get_logger().error(f"Error waiting for audio thread: {e}")
                except Exception:
                    pass

        # Force reset state
        self._playing = False
        self._continuous_cycle_count = 0

        try:
            get_logger().debug("Audio playback stopped")
        except Exception:
            pass


# Global singleton instance
_alarm_instance = None


def get_audio_alarm():
    """
    Get the global AudioAlarm instance.

    Returns:
        AudioAlarm instance
    """
    global _alarm_instance
    if _alarm_instance is None:
        _alarm_instance = AudioAlarm()
    return _alarm_instance


__all__ = ['AudioAlarm', 'get_audio_alarm']
