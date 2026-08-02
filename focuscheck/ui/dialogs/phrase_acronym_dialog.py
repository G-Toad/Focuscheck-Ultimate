"""
Phrase Acronym Challenge Dialog.

Shows acronym boxes that user must fill by clicking letter buttons or typing.
Letter buttons are disabled when used and re-enabled when cleared.
Incorrect button clicks show visual feedback on the correct target box.
Auto-continues when all letters are correctly placed.
"""

import tkinter as tk
from tkinter import font as tkfont
import random
import re
import platform
import ctypes


class PhraseAcronymDialog(tk.Toplevel):
    """Dialog for phrase acronym challenge with button clicks and typing."""

    def __init__(self, parent, phrase, on_complete, settings):
        """
        Initialize the acronym challenge dialog.

        Args:
            parent: Parent window
            phrase: Full phrase to extract acronym from
            on_complete: Callback function when challenge is completed
            settings: Settings dictionary for display options
        """
        super().__init__(parent)

        self.phrase = phrase
        self.on_complete = on_complete
        self.settings = settings

        # Extract acronym (first letter of each word, letters only)
        # Enhanced regex handles:
        # - Contractions: don't, you're, I'm, we'll, they've
        # - Leading apostrophes: 'twas, 'tis, rock 'n' roll
        # - Trailing apostrophes: goin', singin', dancin'
        # - Hyphenated words: self-esteem, mother-in-law (treated as ONE word)
        # - Complex contractions: y'all, y'all'd've, shouldn't've
        # - Possessives: John's, students'
        # Pattern explanation:
        #   '?              - Optional leading apostrophe
        #   [A-Za-z]+       - One or more letters (required)
        #   (?:[-'][A-Za-z]+)* - Zero or more groups of (hyphen OR apostrophe + letters)
        #   '?              - Optional trailing apostrophe
        pattern = r"'?[A-Za-z]+(?:[-'][A-Za-z]+)*'?"
        words = re.findall(pattern, phrase)

        # Clean up matched words: remove leading/trailing apostrophes and hyphens
        cleaned_words = []
        for word in words:
            # Strip unwanted leading/trailing characters (', -)
            cleaned = word.strip("'-")
            if cleaned:  # Only add non-empty words
                cleaned_words.append(cleaned)

        # Extract first letter of each cleaned word
        self.acronym = ''.join(word[0].upper() for word in cleaned_words if word)

        if not self.acronym:
            # No valid acronym - call complete immediately
            self.destroy()
            if callable(on_complete):
                on_complete()
            return

        # State tracking
        self.boxes = []  # Entry widgets for each letter
        self.letter_buttons = []  # Clickable letter buttons
        self.letter_to_button = {}  # Map letter index to button for easy lookup

        # Get display settings
        self.box_size = settings.get("phrase_acronym_box_size", 60)
        self.letter_size = settings.get("phrase_acronym_letter_size", 45)
        self.font_size = settings.get("phrase_acronym_font_size", 16)

        # Configure window
        self.title("Phrase Challenge")
        self.configure(bg="#2b2b2b")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Make always on top
        self.attributes("-topmost", True)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Build UI
        self._create_ui()

        # Center on screen
        self.update_idletasks()
        self._center_window()

        # Force window to be visible and rendered
        self.update()

        # Aggressively force window to front
        self._force_window_to_front()

        # Focus first box multiple times to ensure it works
        self.after(100, self._focus_first_box)
        self.after(200, self._focus_first_box)
        self.after(300, self._focus_first_box)

    def _force_window_to_front(self):
        """Aggressively force window to front and grab focus (Windows-specific)."""
        if platform.system().lower() != "windows":
            # Non-Windows fallback
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass
            return

        try:
            hwnd = self.winfo_id()
            user32 = ctypes.windll.user32

            # 1. Attach to foreground thread
            try:
                foreground = user32.GetForegroundWindow()
                if foreground != hwnd:
                    fg_thread = user32.GetWindowThreadProcessId(foreground, None)
                    this_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                    if fg_thread != this_thread:
                        user32.AttachThreadInput(fg_thread, this_thread, True)
            except Exception:
                pass

            # 2. Show and force to foreground
            SW_SHOW = 5
            user32.ShowWindow(hwnd, SW_SHOW)
            user32.SetForegroundWindow(hwnd)

            # 3. Bring to top
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_SHOWWINDOW = 0x0040
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002

            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                               SWP_SHOWWINDOW | SWP_NOSIZE | SWP_NOMOVE)
            user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                               SWP_SHOWWINDOW | SWP_NOSIZE | SWP_NOMOVE)

            # 4. Set focus
            user32.SetFocus(hwnd)

            # 5. Tkinter-level focus
            self.lift()
            self.focus_force()

        except Exception:
            # Fallback to tkinter methods
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass

    def _focus_first_box(self):
        """Focus the first input box (called after window is fully visible)."""
        if self.boxes:
            try:
                # Re-force window focus first
                if platform.system().lower() == "windows":
                    try:
                        hwnd = self.winfo_id()
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
                self.lift()
                self.focus_force()

                # Then focus the box
                self.boxes[0].focus_force()
                self.boxes[0].icursor(0)  # Set cursor at start of entry
            except Exception:
                pass

    def _create_ui(self):
        """Create the dialog UI."""
        main_frame = tk.Frame(self, bg="#2b2b2b", padx=30, pady=30)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title label
        title_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        title_lbl = tk.Label(
            main_frame,
            text="Complete the acronym:",
            font=title_font,
            bg="#2b2b2b",
            fg="#ffffff"
        )
        title_lbl.pack(pady=(0, 20))

        # Acronym boxes frame
        boxes_frame = tk.Frame(main_frame, bg="#2b2b2b")
        boxes_frame.pack(pady=(0, 30))

        self._create_acronym_boxes(boxes_frame)

        # Available letters label
        available_font = tkfont.Font(family="Segoe UI", size=11, weight="normal")
        available_lbl = tk.Label(
            main_frame,
            text="Available Letters:",
            font=available_font,
            bg="#2b2b2b",
            fg="#888888"
        )
        available_lbl.pack(pady=(0, 10))

        # Draggable letters frame
        letters_frame = tk.Frame(main_frame, bg="#2b2b2b")
        letters_frame.pack(pady=(0, 30))

        self._create_draggable_letters(letters_frame)

        # Phrase display
        phrase_font = tkfont.Font(family="Segoe UI", size=self.font_size, slant="italic")
        phrase_lbl = tk.Label(
            main_frame,
            text=f'"{self.phrase}"',
            font=phrase_font,
            bg="#2b2b2b",
            fg="#888888",
            wraplength=500
        )
        phrase_lbl.pack(pady=(0, 10))

    def _create_acronym_boxes(self, parent):
        """Create the acronym input boxes."""
        box_font = tkfont.Font(family="Consolas", size=24, weight="bold")

        for i, letter in enumerate(self.acronym):
            # Create frame for each box
            box_frame = tk.Frame(parent, bg="#2b2b2b")
            box_frame.pack(side=tk.LEFT, padx=5)

            # Create entry box
            box = tk.Entry(
                box_frame,
                width=2,
                font=box_font,
                justify=tk.CENTER,
                bg="#1a1a1a",
                fg="#ffffff",
                insertbackground="#ffffff",
                bd=2,
                relief=tk.SOLID,
                highlightthickness=2,
                highlightbackground="#444444",
                highlightcolor="#00aaff"
            )
            box.pack()

            # Configure entry
            box.configure(validate="key", validatecommand=(box.register(self._validate_box_input), '%P', '%W'))

            # Bind events
            box.bind('<KeyRelease>', lambda e, idx=i: self._on_box_keyrelease(e, idx))
            box.bind('<Button-1>', lambda e, b=box: self._on_box_click(e, b))

            # Store reference
            self.boxes.append(box)

            # Store expected letter and index as widget attributes
            box.expected_letter = letter
            box.expected_index = i
            box.filled_index = None  # Track which button filled this box

    def _create_draggable_letters(self, parent):
        """Create clickable letter buttons."""
        # Create randomized list of letters with indices
        letter_indices = list(range(len(self.acronym)))
        random.shuffle(letter_indices)

        letter_font = tkfont.Font(family="Segoe UI", size=20, weight="bold")

        for idx in letter_indices:
            letter = self.acronym[idx]

            # Create clickable button
            btn = tk.Button(
                parent,
                text=letter,
                font=letter_font,
                bg="#3a7ca5",
                fg="#ffffff",
                activebackground="#2a5c85",
                activeforeground="#ffffff",
                width=3,
                height=1,
                relief=tk.RAISED,
                bd=2,
                cursor="hand2",
                command=lambda b=None, l=letter, i=idx: self._on_letter_click(l, i)
            )
            btn.pack(side=tk.LEFT, padx=5)

            # Store letter value and index
            btn.letter = letter
            btn.letter_index = idx
            btn.used = False  # Track if letter has been correctly placed

            self.letter_buttons.append(btn)
            self.letter_to_button[idx] = btn

    def _validate_box_input(self, new_value, widget_name):
        """Validate input in boxes (only allow single uppercase letter)."""
        if not new_value:
            return True  # Allow empty
        if len(new_value) > 1:
            return False  # Only one character
        if not new_value.isalpha():
            return False  # Only letters
        return True

    def _on_box_keyrelease(self, event, box_index):
        """Handle key release in box (typing mode)."""
        box = self.boxes[box_index]
        entered = box.get().upper()

        if not entered:
            # Box is empty - re-enable the button that was used here
            if box.filled_index is not None:
                btn = self.letter_to_button.get(box.filled_index)
                if btn:
                    btn.used = False
                    btn.config(state=tk.NORMAL)
                box.filled_index = None
            box.configure(highlightbackground="#444444")
            return

        # Check if correct
        if entered == box.expected_letter:
            # Update to uppercase
            box.delete(0, tk.END)
            box.insert(0, entered)

            # Correct letter
            box.configure(highlightbackground="#00ff00")

            # Find and disable the corresponding letter button
            for btn in self.letter_buttons:
                if btn.letter == entered and not btn.used:
                    btn.used = True
                    btn.config(state=tk.DISABLED)
                    box.filled_index = btn.letter_index
                    break

            # Move to next box if not last
            if box_index < len(self.boxes) - 1:
                self.boxes[box_index + 1].focus_set()

            # Check if all complete
            self.after(100, self._check_completion)
        else:
            # Wrong letter - clear the box and highlight red
            box.delete(0, tk.END)
            box.configure(highlightbackground="#ff0000")
            # Reset after a moment
            self.after(300, lambda: box.configure(highlightbackground="#444444"))

    def _on_box_click(self, event, box):
        """Handle click on box to focus it."""
        box.focus_set()

    def _on_letter_click(self, letter, letter_index):
        """
        Handle click on letter button.

        Places the letter in the focused box or next empty box.
        Only allows placement if the letter is correct for that position.
        """
        # Find target box - use focused box if it's an entry box, otherwise first empty
        target_box = self.focus_get()
        target_index = None

        if target_box in self.boxes:
            target_index = self.boxes.index(target_box)
        else:
            # Not focused on a box, find first empty box
            for i, box in enumerate(self.boxes):
                if not box.get():
                    target_box = box
                    target_index = i
                    break

        # If still no target, use first box
        if target_index is None:
            target_box = self.boxes[0]
            target_index = 0

        # Check if this letter is correct for the target box
        expected = target_box.expected_letter

        if letter == expected:
            # Clear any existing content and re-enable its button
            if target_box.filled_index is not None:
                old_btn = self.letter_to_button.get(target_box.filled_index)
                if old_btn:
                    old_btn.used = False
                    old_btn.config(state=tk.NORMAL)

            # Place the letter
            target_box.delete(0, tk.END)
            target_box.insert(0, letter)
            target_box.configure(highlightbackground="#00ff00")

            # Mark button as used and disable it
            btn = self.letter_to_button[letter_index]
            btn.used = True
            btn.config(state=tk.DISABLED)
            target_box.filled_index = letter_index

            # Move to next box if not last
            if target_index < len(self.boxes) - 1:
                self.boxes[target_index + 1].focus_set()

            # Check completion
            self.after(100, self._check_completion)
        else:
            # Wrong letter - flash red feedback on the correct box for this letter
            correct_box_index = letter_index
            if correct_box_index < len(self.boxes):
                correct_box = self.boxes[correct_box_index]
                original_bg = correct_box.cget("highlightbackground")
                correct_box.configure(highlightbackground="#ff0000")
                self.after(300, lambda: correct_box.configure(highlightbackground=original_bg) if not correct_box.get() else None)

    def _check_completion(self):
        """Check if all boxes are correctly filled."""
        all_correct = True

        for box in self.boxes:
            entered = box.get().upper()
            if entered != box.expected_letter:
                all_correct = False
                break

        if all_correct and all(box.get() for box in self.boxes):
            # All correct - auto-complete
            self._complete()

    def _complete(self):
        """Complete the challenge successfully."""
        # Flash green feedback
        for box in self.boxes:
            box.configure(highlightbackground="#00ff00")

        # Close after short delay
        self.after(300, self._finish_and_close)

    def _finish_and_close(self):
        """Finish challenge and close dialog."""
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        if callable(self.on_complete):
            self.on_complete()

    def _on_close(self):
        """Handle window close button (treat as cancel)."""
        # Don't call on_complete - user cancelled
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _center_window(self):
        """Center the dialog on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
