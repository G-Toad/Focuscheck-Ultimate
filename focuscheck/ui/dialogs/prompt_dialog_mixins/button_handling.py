"""
Button handling mixin for PromptDialog.

Contains all button-related methods including placement, configuration,
focus management, and event handling.
"""

import random
import tkinter as tk

try:
    from ...utils import get_logger
except ImportError:
    import logging
    def get_logger():
        return logging.getLogger(__name__)


class ButtonHandlingMixin:
    """Mixin for button-related functionality in PromptDialog."""

    def _place_buttons_random(self):
        """
        Randomly arrange buttons in the button row.

        Applies randomization settings for button position and padding
        to prevent habit formation.
        """
        for w in self.button_row.winfo_children():
            w.grid_forget()
        left_first = True
        if self.settings["anti_habit_enabled"] and self.settings["randomize_buttons"] and self.btn_waste is not None:
            left_first = bool(random.getrandbits(1))
        pad_l = random.randint(0, 12) if self.settings["randomize_buttons"] else 6
        pad_r = random.randint(0, 12) if self.settings["randomize_buttons"] else 6
        pad_y = random.randint(0, 6) if self.settings["randomize_buttons"] else 4

        if self.btn_waste is None:
            pad = max(pad_l, pad_r)
            self.btn_study.grid(row=0, column=0, padx=(pad, pad), pady=pad_y)
        else:
            if left_first:
                self.btn_study.grid(row=0, column=0, padx=(pad_l, 6), pady=pad_y)
                self.btn_waste.grid(row=0, column=1, padx=(6, pad_r), pady=pad_y)
            else:
                self.btn_waste.grid(row=0, column=0, padx=(pad_l, 6), pady=pad_y)
                self.btn_study.grid(row=0, column=1, padx=(6, pad_r), pady=pad_y)
        self._update_action_button_default()

    def _configure_action_buttons(self):
        """
        Configure all action buttons with focus and keyboard handlers.

        Ensures all buttons in _action_buttons list have proper event
        bindings for focus and keyboard interaction.
        """
        # Ensure tracking list ignores widgets that were destroyed
        alive = []
        for btn in getattr(self, '_bound_action_buttons', []):
            try:
                if btn is not None and btn.winfo_exists():
                    alive.append(btn)
            except Exception:
                pass
        self._bound_action_buttons = alive
        for btn in self._action_buttons:
            self._configure_single_action_button(btn)

    def _configure_single_action_button(self, btn):
        """
        Configure a single action button with event handlers.

        Args:
            btn: The button widget to configure
        """
        if btn is None or btn in self._bound_action_buttons:
            return
        try:
            btn.configure(takefocus=True)
        except Exception:
            pass
        btn.bind('<FocusIn>', lambda _evt, b=btn: self._on_action_button_focus(b), add=True)
        btn.bind('<Return>', lambda _evt, b=btn: self._handle_action_button_key(b), add=True)
        btn.bind('<KP_Enter>', lambda _evt, b=btn: self._handle_action_button_key(b), add=True)
        btn.bind('<space>', lambda _evt, b=btn: self._handle_action_button_key(b), add=True)
        self._bound_action_buttons.append(btn)

    def _on_action_button_focus(self, btn):
        """
        Handle focus event on an action button.

        Args:
            btn: The button that received focus
        """
        self._update_action_button_default(btn)

    def _handle_action_button_key(self, btn):
        """
        Handle keyboard activation of an action button.

        Args:
            btn: The button to invoke

        Returns:
            'break' to stop event propagation
        """
        self._invoke_action_button(btn)
        return 'break'

    def _invoke_action_button(self, btn):
        """
        Invoke the action associated with a button.

        Args:
            btn: The button to invoke (btn_study or btn_waste)
        """
        logger = get_logger()
        logger.info("=" * 80)
        logger.info("BUTTON CLICK: _invoke_action_button() CALLED")
        logger.info("  Button: %s", btn)
        logger.info("  Button text: %s", btn.cget('text') if btn else "None")

        if btn is None:
            logger.warning("  Button is None, returning without action")
            logger.info("BUTTON CLICK: _invoke_action_button() ABORTED (None)")
            logger.info("=" * 80)
            return

        logger.info("  Identifying which button was clicked...")

        try:
            if btn is self.btn_study:
                logger.info("  >>> STUDYING BUTTON CLICKED <<<")
                logger.info("    Button object: %s", btn)
                logger.info("    Button text: %s", btn.cget('text'))
                logger.info("    Calling _trigger_studying_choice()...")
                self._trigger_studying_choice()
                logger.info("    _trigger_studying_choice() completed")
                logger.info("BUTTON CLICK: _invoke_action_button() COMPLETED (STUDYING)")
                logger.info("=" * 80)
                return

            if btn is self.btn_waste:
                logger.info("  >>> WASTING TIME BUTTON CLICKED <<<")
                logger.info("    Button object: %s", btn)
                logger.info("    Button text: %s", btn.cget('text'))
                logger.info("    Calling _on_wasting_clicked()...")
                self._on_wasting_clicked()
                logger.info("    _on_wasting_clicked() completed")
                logger.info("BUTTON CLICK: _invoke_action_button() COMPLETED (WASTING)")
                logger.info("=" * 80)
                return

            logger.warning("  Unknown button, not study or waste")
            logger.info("    self.btn_study: %s", self.btn_study)
            logger.info("    self.btn_waste: %s", self.btn_waste)
            logger.info("    clicked button: %s", btn)

        except Exception as e:
            logger.error("  ERROR identifying button: %s", e)
            logger.exception("  Full exception:")

        logger.info("  Falling back to generic btn.invoke()...")
        try:
            logger.info("    Calling btn.invoke()...")
            btn.invoke()
            logger.info("    btn.invoke() completed")
        except Exception as e:
            logger.error("    ERROR invoking button: %s", e)
            logger.exception("    Full exception:")

        logger.info("BUTTON CLICK: _invoke_action_button() COMPLETED (generic invoke)")
        logger.info("=" * 80)

    def _handle_action_key(self, event):
        """
        Handle Enter/Return key press for action buttons.

        Args:
            event: The keyboard event

        Returns:
            None to allow event propagation, or result from button handler
        """
        widget = self.focus_get()
        if widget in self._action_buttons:
            return self._handle_action_button_key(widget)
        # Don't steal Enter from text/entry widgets
        ENTRY_WIDGET_TYPES = (tk.Entry, tk.Text)
        try:
            from tkinter import ttk
            ENTRY_WIDGET_TYPES = (tk.Entry, ttk.Entry, tk.Text)
        except ImportError:
            pass
        if widget is not None and isinstance(widget, ENTRY_WIDGET_TYPES):
            return None
        # When auto-focus is enabled, ALWAYS prefer Study button
        # This ensures Enter key triggers Study, not Wasting Time
        if self._modal_auto_focus_enabled() and self.btn_study is not None:
            try:
                if self.btn_study.winfo_exists() and self.btn_study.winfo_ismapped():
                    return self._handle_action_button_key(self.btn_study)
            except Exception:
                pass
        # Fallback: use primary button (grid order)
        if widget is None or widget == self:
            target = self._get_primary_action_button()
            if target is not None:
                self._focus_button(target)
                return self._handle_action_button_key(target)
        return None

    def _focus_button(self, btn):
        """
        Set focus to a specific button.

        Args:
            btn: The button to focus
        """
        if btn is None:
            return
        try:
            self.lift()
        except Exception:
            pass
        try:
            self.focus_force()
        except Exception:
            pass
        try:
            btn.focus_force()  # Use focus_force for more aggressive focus
        except Exception:
            pass
        self._update_action_button_default(btn)

    def _update_action_button_default(self, active_button=None):
        """
        Update the default button styling.

        Args:
            active_button: The button to mark as default, or None to use primary
        """
        for candidate in self._action_buttons:
            if candidate is None:
                continue
            try:
                candidate.configure(default='normal')
            except tk.TclError:
                pass
        if active_button is None:
            active_button = self._get_primary_action_button()
        if active_button is not None:
            try:
                active_button.configure(default='active')
            except tk.TclError:
                pass

    def _get_primary_action_button(self):
        """
        Get the primary action button (first visible button in grid order).

        Returns:
            The primary button widget, or None if no buttons available
        """
        buttons = [btn for btn in self._action_buttons if btn is not None]
        if not buttons:
            return None
        available = []
        for btn in buttons:
            try:
                if btn.winfo_exists() and btn.winfo_ismapped():
                    available.append(btn)
            except Exception:
                continue
        if not available:
            return None
        try:
            return min(available, key=lambda b: (
                int(b.grid_info().get('row', 0)),
                int(b.grid_info().get('column', 0))
            ))
        except Exception:
            return available[0]

    def _focus_first_action_button(self):
        """Focus the first (primary) action button."""
        self._focus_button(self._get_primary_action_button())

    def _sync_initial_button_focus(self):
        """
        Synchronize initial button focus state.

        Called after dialog creation to set proper initial focus
        based on modal auto-focus settings.
        """
        # Force window to front again (in case focus was stolen)
        try:
            self._force_window_to_front()
        except Exception:
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass

        if self._modal_auto_focus_enabled():
            self._focus_first_action_button()
        else:
            self._update_action_button_default()
