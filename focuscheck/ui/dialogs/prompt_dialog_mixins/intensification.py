"""
Intensification mixin for PromptDialog.

Contains methods for escalating visual and behavioral intensity,
including overdrive stages, screen dimming, and various visual effects.
"""

import time
import random
import platform
import ctypes
from ctypes import wintypes

from ..intensification_helpers import lift_all_child_windows, _configure_window_position_api
import tkinter as tk

try:
    from ....utils import get_logger, log_exception, get_audio_alarm
except ImportError:
    def get_logger():
        import logging
        return logging.getLogger(__name__)
    def log_exception(msg):
        pass
    def get_audio_alarm():
        class DummyAlarm:
            def is_available(self): return False
            def play_escalating_alarm(self, *args, **kwargs): pass
            def play_attention_beep(self): pass
            def play_urgent_alarm(self): pass
            def stop(self): pass
        return DummyAlarm()


def _configure_gamma_api(user32, gdi32):
    """Declare device-context and gamma-ramp signatures."""
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    gdi32.GetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
    gdi32.GetDeviceGammaRamp.restype = wintypes.BOOL
    gdi32.SetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
    gdi32.SetDeviceGammaRamp.restype = wintypes.BOOL


def _configure_magnification_api(magnification):
    """Declare the fullscreen magnification lifecycle signatures."""
    magnification.MagInitialize.argtypes = []
    magnification.MagInitialize.restype = wintypes.BOOL
    magnification.MagUninitialize.argtypes = []
    magnification.MagUninitialize.restype = wintypes.BOOL
    magnification.MagSetFullscreenColorEffect.argtypes = [ctypes.c_void_p]
    magnification.MagSetFullscreenColorEffect.restype = wintypes.BOOL


class IntensificationMixin:
    """Mixin for intensification and overdrive functionality in PromptDialog."""

    def _lift_all_child_windows(self):
        return lift_all_child_windows(self)

    def _begin_intensify(self):
        """
        Begin the intensification sequence.

        Called after the initial delay to start escalating visual effects.
        """
        if self._closed: return
        try: self.lift(); self.focus_force()
        except Exception: pass
        # Nudge the taskbar to flash for attention (Windows)
        try: self._flash_taskbar_begin()
        except Exception: pass
        # Play audio alert if configured for intensification trigger
        try:
            if self.settings.get("audio_alerts_enabled", False):
                if self.settings.get("audio_alarm_trigger", "overdrive") == "intensification":
                    self._play_audio_alarm()
        except Exception:
            pass
        self._step_intensity()

    def _step_intensity(self):
        """
        Step intensity level up and apply corresponding effects.

        Progressively enables pulse and shake effects as intensity increases.
        """
        if self._closed: return
        if self.intensity_level < self.settings["max_intensity_level"]:
            self.intensity_level += 1
        if self.intensity_level >= 1 and self.settings.get("enable_intensity_pulse", True):
            self._pulse_buttons()
        if (self.intensity_level >= 2 and not self._shaking and
            self.settings.get("enable_intensity_shake", True) and not self.settings.get("disable_jiggling", False)):
            self._shaking = True
            self._shake_window(times=12, pixels=10, delay=18)
        if self.intensity_level < self.settings["max_intensity_level"]:
            self._schedule_timer(1800, self._step_intensity)

    def _begin_overdrive(self):
        """
        Begin overdrive mode after deadline is missed.

        Applies aggressive visual effects and schedules further escalation stages.
        """
        if self._closed: return
        self._overdrive = True
        self._overdrive_start_time = getattr(self, "_monotonic_now", time.monotonic)()  # Track when overdrive started
        try: self._flash_taskbar_begin()
        except Exception: pass
        # Play audio alert if configured for overdrive trigger
        try:
            if self.settings.get("audio_alerts_enabled", False):
                if self.settings.get("audio_alarm_trigger", "overdrive") == "overdrive":
                    self._play_audio_alarm()
        except Exception:
            pass
        if self.settings.get("enable_overdrive_flash_background", True):
            self._flash_background()
        if self.settings.get("enable_overdrive_shake_loop", True) and not self.settings.get("disable_jiggling", False):
            self._shake_loop(amplitude=18, delay=14)
        if self.settings.get("enable_overdrive_jiggle_buttons", True) and not self.settings.get("disable_jiggling", False):
            self._jiggle_buttons()
        self._info_lbl.config(text="You missed the minute-decide now. (Logged as late once you choose.)")
        # Ensure readable text (avoid mojibake)
        try:
            self._info_lbl.config(text="You missed the minute - decide now. (Will log as late once you choose.)")
        except Exception:
            pass
        # Start speaker switch timer if enabled
        if self.settings.get("audio_try_speaker_switch", False):
            switch_delay = int(self.settings.get("audio_speaker_switch_after_seconds", 30)) * 1000
            self._schedule_timer(switch_delay, self._try_audio_device_switch)
        # Escalate to stage 4 if enabled
        if self.settings.get("overdrive_stage4_enabled", True):
            delay4 = int(self.settings.get("overdrive_stage4_after_seconds", 12)) * 1000
            self._schedule_timer(delay4, self._begin_overdrive_stage4)
        # Schedule overdrive Stage 5 (multi-monitor blackout/dim) after Stage 4 + configured delay
        if self.settings.get("overdrive_stage5_enabled", True):
            try:
                s4 = int(self.settings.get("overdrive_stage4_after_seconds", 12)) if self.settings.get("overdrive_stage4_enabled", True) else 0
            except Exception:
                s4 = 0
            try:
                s5 = int(self.settings.get("overdrive_stage5_after_seconds", 60))
            except Exception:
                s5 = 60
            self._schedule_timer(max(0, (s4 + s5) * 1000), self._begin_overdrive_stage5)

    def _pulse_buttons(self):
        """
        Create pulsing color effect on action buttons.

        Continuously cycles button background colors between values.
        """
        if self._closed: return
        self._pulse_val += self._pulse_dir * 22
        if self._pulse_val > 200: self._pulse_dir = -1
        if self._pulse_val < 30:  self._pulse_dir = 1
        v = self._pulse_val
        g = max(0, min(255, 50 + v))
        col = f"#{255:02x}{g:02x}{g:02x}"
        for b in self._action_buttons:
            try:
                b.configure(highlightthickness=0, bg=col, activebackground=col)
            except Exception:
                pass
        self._schedule_timer(70, self._pulse_buttons)

    def _shake_window(self, times=10, pixels=10, delay=20):
        """
        Shake the window back and forth.

        Args:
            times: Number of shake iterations
            pixels: Shake amplitude in pixels
            delay: Delay between shakes in milliseconds
        """
        if self._closed: return
        try:
            x0, y0 = self.winfo_x(), self.winfo_y()
            w, h = self.winfo_width(), self.winfo_height()
            rect = self._get_own_monitor_workarea()
        except Exception:
            self._shaking = False; return
        def do(n):
            if self._closed: return
            if n <= 0:
                # Reset exactly to original position (also clamped)
                cx, cy = self._clamp_to_rect(x0, y0, w, h, rect)
                self.geometry(f"+{cx}+{cy}")
                self._shaking = False; return
            if self.settings.get("shake_lock_position", True):
                # Do not move the window; simulate time passing only
                self._schedule_timer(delay, lambda: do(n-1))
                return
            dx = pixels if (n % 2 == 0) else -pixels
            nx, ny = x0 + dx, y0
            nx, ny = self._clamp_to_rect(nx, ny, w, h, rect)
            self.geometry(f"+{nx}+{ny}")
            self._schedule_timer(delay, lambda: do(n-1))
        do(times)

    def _flash_background(self):
        """
        Flash the dialog background between dark and red.

        Runs until overdrive stage 4 begins.
        """
        if self._closed or not self._overdrive or self._overdrive_stage4: return
        curr = self.cget("bg")
        nextc = "#300" if curr == "#111" else "#111"
        self.configure(bg=nextc)
        for f in (self.button_row,):
            f.config(bg=nextc)
        self._schedule_timer(120, self._flash_background)

    def _begin_overdrive_stage4(self):
        """
        Begin overdrive stage 4: ultra-fast red flashing.
        """
        if self._closed or not self._overdrive: return
        self._overdrive_stage4 = True
        # Play audio alert if configured for overdrive_stage4 trigger
        try:
            if self.settings.get("audio_alerts_enabled", False):
                if self.settings.get("audio_alarm_trigger", "overdrive") == "overdrive_stage4":
                    self._play_audio_alarm()
        except Exception:
            pass
        # Start ultra-fast red flashing
        self._flash_stage4()

    def _begin_overdrive_stage5(self):
        """
        Begin overdrive stage 5: screen dimming/blackout overlays.

        Creates overlays across all monitors or uses gamma/magnification
        effects to dim the screen.
        """
        if self._closed or not self._overdrive or self._overdrive_stage5:
            return
        self._overdrive_stage5 = True
        try:
            get_logger().info("overdrive stage5: begin")
        except Exception:
            pass
        # Play audio alert if configured for overdrive_stage5 trigger
        try:
            if self.settings.get("audio_alerts_enabled", False):
                if self.settings.get("audio_alarm_trigger", "overdrive") == "overdrive_stage5":
                    self._play_audio_alarm()
        except Exception:
            pass
        # If configured max alpha is zero or negative, skip creating overlays entirely
        try:
            _max_a_probe = float(self.settings.get("overdrive_stage5_dim_max_alpha", 0.92))
        except Exception:
            _max_a_probe = 0.92
        if _max_a_probe <= 0.0:
            try:
                get_logger().warning("overdrive stage5: skipped (max alpha <= 0)")
            except Exception:
                pass
            self._overdrive_stage5 = False
            return
        # Decide engine: overlay (default) or gamma/magnifier (Windows only)
        engine = str(self.settings.get("overdrive_stage5_engine", "overlay")).strip().lower()
        if engine not in ("overlay","gamma"):
            engine = "overlay"
        # Prefer magnification (color effect) on Windows for reliable click-through
        try:
            if platform.system().lower() == 'windows' and bool(self.settings.get('overdrive_stage5_click_through', True)):
                engine = 'mag'
        except Exception:
            pass
        self._stage5_engine = engine

        if engine == "mag" and platform.system().lower() == "windows":
            try:
                self._mag_prepare()
            except Exception:
                log_exception("stage5: magnifier prepare failed; falling back to gamma")
                self._stage5_engine = "gamma"
        if self._stage5_engine == "gamma" and platform.system().lower() == "windows":
            # Prepare gamma engine; no overlays created
            try:
                self._gamma_prepare()
            except Exception:
                log_exception("stage5: gamma prepare failed; falling back to overlay")
                self._stage5_engine = "overlay"

        if self._stage5_engine == "overlay":
            try:
                self._create_stage5_overlays()
            except Exception:
                log_exception("stage5 overlay creation failed")
        # Start dimming loop
        self._stage5_dim_alpha = 0.0
        self._stage5_dim_dir = 1
        try:
            self._stage5_start_mono = getattr(self, "_monotonic_now", time.monotonic)()
        except Exception:
            self._stage5_start_mono = 0.0
        self._stage5_hold_engaged = False
        self._stage5_dim_tick()

    def _gamma_prepare(self):
        """
        Prepare gamma engine for screen dimming (Windows only).

        Obtains device context and original gamma ramp for restoration.
        """
        if platform.system().lower() != 'windows':
            return
        gdi32 = ctypes.windll.gdi32
        user32 = ctypes.windll.user32
        _configure_gamma_api(user32, gdi32)
        class GAMMARAMP(ctypes.Structure):
            _fields_ = [("Red", ctypes.c_ushort * 256),
                        ("Green", ctypes.c_ushort * 256),
                        ("Blue", ctypes.c_ushort * 256)]
        self._GAMMARAMP = GAMMARAMP
        # Use screen DC (primary). This dims the built-in panel (typical laptop).
        hdc = user32.GetDC(None)
        if not hdc:
            raise RuntimeError("GetDC(None) failed")
        try:
            orig = GAMMARAMP()
            ok = gdi32.GetDeviceGammaRamp(hdc, ctypes.byref(orig))
            if not ok:
                # Some drivers don't support Get; still proceed with a generated linear ramp
                for i in range(256):
                    v = int(min(65535, max(0, i * 257)))
                    orig.Red[i] = v; orig.Green[i] = v; orig.Blue[i] = v
            self._gamma_hdc = hdc
            self._gamma_orig = orig
            self._gamma_active = True
        except Exception:
            # Clean up HDC if anything fails after GetDC
            try:
                user32.ReleaseDC(None, hdc)
            except Exception:
                pass
            raise

    def _gamma_apply_level(self, brightness: float):
        """
        Apply gamma brightness level (Windows only).

        Args:
            brightness: 1.0 = normal, 0.0 = black
        """
        if not self._gamma_active or platform.system().lower() != 'windows':
            return
        try:
            b = max(0.0, min(1.0, float(brightness)))
        except Exception:
            b = 1.0
        gdi32 = ctypes.windll.gdi32
        _configure_gamma_api(ctypes.windll.user32, gdi32)
        class GAMMARAMP(ctypes.Structure):
            _fields_ = [("Red", ctypes.c_ushort * 256),
                        ("Green", ctypes.c_ushort * 256),
                        ("Blue", ctypes.c_ushort * 256)]
        ramp = GAMMARAMP()
        # Build a simple linear ramp scaled by brightness
        for i in range(256):
            v = int(min(65535, max(0, round(i * 257 * b))))
            ramp.Red[i] = v
            ramp.Green[i] = v
            ramp.Blue[i] = v
        gdi32.SetDeviceGammaRamp(self._gamma_hdc, ctypes.byref(ramp))

    def _gamma_restore(self):
        """
        Restore original gamma ramp (Windows only).
        """
        if not self._gamma_active or platform.system().lower() != 'windows':
            return
        try:
            gdi32 = ctypes.windll.gdi32
            user32 = ctypes.windll.user32
            _configure_gamma_api(user32, gdi32)
            if self._gamma_hdc and self._gamma_orig:
                gdi32.SetDeviceGammaRamp(self._gamma_hdc, ctypes.byref(self._gamma_orig))
            if self._gamma_hdc:
                user32.ReleaseDC(None, self._gamma_hdc)
        except Exception:
            pass
        finally:
            self._gamma_active = False
            self._gamma_hdc = None
            self._gamma_orig = None

    def _mag_prepare(self):
        """
        Prepare magnification API for screen dimming (Windows only).

        Initializes magnification API for color effect transformations.
        """
        if platform.system().lower() != 'windows':
            return
        # Load Magnification API
        try:
            self._magnification = ctypes.windll.magnification
        except Exception as e:
            raise RuntimeError("Magnification API not available") from e
        _configure_magnification_api(self._magnification)
        if not self._magnification.MagInitialize():
            raise RuntimeError("MagInitialize failed")
        try:
            # Ensure identity first
            class MAGCOLOREFFECT(ctypes.Structure):
                _fields_ = [("transform", ctypes.c_float * 25)]
            self._MAGCOLOREFFECT = MAGCOLOREFFECT
            ident = MAGCOLOREFFECT()
            mat = ident.transform
            for i in range(25):
                mat[i] = 0.0
            mat[0] = mat[6] = mat[12] = 1.0
            mat[18] = 1.0  # alpha
            mat[24] = 1.0
            # Best effort; ignore failure
            try:
                self._magnification.MagSetFullscreenColorEffect(ctypes.byref(ident))
            except Exception:
                pass
            self._mag_active = True
        except Exception:
            # Clean up if anything fails after MagInitialize
            try:
                self._magnification.MagUninitialize()
            except Exception:
                pass
            raise

    def _mag_apply_level(self, brightness: float):
        """
        Apply magnification brightness level (Windows only).

        Args:
            brightness: 1.0 = normal, 0.0 = black
        """
        if not self._mag_active or platform.system().lower() != 'windows':
            return
        try:
            b = max(0.0, min(1.0, float(brightness)))
        except Exception:
            b = 1.0
        MAGCOLOREFFECT = self._MAGCOLOREFFECT
        eff = MAGCOLOREFFECT()
        mat = eff.transform
        for i in range(25):
            mat[i] = 0.0
        # Scale RGB by b; keep alpha 1
        mat[0] = b
        mat[6] = b
        mat[12] = b
        mat[18] = 1.0
        mat[24] = 1.0
        self._magnification.MagSetFullscreenColorEffect(ctypes.byref(eff))

    def _mag_restore(self):
        """
        Restore magnification API to normal (Windows only).
        """
        if not self._mag_active or platform.system().lower() != 'windows':
            return
        try:
            MAGCOLOREFFECT = self._MAGCOLOREFFECT
            eff = MAGCOLOREFFECT()
            mat = eff.transform
            for i in range(25):
                mat[i] = 0.0
            mat[0] = mat[6] = mat[12] = 1.0
            mat[18] = 1.0
            mat[24] = 1.0
            self._magnification.MagSetFullscreenColorEffect(ctypes.byref(eff))
        except Exception:
            pass
        try:
            self._magnification.MagUninitialize()
        except Exception:
            pass
        self._mag_active = False

    def _get_virtual_screen_rect(self):
        """
        Return (x, y, w, h) covering all monitors (Windows) or primary screen fallback.

        Returns:
            Tuple of (x, y, width, height)
        """
        try:
            if platform.system().lower() == "windows":
                user32 = ctypes.windll.user32
                SM_XVIRTUALSCREEN = 76
                SM_YVIRTUALSCREEN = 77
                SM_CXVIRTUALSCREEN = 78
                SM_CYVIRTUALSCREEN = 79
                x = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
                y = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
                w = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
                h = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
                if w > 0 and h > 0:
                    return (x, y, w, h)
        except Exception:
            pass
        # Fallback to single screen
        try:
            w = int(self.winfo_screenwidth())
            h = int(self.winfo_screenheight())
            return (0, 0, w, h)
        except Exception:
            return (0, 0, 1920, 1080)

    def _create_stage5_overlays(self):
        """
        Create overlay windows to cover all monitors.

        Uses native Windows overlays with click-through if possible,
        otherwise falls back to Tkinter overlays.
        """
        # Use a single virtual-screen overlay to cover all monitors
        x, y, w, h = self._get_virtual_screen_rect()
        try:
            get_logger().info("overdrive stage5: overlay rect x=%s y=%s w=%s h=%s", x, y, w, h)
        except Exception:
            pass
        color = str(self.settings.get("overdrive_stage5_dim_color", "#000000") or "#000000")
        click_through = bool(self.settings.get('overdrive_stage5_click_through', True))

        from ..windows_utils import _WinClickThroughOverlay, _enable_click_through_windows, _install_httransparent_wndproc

        if platform.system().lower() == 'windows' and click_through:
            # Robust native click-through overlay for Windows 10/11
            try:
                ov_native = _WinClickThroughOverlay(x, y, w, h, color_hex=color)
                self._stage5_overlays = [ov_native]
                # Store overlay HWND for Z-order positioning
                self._stage5_overlay_hwnd = ov_native.get_hwnd()

                try:
                    # Position main prompt dialog above overlay
                    prompt_hwnd = wintypes.HWND(self.winfo_id())
                    user32 = ctypes.windll.user32
                    _configure_window_position_api(user32)
                    SWP_NOACTIVATE = 0x0010
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    user32.SetWindowPos(
                        prompt_hwnd,
                        self._stage5_overlay_hwnd,  # Insert above overlay
                        0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                    )
                    self.lift(); self.focus_force()
                    self._lift_all_child_windows()
                except Exception:
                    pass
                return
            except Exception:
                log_exception("stage5: native overlay failed; falling back to Tk overlay")
        # Fallback: Tk overlay
        ov = tk.Toplevel(self)
        ov.withdraw()
        try: ov.overrideredirect(True)
        except Exception: pass
        # DON'T set topmost on overlay - we want FocusCheck windows above it
        # try: ov.attributes('-topmost', True)
        # except Exception: pass
        try: ov.configure(bg=color)
        except Exception: pass
        try: ov.geometry(f"{w}x{h}+{x}+{y}")
        except Exception: pass
        try: ov.attributes('-alpha', 0.0)
        except Exception: pass
        try: ov.deiconify()
        except Exception: pass
        # Mark this as an overlay so we can identify it later
        ov._is_stage5_overlay = True
        try:
            if platform.system().lower() == 'windows' and click_through:
                ov.update_idletasks()
                hwnd = wintypes.HWND(ov.winfo_id())
                _enable_click_through_windows(hwnd)
                _install_httransparent_wndproc(hwnd, owner_widget=ov)
        except Exception:
            pass
        self._stage5_overlays = [ov]
        # For Tkinter overlay, we don't have HWND, so just use Tk's lower/lift
        self._stage5_overlay_hwnd = None
        try:
            # Lower overlay below FocusCheck windows
            ov.lower(self)
            self.lift(); self.focus_force()
            self._lift_all_child_windows()
        except Exception:
            pass

    def _stage5_dim_tick(self):
        """
        Update stage 5 overlay opacity/brightness on a timer.

        Handles pulsing, slow dim, and hold behaviors based on settings.
        """
        if self._closed or not self._overdrive_stage5:
            return
        try:
            max_a = float(self.settings.get("overdrive_stage5_dim_max_alpha", 0.92))
        except Exception:
            max_a = 0.92
        slow_enabled = bool(self.settings.get("overdrive_stage5_slow_dim_enabled", False))
        try:
            slow_secs = int(self.settings.get("overdrive_stage5_slow_dim_seconds", 30))
        except Exception:
            slow_secs = 30
        pulse = bool(self.settings.get("overdrive_stage5_dim_pulse", True))
        try:
            hold_after = int(self.settings.get("overdrive_stage5_hold_after_seconds", 0))
        except Exception:
            hold_after = 0

        # Determine target alpha
        a = self._stage5_dim_alpha
        now_mono = getattr(self, "_monotonic_now", time.monotonic)()
        if slow_enabled:
            # One-way slow dim to black
            if slow_secs <= 0:
                a = max_a
            else:
                elapsed = max(0.0, now_mono - (self._stage5_start_mono or now_mono))
                # Prevent division by zero
                if slow_secs > 0.001:
                    prog = max(0.0, min(1.0, elapsed / float(slow_secs)))
                else:
                    prog = 1.0
                a = max_a * prog
        else:
            # Pulse fade in/out
            step = 0.05
            a = self._stage5_dim_alpha + (step * self._stage5_dim_dir)
            if a >= max_a:
                a = max_a
                if pulse:
                    self._stage5_dim_dir = -1
            if a <= 0.0:
                a = 0.0
                if pulse:
                    self._stage5_dim_dir = 1

        # Engage final hold if configured
        if (not self._stage5_hold_engaged) and hold_after > 0:
            try:
                if (now_mono - (self._stage5_start_mono or now_mono)) >= hold_after:
                    self._stage5_hold_engaged = True
                    a = max_a
            except Exception:
                pass

        self._stage5_dim_alpha = a

        # Apply engine output
        eng = getattr(self, '_stage5_engine', 'overlay')
        if eng == 'mag' and platform.system().lower() == 'windows':
            # Map overlay alpha to brightness via magnification color matrix
            self._mag_apply_level(1.0 - a)
        elif eng == 'gamma' and platform.system().lower() == 'windows':
            # Map overlay alpha to brightness (1.0 = normal, 0.0 = black)
            self._gamma_apply_level(1.0 - a)
        else:
            click_through = bool(self.settings.get('overdrive_stage5_click_through', True))
            from ..windows_utils import _enable_click_through_windows
            for ov in list(self._stage5_overlays or []):
                try:
                    if hasattr(ov, 'set_alpha') and callable(getattr(ov, 'set_alpha')):
                        ov.set_alpha(a)
                    else:
                        ov.attributes('-alpha', a)
                        # Re-assert click-through on Tk overlay in case Tk reset styles
                        if click_through and platform.system().lower() == 'windows':
                            try: ov.update_idletasks()
                            except Exception: pass
                            hwnd = wintypes.HWND(ov.winfo_id())
                            _enable_click_through_windows(hwnd)
                except Exception:
                    pass
        # Keep FocusCheck windows above overlays
        if getattr(self, '_stage5_engine', 'overlay') == 'overlay':
            try:
                # Re-position main prompt above overlay
                if platform.system().lower() == 'windows':
                    try:
                        prompt_hwnd = wintypes.HWND(self.winfo_id())
                        user32 = ctypes.windll.user32
                        _configure_window_position_api(user32)
                        SWP_NOACTIVATE = 0x0010
                        SWP_NOMOVE = 0x0002
                        SWP_NOSIZE = 0x0001
                        overlay_hwnd = getattr(self, '_stage5_overlay_hwnd', None)
                        try:
                            insert_after = wintypes.HWND(overlay_hwnd) if overlay_hwnd else wintypes.HWND(-1)
                        except Exception:
                            insert_after = wintypes.HWND(-1)

                        # Position at top of topmost layer, above the overlay
                        user32.SetWindowPos(
                            prompt_hwnd,
                            insert_after,
                            0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                        )
                    except Exception:
                        pass

                self.lift()
                self._lift_all_child_windows()
            except Exception:
                pass
        # Schedule next tick unless we're holding final black
        if self._stage5_hold_engaged and slow_enabled:
            # In slow-dim mode, once held at max we can stop ticking
            self._stage5_dim_timer = None
            return
        if self._stage5_hold_engaged and not slow_enabled and not pulse:
            # If we weren't pulsing anyway, stop
            self._stage5_dim_timer = None
            return
        try:
            # Use 500ms for better performance while maintaining smooth animation
            self._stage5_dim_timer = self._schedule_timer(500, self._stage5_dim_tick)
        except Exception:
            self._stage5_dim_timer = None

    def _destroy_stage5_overlays(self):
        """
        Destroy stage 5 overlays and restore screen to normal.

        Cleans up overlay windows and restores gamma/magnification settings.
        """
        try:
            if self._stage5_dim_timer is not None:
                try:
                    self._cancel_timer(self._stage5_dim_timer)
                    # Only clear timer ID if cancellation succeeded
                    self._stage5_dim_timer = None
                except Exception:
                    # If cancellation failed, log but still clear to prevent double-cancel
                    try:
                        get_logger().warning("Failed to cancel stage5 dim timer")
                    except Exception:
                        pass
                    self._stage5_dim_timer = None
        except Exception:
            pass
        # Restore gamma engine if used
        try:
            if getattr(self, '_stage5_engine', 'overlay') == 'gamma':
                self._gamma_restore()
        except Exception:
            pass
        # Restore magnification engine if used
        try:
            if getattr(self, '_stage5_engine', 'overlay') == 'mag':
                self._mag_restore()
        except Exception:
            pass

        from ..windows_utils import GWL_WNDPROC

        try:
            for ov in list(self._stage5_overlays or []):
                # Restore original wndproc if we subclassed for click-through
                try:
                    old = getattr(ov, "_ct_click_oldproc", None)
                    setter = getattr(ov, "_ct_click_setter", None)
                    if old and setter:
                        try:
                            setter(wintypes.HWND(ov.winfo_id()), GWL_WNDPROC, ctypes.c_void_p(old))
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    ov.destroy()
                except Exception:
                    pass
        finally:
            self._stage5_overlays = []

        # Reset topmost attribute on windows that were lifted during stage 5
        try:
            for window in getattr(self, '_stage5_topmost_windows', []):
                try:
                    if window.winfo_exists():
                        window.attributes('-topmost', False)
                except Exception:
                    pass
            self._stage5_topmost_windows = []
        except Exception:
            pass

        try:
            get_logger().info("overdrive stage5: destroyed overlays and reset window states")
        except Exception:
            pass

    def _flash_stage4(self):
        """
        Ultra-fast red flashing for stage 4 overdrive.

        Alternates between dark red and normal background at high frequency.
        """
        if self._closed or not self._overdrive_stage4: return
        curr = self.cget("bg")
        nextc = "#b00" if curr != "#b00" else "#111"
        self.configure(bg=nextc)
        for f in (self.button_row,):
            f.config(bg=nextc)
        # Accent buttons as well for consistent alerting
        try:
            for b in self._action_buttons:
                b.configure(bg=("#ff4d4d" if nextc == "#b00" else "#333"), activebackground=("#ff4d4d" if nextc == "#b00" else "#333"))
        except Exception:
            pass
        rate = max(20, int(self.settings.get("overdrive_stage4_flash_ms", 60)))
        self._schedule_timer(rate, self._flash_stage4)

    def _shake_loop(self, amplitude=16, delay=14):
        """
        Continuous shaking loop during overdrive.

        Args:
            amplitude: Shake amplitude in pixels
            delay: Delay between shake movements
        """
        if self._closed or not self._overdrive: return
        self._shake_window(times=8, pixels=amplitude, delay=delay)
        self._schedule_timer(220, lambda: self._shake_loop(amplitude, delay))

    def _jiggle_buttons(self):
        """
        Apply jiggling effect to buttons during overdrive.

        Can use different styles: nudge (position) or pulse (size).
        """
        if self._closed or not self._overdrive: return
        style = str(self.settings.get("jiggle_style", "nudge"))
        if style == "off":
            return
        if style == "nudge":
            self._place_buttons_nudge()
        elif style == "pulse":
            fs = random.choice([15,16,17,18])
            try:
                self.btn_study.config(font=("Segoe UI", fs, "bold"))
                if self.btn_waste is not None:
                    self.btn_waste.config(font=("Segoe UI", fs, "bold"))
            except Exception:
                pass
        self._schedule_timer(1200, self._jiggle_buttons)

    def _place_buttons_nudge(self):
        """
        Nudge buttons slightly without full randomization.

        Minimal movement to maintain click-ability during overdrive jiggle.
        """
        # Minimal, click-friendly movement
        for w in self.button_row.winfo_children():
            w.grid_forget()
        pad_l = random.randint(0, 2)
        pad_r = random.randint(0, 2)
        pad_y = random.randint(0, 2)
        if self.btn_waste is None:
            pad = max(pad_l, pad_r)
            self.btn_study.grid(row=0, column=0, padx=(pad, pad), pady=pad_y)
        else:
            # Keep order stable to avoid chasing
            self.btn_study.grid(row=0, column=0, padx=(pad_l, 6), pady=pad_y)
            self.btn_waste.grid(row=0, column=1, padx=(6, pad_r), pady=pad_y)

    def _play_audio_alarm(self):
        """
        Play audio alarm based on settings.

        Uses pattern, mode, duration, and safety settings from configuration.
        """
        try:
            alarm = get_audio_alarm()
            if not alarm.is_available():
                return

            pattern = str(self.settings.get("audio_alarm_pattern", "rapid_beeps"))
            mode = str(self.settings.get("audio_alarm_mode", "once"))
            duration = int(self.settings.get("audio_alarm_duration_seconds", 5))
            safe_mode = bool(self.settings.get("audio_earphone_safe_mode", True))
            max_volume = float(self.settings.get("audio_max_volume", 0.7))

            alarm.play_pattern(
                pattern=pattern,
                duration_seconds=duration,
                mode=mode,
                safe_mode=safe_mode,
                max_volume=max_volume
            )
        except Exception:
            log_exception("Audio alarm playback failed")

    def _try_audio_device_switch(self):
        """
        Try to switch audio output from headphones to speakers.

        Called after configured delay if user still hasn't responded.
        """
        if self._closed or not self._overdrive:
            return

        try:
            alarm = get_audio_alarm()
            if alarm.can_switch_devices():
                if alarm.try_switch_to_speakers():
                    try:
                        get_logger().info("Audio output switched to speakers")
                    except Exception:
                        pass
                    # Play alarm again on speakers
                    self._play_audio_alarm()
        except Exception:
            log_exception("Audio device switch failed")
