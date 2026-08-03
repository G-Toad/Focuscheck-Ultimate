"""
Manual Crop Adjustment Window.

Provides a comprehensive live preview interface for manually adjusting camera crop settings.
Features include multiple anchor modes, zoom control, grid overlays, crop presets, and real-time statistics.
"""

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import platform
from ..settings.manager import save_settings
from .camera.manual_crop_utils import calculate_crop_region
from ..utils.timers import TimerRegistry

# Try to import cv2 for camera access
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

# Try to import PIL for image conversion
try:
    from PIL import Image, ImageTk, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageTk = None


class CropAdjustmentWindow(tk.Toplevel):
    """
    Window for adjusting manual crop settings with live camera preview.

    Features:
    - Live camera feed with crop rectangle overlay
    - Multiple anchor modes (Edge, Corner, Center)
    - Zoom control with visual feedback
    - Grid overlays (rule-of-thirds, 4x4)
    - Crop presets (save/load configurations)
    - Real-time statistics
    - Test preview mode
    """

    def __init__(self, parent, settings, on_settings_updated, persist_settings=None):
        """
        Initialize crop adjustment window.

        Args:
            parent: Parent window
            settings: Settings dictionary
            on_settings_updated: Callback function(new_settings) when settings are applied
            persist_settings: Optional App-owned callback receiving the full draft
        """
        super().__init__(parent)

        self.settings = settings.copy()  # Work with a copy until applied
        self.on_settings_updated = on_settings_updated
        self.persist_settings = persist_settings
        self.original_settings = settings.copy()  # Keep original for dirty checking
        self.has_unsaved_changes = False  # Track if settings have been modified

        # Camera state
        self.camera = None
        self.camera_update_timer = None
        self._camera_generation = 0
        self._camera_init_timer = None
        self._timers = TimerRegistry(self)
        self.current_frame = None
        self.preview_photo = None
        self.crop_preview_photo = None

        # Configure window
        self.title("Manual Crop Adjustment - Live Preview")
        self.configure(bg="#1a1a1a")

        # More reasonable default size
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = min(1100, int(screen_width * 0.85))
        window_height = min(650, int(screen_height * 0.85))
        self.geometry(f"{window_width}x{window_height}")

        # Set minimum size
        self.minsize(900, 550)
        self.resizable(True, True)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Build UI
        self._create_ui()

        # Start camera if available
        if CV2_AVAILABLE and PIL_AVAILABLE:
            self._timers.schedule(
                "camera-init",
                500,
                lambda: self._initialize_camera(self._camera_generation),
            )
            self._camera_init_timer = self._timers.callback_id("camera-init")
        else:
            messagebox.showwarning(
                "Camera Unavailable",
                "OpenCV and PIL are required for live preview.\n"
                "Install with: pip install opencv-python pillow\n\n"
                "You can still adjust settings without preview.",
                parent=self
            )

        # Center window
        self.update_idletasks()
        self._center_window()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Keyboard shortcuts
        self.bind("<Control-s>", lambda e: self._save_and_close())  # Save & close
        self.bind("<Control-S>", lambda e: self._save_and_close())
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.bind("<Control-r>", lambda e: self._reset_to_defaults())
        self.bind("<Control-R>", lambda e: self._reset_to_defaults())
        self.bind("<Control-d>", lambda e: self._auto_detect_face())
        self.bind("<Control-D>", lambda e: self._auto_detect_face())

    def _create_ui(self):
        """Build the main UI layout."""
        # IMPORTANT: Create button bar FIRST so it's always visible at bottom
        self._create_button_bar()

        # Main container with resizable panels (will fill remaining space above buttons)
        main_container = tk.Frame(self, bg="#1a1a1a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        # Use PanedWindow for resizable panels
        self.paned_window = tk.PanedWindow(
            main_container,
            orient=tk.HORIZONTAL,
            sashwidth=8,
            sashrelief=tk.RAISED,
            bg="#00aaff",
            bd=0
        )
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Left panel - Preview (60% width - larger for better visibility)
        preview_container = tk.Frame(self.paned_window, bg="#2b2b2b")
        self._create_preview_panel(preview_container)
        self.paned_window.add(preview_container, minsize=500, width=650)

        # Right panel - Controls (40% width - compact but functional)
        controls_container = tk.Frame(self.paned_window, bg="#2b2b2b")
        self._create_controls_panel(controls_container)
        self.paned_window.add(controls_container, minsize=350, width=450)

    def _create_preview_panel(self, parent):
        """Create left panel with live camera preview."""
        preview_panel = tk.Frame(parent, bg="#2b2b2b")
        preview_panel.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = tk.Frame(preview_panel, bg="#2b2b2b")
        header_frame.pack(fill=tk.X, pady=5)

        title_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        title_label = tk.Label(
            header_frame,
            text="Live Camera Preview",
            font=title_font,
            bg="#2b2b2b",
            fg="#00aaff"
        )
        title_label.pack(pady=5)

        # Main camera preview canvas
        preview_frame = tk.Frame(preview_panel, bg="#000000")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_canvas = tk.Canvas(
            preview_frame,
            bg="#000000",
            highlightthickness=0,
            width=700,
            height=525
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        # Crop preview inset
        inset_frame = tk.Frame(preview_panel, bg="#1a1a1a", relief=tk.SUNKEN, borderwidth=2)
        inset_frame.pack(fill=tk.X, padx=5, pady=5)

        inset_label_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        inset_label = tk.Label(
            inset_frame,
            text="Cropped Output Preview:",
            font=inset_label_font,
            bg="#1a1a1a",
            fg="#888888"
        )
        inset_label.pack(anchor=tk.W, padx=5, pady=(5, 2))

        self.crop_preview_canvas = tk.Canvas(
            inset_frame,
            bg="#000000",
            highlightthickness=0,
            width=500,
            height=375
        )
        self.crop_preview_canvas.pack(padx=5, pady=(0, 5))

    def _create_controls_panel(self, parent):
        """Create right panel with all controls."""
        controls_panel = tk.Frame(parent, bg="#2b2b2b")
        controls_panel.pack(fill=tk.BOTH, expand=True)

        # Make scrollable
        canvas = tk.Canvas(controls_panel, bg="#2b2b2b", highlightthickness=0, width=420)
        scrollbar = ttk.Scrollbar(controls_panel, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2b2b2b")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # CRITICAL: Add mousewheel scrolling support
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Store reference for keyboard shortcuts
        self.controls_canvas = canvas

        # Add all control sections (presets first - most important for quick access)
        self._create_presets_section(scrollable_frame)
        self._create_anchor_mode_section(scrollable_frame)
        self._create_zoom_section(scrollable_frame)
        self._create_output_dimensions_section(scrollable_frame)
        self._create_display_options_section(scrollable_frame)
        self._create_stats_section(scrollable_frame)

    def _create_anchor_mode_section(self, parent):
        """Create anchor mode selection and controls."""
        section_frame = self._create_section_frame(parent, "Anchor Mode")

        # Anchor mode dropdown
        mode_frame = tk.Frame(section_frame, bg="#2b2b2b")
        mode_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            mode_frame,
            text="Mode:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.anchor_mode_var = tk.StringVar(value=self.settings.get("manual_crop_anchor_mode", "center"))
        self.anchor_mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.anchor_mode_var,
            values=["center", "edge", "corner"],
            state="readonly",
            width=15
        )
        self.anchor_mode_combo.pack(side=tk.LEFT)
        self.anchor_mode_combo.bind("<<ComboboxSelected>>", self._on_anchor_mode_changed)

        tk.Label(
            mode_frame,
            text="← Choose how crop is anchored",
            bg="#2b2b2b",
            fg="#888888",
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Dynamic controls container (changes based on mode)
        self.anchor_controls_frame = tk.Frame(section_frame, bg="#2b2b2b")
        self.anchor_controls_frame.pack(fill=tk.X, pady=5)

        # Initialize controls for current mode
        self._update_anchor_controls()

    def _create_zoom_section(self, parent):
        """Create zoom controls."""
        section_frame = self._create_section_frame(parent, "Zoom")

        # Zoom slider
        zoom_frame = tk.Frame(section_frame, bg="#2b2b2b")
        zoom_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            zoom_frame,
            text="Zoom level:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W)

        self.zoom_var = tk.DoubleVar(value=self.settings.get("manual_crop_zoom", 1.0))

        slider_container = tk.Frame(zoom_frame, bg="#2b2b2b")
        slider_container.pack(fill=tk.X, pady=5)

        self.zoom_slider = tk.Scale(
            slider_container,
            from_=0.5,
            to=5.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.zoom_var,
            bg="#3a3a3a",
            fg="#ffffff",
            highlightthickness=0,
            troughcolor="#1a1a1a",
            activebackground="#00aaff",
            command=self._on_zoom_changed
        )
        self.zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.zoom_label = tk.Label(
            slider_container,
            text=f"{self.zoom_var.get():.1f}x",
            bg="#2b2b2b",
            fg="#00aaff",
            font=("Segoe UI", 10, "bold"),
            width=5
        )
        self.zoom_label.pack(side=tk.LEFT, padx=(10, 0))

        # Zoom to fit button
        fit_btn = tk.Button(
            zoom_frame,
            text="Auto Zoom to Fit",
            command=self._auto_zoom_to_fit,
            bg="#3a7ca5",
            fg="#ffffff",
            activebackground="#2a5c85",
            font=("Segoe UI", 9),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2"
        )
        fit_btn.pack(fill=tk.X, pady=(5, 0))

    def _create_output_dimensions_section(self, parent):
        """Create output box dimensions controls."""
        section_frame = self._create_section_frame(parent, "Output Dimensions")

        # Lock aspect ratio checkbox
        self.lock_aspect_var = tk.BooleanVar(value=self.settings.get("manual_crop_lock_aspect", True))
        lock_check = tk.Checkbutton(
            section_frame,
            text="Lock aspect ratio",
            variable=self.lock_aspect_var,
            bg="#2b2b2b",
            fg="#ffffff",
            selectcolor="#1a1a1a",
            activebackground="#2b2b2b",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            command=self._on_lock_aspect_changed
        )
        lock_check.pack(anchor=tk.W, pady=(0, 5))

        # Width spinbox
        width_frame = tk.Frame(section_frame, bg="#2b2b2b")
        width_frame.pack(fill=tk.X, pady=3)

        tk.Label(
            width_frame,
            text="Width:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9),
            width=8,
            anchor=tk.W
        ).pack(side=tk.LEFT)

        self.width_var = tk.IntVar(value=self.settings.get("manual_crop_box_width", 400))
        width_spinbox = tk.Spinbox(
            width_frame,
            from_=160,
            to=1920,
            textvariable=self.width_var,
            width=10,
            bg="#3a3a3a",
            fg="#ffffff",
            buttonbackground="#2a2a2a",
            command=self._on_width_changed
        )
        width_spinbox.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(
            width_frame,
            text="pixels",
            bg="#2b2b2b",
            fg="#888888",
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT)

        # Height spinbox
        height_frame = tk.Frame(section_frame, bg="#2b2b2b")
        height_frame.pack(fill=tk.X, pady=3)

        tk.Label(
            height_frame,
            text="Height:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9),
            width=8,
            anchor=tk.W
        ).pack(side=tk.LEFT)

        self.height_var = tk.IntVar(value=self.settings.get("manual_crop_box_height", 300))
        height_spinbox = tk.Spinbox(
            height_frame,
            from_=120,
            to=1080,
            textvariable=self.height_var,
            width=10,
            bg="#3a3a3a",
            fg="#ffffff",
            buttonbackground="#2a2a2a",
            command=self._on_height_changed
        )
        height_spinbox.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(
            height_frame,
            text="pixels",
            bg="#2b2b2b",
            fg="#888888",
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT)

        # Aspect ratio presets
        aspect_label = tk.Label(
            section_frame,
            text="Aspect ratio presets:",
            bg="#2b2b2b",
            fg="#888888",
            font=("Segoe UI", 8)
        )
        aspect_label.pack(anchor=tk.W, pady=(10, 2))

        aspect_frame = tk.Frame(section_frame, bg="#2b2b2b")
        aspect_frame.pack(fill=tk.X)

        aspect_ratios = [
            ("16:9", 16/9),
            ("4:3", 4/3),
            ("1:1", 1.0),
            ("21:9", 21/9),
            ("9:16", 9/16)  # Vertical/portrait
        ]

        for label, ratio in aspect_ratios:
            btn = tk.Button(
                aspect_frame,
                text=label,
                command=lambda r=ratio: self._apply_aspect_ratio(r),
                bg="#3a7ca5",
                fg="#ffffff",
                activebackground="#2a5c85",
                font=("Segoe UI", 8, "bold"),
                relief=tk.RAISED,
                bd=1,
                cursor="hand2"
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)

        # Size presets
        presets_label = tk.Label(
            section_frame,
            text="Size presets:",
            bg="#2b2b2b",
            fg="#888888",
            font=("Segoe UI", 8)
        )
        presets_label.pack(anchor=tk.W, pady=(8, 2))

        presets_frame = tk.Frame(section_frame, bg="#2b2b2b")
        presets_frame.pack(fill=tk.X)

        preset_sizes = [
            ("320×240", 320, 240),
            ("640×480", 640, 480),
            ("800×600", 800, 600),
            ("1280×720", 1280, 720)
        ]

        for label, w, h in preset_sizes:
            btn = tk.Button(
                presets_frame,
                text=label,
                command=lambda w=w, h=h: self._apply_dimension_preset(w, h),
                bg="#444444",
                fg="#ffffff",
                activebackground="#555555",
                font=("Segoe UI", 8),
                relief=tk.RAISED,
                bd=1,
                cursor="hand2"
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)

    def _create_display_options_section(self, parent):
        """Create display and overlay options."""
        section_frame = self._create_section_frame(parent, "Display Options")

        # Live update toggle
        self.live_update_var = tk.BooleanVar(value=True)
        live_check = tk.Checkbutton(
            section_frame,
            text="Live preview updates (uncheck to pause and improve performance)",
            variable=self.live_update_var,
            bg="#2b2b2b",
            fg="#ffffff",
            selectcolor="#1a1a1a",
            activebackground="#2b2b2b",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold")
        )
        live_check.pack(anchor=tk.W, pady=(0, 10))

        # Grid overlay dropdown
        grid_frame = tk.Frame(section_frame, bg="#2b2b2b")
        grid_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            grid_frame,
            text="Grid overlay:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.grid_overlay_var = tk.StringVar(value=self.settings.get("manual_crop_grid_overlay", "off"))
        grid_combo = ttk.Combobox(
            grid_frame,
            textvariable=self.grid_overlay_var,
            values=["off", "rule_of_thirds", "4x4", "custom"],
            state="readonly",
            width=15
        )
        grid_combo.pack(side=tk.LEFT)
        grid_combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

        # Show safe zones checkbox
        self.safe_zones_var = tk.BooleanVar(value=self.settings.get("manual_crop_show_safe_zones", False))
        safe_check = tk.Checkbutton(
            section_frame,
            text="Show safe zones (areas that might be cut off)",
            variable=self.safe_zones_var,
            bg="#2b2b2b",
            fg="#ffffff",
            selectcolor="#1a1a1a",
            activebackground="#2b2b2b",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            command=self._update_preview
        )
        safe_check.pack(anchor=tk.W, pady=5)

        # Preview opacity slider
        opacity_frame = tk.Frame(section_frame, bg="#2b2b2b")
        opacity_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            opacity_frame,
            text="Overlay opacity:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W)

        self.opacity_var = tk.DoubleVar(value=self.settings.get("manual_crop_preview_opacity", 0.7))

        opacity_slider_container = tk.Frame(opacity_frame, bg="#2b2b2b")
        opacity_slider_container.pack(fill=tk.X, pady=5)

        opacity_slider = tk.Scale(
            opacity_slider_container,
            from_=0.0,
            to=1.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.opacity_var,
            bg="#3a3a3a",
            fg="#ffffff",
            highlightthickness=0,
            troughcolor="#1a1a1a",
            activebackground="#00aaff",
            command=lambda v: self._update_preview()
        )
        opacity_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.opacity_label = tk.Label(
            opacity_slider_container,
            text=f"{int(self.opacity_var.get() * 100)}%",
            bg="#2b2b2b",
            fg="#00aaff",
            font=("Segoe UI", 10, "bold"),
            width=5
        )
        self.opacity_label.pack(side=tk.LEFT, padx=(10, 0))

    def _create_presets_section(self, parent):
        """Create crop presets management."""
        section_frame = self._create_section_frame(parent, "Crop Presets")

        # Preset dropdown
        preset_frame = tk.Frame(section_frame, bg="#2b2b2b")
        preset_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            preset_frame,
            text="Preset:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 8))

        presets = self.settings.get("manual_crop_presets", {})
        preset_names = list(presets.keys())

        self.preset_var = tk.StringVar(value=preset_names[0] if preset_names else "")
        self.preset_combo = ttk.Combobox(
            preset_frame,
            textvariable=self.preset_var,
            values=preset_names,
            state="readonly",
            width=20
        )
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Action buttons - simplified
        btn_frame = tk.Frame(section_frame, bg="#2b2b2b")
        btn_frame.pack(fill=tk.X, pady=5)

        load_btn = tk.Button(
            btn_frame,
            text="Load",
            command=self._load_preset,
            bg="#00aa00",
            fg="#ffffff",
            activebackground="#008800",
            font=("Segoe UI", 9, "bold"),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            width=10
        )
        load_btn.pack(side=tk.LEFT, padx=(0, 5))

        save_btn = tk.Button(
            btn_frame,
            text="Save As...",
            command=self._save_preset,
            bg="#3a7ca5",
            fg="#ffffff",
            activebackground="#2a5c85",
            font=("Segoe UI", 9),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2"
        )
        save_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        delete_btn = tk.Button(
            btn_frame,
            text="Delete",
            command=self._delete_preset,
            bg="#c53030",
            fg="#ffffff",
            activebackground="#9f2020",
            font=("Segoe UI", 9),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            width=10
        )
        delete_btn.pack(side=tk.LEFT)

    def _create_stats_section(self, parent):
        """Create real-time statistics display."""
        section_frame = self._create_section_frame(parent, "Real-time Statistics")

        # Stats text widget (read-only)
        self.stats_text = tk.Text(
            section_frame,
            height=8,
            bg="#1a1a1a",
            fg="#00ff00",
            font=("Consolas", 9),
            relief=tk.SUNKEN,
            borderwidth=2,
            state=tk.DISABLED
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Initialize stats
        self._update_stats()

    def _create_button_bar(self):
        """Create bottom button bar with action buttons."""
        # Keyboard shortcuts help text
        help_frame = tk.Frame(self, bg="#1a1a1a", relief=tk.SUNKEN, borderwidth=1)
        help_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 5))

        help_text = "Shortcuts: Ctrl+S=Save & Close | Esc=Cancel | Ctrl+R=Reset | Ctrl+D=Auto-detect"
        tk.Label(
            help_frame,
            text=help_text,
            bg="#1a1a1a",
            fg="#00aaff",
            font=("Segoe UI", 8),
            pady=3
        ).pack()

        button_bar = tk.Frame(self, bg="#2b2b2b", relief=tk.RIDGE, borderwidth=2)
        button_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 5))

        # Left side buttons
        reset_btn = tk.Button(
            button_bar,
            text="Reset to Defaults",
            command=self._reset_to_defaults,
            bg="#444444",
            fg="#ffffff",
            activebackground="#555555",
            font=("Segoe UI", 9),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            width=15
        )
        reset_btn.pack(side=tk.LEFT, padx=5, pady=5)

        auto_btn = tk.Button(
            button_bar,
            text="Auto-Detect Face",
            command=self._auto_detect_face,
            bg="#3a7ca5",
            fg="#ffffff",
            activebackground="#2a5c85",
            font=("Segoe UI", 9),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            width=15
        )
        auto_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Spacer
        tk.Label(button_bar, bg="#2b2b2b").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Right side buttons - Clear and simple
        cancel_btn = tk.Button(
            button_bar,
            text="Cancel",
            command=self._on_cancel,
            bg="#c53030",
            fg="#ffffff",
            activebackground="#9f2020",
            font=("Segoe UI", 10),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            width=12
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 5), pady=5)

        save_and_close_btn = tk.Button(
            button_bar,
            text="💾 Save & Close",
            command=self._save_and_close,
            bg="#00aa00",
            fg="#ffffff",
            activebackground="#008800",
            font=("Segoe UI", 11, "bold"),
            relief=tk.RAISED,
            bd=3,
            cursor="hand2",
            width=16
        )
        save_and_close_btn.pack(side=tk.RIGHT, padx=(5, 0), pady=5)

    def _create_section_frame(self, parent, title):
        """Create a section frame with title."""
        section_outer = tk.Frame(parent, bg="#2b2b2b")
        section_outer.pack(fill=tk.X, pady=(10, 0))

        title_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        title_label = tk.Label(
            section_outer,
            text=title,
            font=title_font,
            bg="#2b2b2b",
            fg="#00aaff"
        )
        title_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

        section_frame = tk.Frame(section_outer, bg="#2b2b2b", relief=tk.GROOVE, borderwidth=1)
        section_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # Add padding inside
        padded_frame = tk.Frame(section_frame, bg="#2b2b2b")
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        return padded_frame

    # ===== CAMERA MANAGEMENT =====

    def _initialize_camera(self, generation=None):
        """Initialize camera feed."""
        current_generation = getattr(self, "_camera_generation", 0)
        if generation is None:
            generation = current_generation
        if generation != current_generation or not CV2_AVAILABLE:
            return
        self._camera_init_timer = None

        try:
            device_index = self.settings.get("camera_device_index", 0)
            self.camera = cv2.VideoCapture(device_index)

            if not self.camera.isOpened():
                messagebox.showerror(
                    "Camera Error",
                    f"Could not open camera device {device_index}",
                    parent=self
                )
                return

            # Start update loop
            self._update_camera_feed(generation)

        except Exception as e:
            messagebox.showerror(
                "Camera Error",
                f"Failed to initialize camera: {e}",
                parent=self
            )

    def _update_camera_feed(self, generation=None):
        """Update camera feed and preview."""
        current_generation = getattr(self, "_camera_generation", 0)
        if generation is None:
            generation = current_generation
        if generation != current_generation or not self.camera or not self.camera.isOpened():
            return

        try:
            ret, frame = self.camera.read()
            if ret:
                self.current_frame = frame
                self._update_preview()

            # Schedule next update (30 FPS)
            self._schedule_camera_update(33, generation)

        except Exception:
            pass

    def _schedule_camera_update(self, delay_ms, generation):
        if getattr(self, "_closed", False):
            return
        self._timers.schedule(
            "camera-feed",
            delay_ms,
            lambda: self._update_camera_feed(generation),
        )
        self.camera_update_timer = self._timers.callback_id("camera-feed")

    def _update_preview(self):
        """Update preview canvas with current frame and crop overlay."""
        if self.current_frame is None or not PIL_AVAILABLE:
            return

        # Check if live updates are enabled
        if not getattr(self, 'live_update_var', None) or not self.live_update_var.get():
            return

        try:
            frame = self.current_frame.copy()

            # Flip if enabled
            if self.settings.get("camera_flip_horizontal", True):
                frame = cv2.flip(frame, 1)

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_height, frame_width = frame_rgb.shape[:2]

            # Calculate crop region
            crop_rect = self._calculate_crop_region(frame_width, frame_height)
            x1, y1, x2, y2 = crop_rect

            # Create PIL image for drawing
            pil_image = Image.fromarray(frame_rgb)
            draw = ImageDraw.Draw(pil_image, 'RGBA')

            # Draw crop rectangle
            opacity = int(self.opacity_var.get() * 255)
            draw.rectangle([x1, y1, x2, y2], outline=(0, 255, 0, 255), width=3)

            # Draw dimmed overlay outside crop area
            overlay_color = (0, 0, 0, int(opacity * 0.6))
            if x1 > 0:  # Left side
                draw.rectangle([0, 0, x1, frame_height], fill=overlay_color)
            if y1 > 0:  # Top side
                draw.rectangle([0, 0, frame_width, y1], fill=overlay_color)
            if x2 < frame_width:  # Right side
                draw.rectangle([x2, 0, frame_width, frame_height], fill=overlay_color)
            if y2 < frame_height:  # Bottom side
                draw.rectangle([0, y2, frame_width, frame_height], fill=overlay_color)

            # Draw grid overlay if enabled
            grid_mode = self.grid_overlay_var.get()
            if grid_mode != "off":
                self._draw_grid_overlay(draw, x1, y1, x2, y2, grid_mode)

            # Draw anchor point indicator
            self._draw_anchor_indicator(draw, frame_width, frame_height, x1, y1, x2, y2)

            # Resize to fit canvas
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            if canvas_width > 1 and canvas_height > 1:
                pil_image.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)

            # Update preview canvas
            self.preview_photo = ImageTk.PhotoImage(pil_image)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                canvas_width // 2,
                canvas_height // 2,
                image=self.preview_photo,
                anchor=tk.CENTER
            )

            # Update crop preview inset
            self._update_crop_preview(frame_rgb, crop_rect)

            # Update stats
            self._update_stats()

        except Exception as e:
            pass

    def _update_crop_preview(self, frame_rgb, crop_rect):
        """Update the crop preview inset showing actual output."""
        if not PIL_AVAILABLE:
            return

        try:
            x1, y1, x2, y2 = crop_rect

            # Crop the region
            cropped = frame_rgb[y1:y2, x1:x2]

            if cropped.size == 0:
                return

            # Resize to output dimensions
            box_w = self.width_var.get()
            box_h = self.height_var.get()
            cropped_resized = cv2.resize(cropped, (box_w, box_h), interpolation=cv2.INTER_LINEAR)

            # Convert to PIL and display
            pil_crop = Image.fromarray(cropped_resized)

            # Resize to fit inset canvas
            inset_width = self.crop_preview_canvas.winfo_width()
            inset_height = self.crop_preview_canvas.winfo_height()
            if inset_width > 1 and inset_height > 1:
                pil_crop.thumbnail((inset_width, inset_height), Image.Resampling.LANCZOS)

            self.crop_preview_photo = ImageTk.PhotoImage(pil_crop)
            self.crop_preview_canvas.delete("all")
            self.crop_preview_canvas.create_image(
                inset_width // 2,
                inset_height // 2,
                image=self.crop_preview_photo,
                anchor=tk.CENTER
            )

        except Exception:
            pass

    def _calculate_crop_region(self, frame_width, frame_height):
        """Calculate crop rectangle based on current settings."""
        # Sync live UI values back to settings for shared helper
        self.settings.update({
            "manual_crop_anchor_mode": self.anchor_mode_var.get(),
            "manual_crop_zoom": self.zoom_var.get(),
            "manual_crop_box_width": self.width_var.get(),
            "manual_crop_box_height": self.height_var.get(),
        })

        return calculate_crop_region(self.settings, frame_width, frame_height)

    def _draw_grid_overlay(self, draw, x1, y1, x2, y2, grid_mode):
        """Draw grid overlay on crop region."""
        grid_color = (255, 255, 255, 128)

        if grid_mode == "rule_of_thirds":
            # Draw thirds lines
            third_w = (x2 - x1) // 3
            third_h = (y2 - y1) // 3

            # Vertical lines
            draw.line([x1 + third_w, y1, x1 + third_w, y2], fill=grid_color, width=1)
            draw.line([x1 + 2 * third_w, y1, x1 + 2 * third_w, y2], fill=grid_color, width=1)

            # Horizontal lines
            draw.line([x1, y1 + third_h, x2, y1 + third_h], fill=grid_color, width=1)
            draw.line([x1, y1 + 2 * third_h, x2, y1 + 2 * third_h], fill=grid_color, width=1)

        elif grid_mode == "4x4":
            # Draw 4x4 grid
            quarter_w = (x2 - x1) // 4
            quarter_h = (y2 - y1) // 4

            for i in range(1, 4):
                # Vertical lines
                draw.line([x1 + i * quarter_w, y1, x1 + i * quarter_w, y2], fill=grid_color, width=1)
                # Horizontal lines
                draw.line([x1, y1 + i * quarter_h, x2, y1 + i * quarter_h], fill=grid_color, width=1)

    def _draw_anchor_indicator(self, draw, frame_width, frame_height, x1, y1, x2, y2):
        """Draw anchor point indicator."""
        anchor_mode = self.anchor_mode_var.get()
        indicator_color = (255, 0, 0, 255)
        indicator_size = 10

        if anchor_mode == "center":
            offset_x = float(self.settings.get("manual_crop_center_offset_x", 0.0))
            offset_y = float(self.settings.get("manual_crop_center_offset_y", 0.0))

            center_x = frame_width // 2 + int(offset_x * frame_width)
            center_y = frame_height // 2 + int(offset_y * frame_height)

            # Draw crosshair
            draw.line([center_x - indicator_size, center_y, center_x + indicator_size, center_y],
                     fill=indicator_color, width=2)
            draw.line([center_x, center_y - indicator_size, center_x, center_y + indicator_size],
                     fill=indicator_color, width=2)

        elif anchor_mode == "edge":
            edge = self.settings.get("manual_crop_edge", "top")

            if edge == "top":
                anchor_x, anchor_y = (x1 + x2) // 2, y1
            elif edge == "bottom":
                anchor_x, anchor_y = (x1 + x2) // 2, y2
            elif edge == "left":
                anchor_x, anchor_y = x1, (y1 + y2) // 2
            else:  # right
                anchor_x, anchor_y = x2, (y1 + y2) // 2

            # Draw small circle
            draw.ellipse(
                [anchor_x - indicator_size//2, anchor_y - indicator_size//2,
                 anchor_x + indicator_size//2, anchor_y + indicator_size//2],
                fill=indicator_color
            )

        elif anchor_mode == "corner":
            corner = self.settings.get("manual_crop_corner", "top_left")

            if corner == "top_left":
                anchor_x, anchor_y = x1, y1
            elif corner == "top_right":
                anchor_x, anchor_y = x2, y1
            elif corner == "bottom_left":
                anchor_x, anchor_y = x1, y2
            else:  # bottom_right
                anchor_x, anchor_y = x2, y2

            # Draw small square
            draw.rectangle(
                [anchor_x - indicator_size//2, anchor_y - indicator_size//2,
                 anchor_x + indicator_size//2, anchor_y + indicator_size//2],
                fill=indicator_color
            )

    def _update_stats(self):
        """Update real-time statistics display."""
        if self.current_frame is None:
            return

        try:
            frame_height, frame_width = self.current_frame.shape[:2]

            # Calculate crop region
            crop_rect = self._calculate_crop_region(frame_width, frame_height)
            x1, y1, x2, y2 = crop_rect

            crop_width = x2 - x1
            crop_height = y2 - y1

            box_width = self.width_var.get()
            box_height = self.height_var.get()

            zoom = self.zoom_var.get()

            # Calculate aspect ratios
            crop_aspect = crop_width / crop_height if crop_height > 0 else 0
            box_aspect = box_width / box_height if box_height > 0 else 0

            # Calculate pixels lost
            frame_area = frame_width * frame_height
            crop_area = crop_width * crop_height
            pixels_lost_pct = ((frame_area - crop_area) / frame_area * 100) if frame_area > 0 else 0

            # Build stats text
            stats_lines = [
                f"Source Frame: {frame_width} × {frame_height}",
                f"Crop Region: {crop_width} × {crop_height} @ ({x1}, {y1})",
                f"Output Size: {box_width} × {box_height}",
                f"",
                f"Zoom Level: {zoom:.1f}x ({int(zoom * 100)}%)",
                f"Crop Aspect: {crop_aspect:.2f}:1",
                f"Output Aspect: {box_aspect:.2f}:1",
                f"",
                f"Area Cropped: {pixels_lost_pct:.1f}% of frame",
                f"Anchor Mode: {self.anchor_mode_var.get().upper()}",
            ]

            stats_text = "\n".join(stats_lines)

            # Update text widget
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete("1.0", tk.END)
            self.stats_text.insert("1.0", stats_text)
            self.stats_text.config(state=tk.DISABLED)

        except Exception:
            pass

    # ===== EVENT HANDLERS =====

    def _on_anchor_mode_changed(self, event=None):
        """Handle anchor mode change."""
        # Save current mode to settings
        self.settings["manual_crop_anchor_mode"] = self.anchor_mode_var.get()

        # Mark as changed
        self._mark_as_changed()

        # Update controls
        self._update_anchor_controls()

        # Update preview
        self._update_preview()

    def _update_anchor_controls(self):
        """Update anchor controls based on selected mode."""
        # Clear existing controls
        for widget in self.anchor_controls_frame.winfo_children():
            widget.destroy()

        mode = self.anchor_mode_var.get()

        if mode == "center":
            # Center mode: X/Y offset sliders
            self._create_center_controls(self.anchor_controls_frame)
        elif mode == "edge":
            # Edge mode: Edge selection + offset slider
            self._create_edge_controls(self.anchor_controls_frame)
        elif mode == "corner":
            # Corner mode: Corner selection + X/Y expansion
            self._create_corner_controls(self.anchor_controls_frame)

    def _create_center_controls(self, parent):
        """Create controls for center anchor mode."""
        # X offset slider
        x_frame = tk.Frame(parent, bg="#2b2b2b")
        x_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            x_frame,
            text="X Offset:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W)

        x_offset_var = tk.DoubleVar(value=self.settings.get("manual_crop_center_offset_x", 0.0))

        x_slider_container = tk.Frame(x_frame, bg="#2b2b2b")
        x_slider_container.pack(fill=tk.X, pady=5)

        x_slider = tk.Scale(
            x_slider_container,
            from_=-0.5,
            to=0.5,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            variable=x_offset_var,
            bg="#3a3a3a",
            fg="#ffffff",
            highlightthickness=0,
            troughcolor="#1a1a1a",
            activebackground="#00aaff",
            command=lambda v: self._on_center_offset_changed('x', v)
        )
        x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        x_label = tk.Label(
            x_slider_container,
            text=f"{x_offset_var.get():+.0%}",
            bg="#2b2b2b",
            fg="#00aaff",
            font=("Segoe UI", 9, "bold"),
            width=7
        )
        x_label.pack(side=tk.LEFT, padx=(10, 0))

        # Store reference for update
        self._center_x_label = x_label
        self._center_x_var = x_offset_var

        # Y offset slider
        y_frame = tk.Frame(parent, bg="#2b2b2b")
        y_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            y_frame,
            text="Y Offset:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W)

        y_offset_var = tk.DoubleVar(value=self.settings.get("manual_crop_center_offset_y", 0.0))

        y_slider_container = tk.Frame(y_frame, bg="#2b2b2b")
        y_slider_container.pack(fill=tk.X, pady=5)

        y_slider = tk.Scale(
            y_slider_container,
            from_=-0.5,
            to=0.5,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            variable=y_offset_var,
            bg="#3a3a3a",
            fg="#ffffff",
            highlightthickness=0,
            troughcolor="#1a1a1a",
            activebackground="#00aaff",
            command=lambda v: self._on_center_offset_changed('y', v)
        )
        y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        y_label = tk.Label(
            y_slider_container,
            text=f"{y_offset_var.get():+.0%}",
            bg="#2b2b2b",
            fg="#00aaff",
            font=("Segoe UI", 9, "bold"),
            width=7
        )
        y_label.pack(side=tk.LEFT, padx=(10, 0))

        # Store reference for update
        self._center_y_label = y_label
        self._center_y_var = y_offset_var

    def _create_edge_controls(self, parent):
        """Create controls for edge anchor mode."""
        # Edge selection dropdown
        edge_frame = tk.Frame(parent, bg="#2b2b2b")
        edge_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            edge_frame,
            text="Edge:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        edge_var = tk.StringVar(value=self.settings.get("manual_crop_edge", "top"))
        edge_combo = ttk.Combobox(
            edge_frame,
            textvariable=edge_var,
            values=["top", "bottom", "left", "right"],
            state="readonly",
            width=10
        )
        edge_combo.pack(side=tk.LEFT)
        edge_combo.bind("<<ComboboxSelected>>", lambda e: self._on_edge_changed(edge_var.get()))

        self._edge_var = edge_var

        # Edge offset slider
        offset_frame = tk.Frame(parent, bg="#2b2b2b")
        offset_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            offset_frame,
            text="Perpendicular Offset:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W)

        offset_var = tk.DoubleVar(value=self.settings.get("manual_crop_edge_offset", 0.0))

        offset_slider_container = tk.Frame(offset_frame, bg="#2b2b2b")
        offset_slider_container.pack(fill=tk.X, pady=5)

        offset_slider = tk.Scale(
            offset_slider_container,
            from_=-1.0,
            to=1.0,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            variable=offset_var,
            bg="#3a3a3a",
            fg="#ffffff",
            highlightthickness=0,
            troughcolor="#1a1a1a",
            activebackground="#00aaff",
            command=lambda v: self._on_edge_offset_changed(v)
        )
        offset_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        offset_label = tk.Label(
            offset_slider_container,
            text=f"{offset_var.get():+.0%}",
            bg="#2b2b2b",
            fg="#00aaff",
            font=("Segoe UI", 9, "bold"),
            width=7
        )
        offset_label.pack(side=tk.LEFT, padx=(10, 0))

        self._edge_offset_label = offset_label
        self._edge_offset_var = offset_var

    def _create_corner_controls(self, parent):
        """Create controls for corner anchor mode."""
        # Corner selection dropdown
        corner_frame = tk.Frame(parent, bg="#2b2b2b")
        corner_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            corner_frame,
            text="Corner:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        corner_var = tk.StringVar(value=self.settings.get("manual_crop_corner", "top_left"))
        corner_combo = ttk.Combobox(
            corner_frame,
            textvariable=corner_var,
            values=["top_left", "top_right", "bottom_left", "bottom_right"],
            state="readonly",
            width=15
        )
        corner_combo.pack(side=tk.LEFT)
        corner_combo.bind("<<ComboboxSelected>>", lambda e: self._on_corner_changed(corner_var.get()))

        self._corner_var = corner_var

        # X expansion slider
        x_frame = tk.Frame(parent, bg="#2b2b2b")
        x_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            x_frame,
            text="Horizontal Expansion:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W)

        expand_x_var = tk.DoubleVar(value=self.settings.get("manual_crop_corner_expand_x", 1.0))

        x_slider_container = tk.Frame(x_frame, bg="#2b2b2b")
        x_slider_container.pack(fill=tk.X, pady=5)

        x_slider = tk.Scale(
            x_slider_container,
            from_=0.0,
            to=5.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=expand_x_var,
            bg="#3a3a3a",
            fg="#ffffff",
            highlightthickness=0,
            troughcolor="#1a1a1a",
            activebackground="#00aaff",
            command=lambda v: self._on_corner_expand_changed('x', v)
        )
        x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        x_label = tk.Label(
            x_slider_container,
            text=f"{expand_x_var.get():.1f}x",
            bg="#2b2b2b",
            fg="#00aaff",
            font=("Segoe UI", 9, "bold"),
            width=7
        )
        x_label.pack(side=tk.LEFT, padx=(10, 0))

        self._corner_expand_x_label = x_label
        self._corner_expand_x_var = expand_x_var

        # Y expansion slider
        y_frame = tk.Frame(parent, bg="#2b2b2b")
        y_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            y_frame,
            text="Vertical Expansion:",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W)

        expand_y_var = tk.DoubleVar(value=self.settings.get("manual_crop_corner_expand_y", 1.0))

        y_slider_container = tk.Frame(y_frame, bg="#2b2b2b")
        y_slider_container.pack(fill=tk.X, pady=5)

        y_slider = tk.Scale(
            y_slider_container,
            from_=0.0,
            to=5.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=expand_y_var,
            bg="#3a3a3a",
            fg="#ffffff",
            highlightthickness=0,
            troughcolor="#1a1a1a",
            activebackground="#00aaff",
            command=lambda v: self._on_corner_expand_changed('y', v)
        )
        y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        y_label = tk.Label(
            y_slider_container,
            text=f"{expand_y_var.get():.1f}x",
            bg="#2b2b2b",
            fg="#00aaff",
            font=("Segoe UI", 9, "bold"),
            width=7
        )
        y_label.pack(side=tk.LEFT, padx=(10, 0))

        self._corner_expand_y_label = y_label
        self._corner_expand_y_var = expand_y_var

    def _on_center_offset_changed(self, axis, value):
        """Handle center offset change."""
        value = float(value)
        self.settings[f"manual_crop_center_offset_{axis}"] = value
        self._mark_as_changed()

        if axis == 'x' and hasattr(self, '_center_x_label'):
            self._center_x_label.config(text=f"{value:+.0%}")
        elif axis == 'y' and hasattr(self, '_center_y_label'):
            self._center_y_label.config(text=f"{value:+.0%}")

        self._update_preview()

    def _on_edge_changed(self, edge):
        """Handle edge selection change."""
        self.settings["manual_crop_edge"] = edge
        self._mark_as_changed()
        self._update_preview()

    def _on_edge_offset_changed(self, value):
        """Handle edge offset change."""
        value = float(value)
        self.settings["manual_crop_edge_offset"] = value
        self._mark_as_changed()

        if hasattr(self, '_edge_offset_label'):
            self._edge_offset_label.config(text=f"{value:+.0%}")

        self._update_preview()

    def _on_corner_changed(self, corner):
        """Handle corner selection change."""
        self.settings["manual_crop_corner"] = corner
        self._mark_as_changed()
        self._update_preview()

    def _on_corner_expand_changed(self, axis, value):
        """Handle corner expansion change."""
        value = float(value)
        self.settings[f"manual_crop_corner_expand_{axis}"] = value
        self._mark_as_changed()

        if axis == 'x' and hasattr(self, '_corner_expand_x_label'):
            self._corner_expand_x_label.config(text=f"{value:.1f}x")
        elif axis == 'y' and hasattr(self, '_corner_expand_y_label'):
            self._corner_expand_y_label.config(text=f"{value:.1f}x")

        self._update_preview()

    def _on_zoom_changed(self, value):
        """Handle zoom slider change."""
        value = float(value)
        self.settings["manual_crop_zoom"] = value
        self._mark_as_changed()
        self.zoom_label.config(text=f"{value:.1f}x")
        self._update_preview()

    def _on_lock_aspect_changed(self):
        """Handle lock aspect ratio checkbox."""
        self.settings["manual_crop_lock_aspect"] = self.lock_aspect_var.get()
        self._mark_as_changed()

    def _on_width_changed(self):
        """Handle width spinbox change."""
        width = self.width_var.get()
        self.settings["manual_crop_box_width"] = width
        self._mark_as_changed()

        if self.lock_aspect_var.get():
            # Adjust height to maintain aspect ratio
            aspect = self.width_var.get() / self.height_var.get() if self.height_var.get() > 0 else 1.0
            new_height = int(width / aspect)
            self.height_var.set(new_height)
            self.settings["manual_crop_box_height"] = new_height

        self._update_preview()

    def _on_height_changed(self):
        """Handle height spinbox change."""
        height = self.height_var.get()
        self.settings["manual_crop_box_height"] = height
        self._mark_as_changed()

        if self.lock_aspect_var.get():
            # Adjust width to maintain aspect ratio
            aspect = self.width_var.get() / self.height_var.get() if self.height_var.get() > 0 else 1.0
            new_width = int(height * aspect)
            self.width_var.set(new_width)
            self.settings["manual_crop_box_width"] = new_width

        self._update_preview()

    def _apply_dimension_preset(self, width, height):
        """Apply a dimension preset."""
        self.width_var.set(width)
        self.height_var.set(height)
        self.settings["manual_crop_box_width"] = width
        self.settings["manual_crop_box_height"] = height
        self._mark_as_changed()
        self._update_preview()

    def _apply_aspect_ratio(self, ratio):
        """Apply an aspect ratio to current dimensions."""
        # Keep width, adjust height to match ratio
        current_width = self.width_var.get()
        new_height = int(current_width / ratio)

        # Clamp to valid range
        new_height = max(120, min(1080, new_height))

        # If height is out of range, adjust width instead
        if new_height != int(current_width / ratio):
            new_width = int(new_height * ratio)
            new_width = max(160, min(1920, new_width))
            self.width_var.set(new_width)

        self.height_var.set(new_height)
        self.settings["manual_crop_box_width"] = self.width_var.get()
        self.settings["manual_crop_box_height"] = self.height_var.get()
        self._mark_as_changed()
        self._update_preview()

    def _auto_zoom_to_fit(self):
        """Auto-calculate zoom to fill box exactly."""
        if self.current_frame is None:
            return

        frame_height, frame_width = self.current_frame.shape[:2]
        box_width = self.width_var.get()
        box_height = self.height_var.get()

        # Calculate zoom needed to fit box
        zoom_x = frame_width / box_width
        zoom_y = frame_height / box_height
        zoom = min(zoom_x, zoom_y)  # Fit to smallest dimension

        # Clamp to valid range
        zoom = max(0.5, min(5.0, zoom))

        self.zoom_var.set(zoom)
        self.settings["manual_crop_zoom"] = zoom
        self._mark_as_changed()
        self._update_preview()

    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        if not messagebox.askyesno(
            "Reset to Defaults",
            "This will reset all crop settings to defaults. Continue?",
            parent=self
        ):
            return

        from ..settings.defaults import DEFAULT_SETTINGS

        # Reset all manual_crop settings
        for key in DEFAULT_SETTINGS:
            if key.startswith("manual_crop_"):
                self.settings[key] = DEFAULT_SETTINGS[key]

        # Update UI
        self.anchor_mode_var.set(self.settings["manual_crop_anchor_mode"])
        self.zoom_var.set(self.settings["manual_crop_zoom"])
        self.width_var.set(self.settings["manual_crop_box_width"])
        self.height_var.set(self.settings["manual_crop_box_height"])
        self.grid_overlay_var.set(self.settings["manual_crop_grid_overlay"])
        self.safe_zones_var.set(self.settings["manual_crop_show_safe_zones"])
        self.lock_aspect_var.set(self.settings["manual_crop_lock_aspect"])
        self.opacity_var.set(self.settings["manual_crop_preview_opacity"])

        self._mark_as_changed()
        self._update_anchor_controls()
        self._update_preview()

    def _auto_detect_face(self):
        """Use face detection to suggest optimal crop."""
        if not CV2_AVAILABLE or self.current_frame is None:
            messagebox.showinfo(
                "Face Detection",
                "Face detection requires OpenCV and a camera feed.",
                parent=self
            )
            return

        try:
            # Use simple face detection
            frame = self.current_frame.copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Load face cascade
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)

            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

            if len(faces) == 0:
                messagebox.showinfo(
                    "No Face Detected",
                    "Could not detect a face in the current frame.",
                    parent=self
                )
                return

            # Use largest face
            face = max(faces, key=lambda r: r[2] * r[3])
            x, y, w, h = face

            # Set center mode with offsets
            frame_height, frame_width = frame.shape[:2]
            center_x = x + w // 2
            center_y = y + int(h * 0.65)  # Slightly lower to include chin

            offset_x = (center_x - frame_width // 2) / frame_width
            offset_y = (center_y - frame_height // 2) / frame_height

            # Clamp offsets
            offset_x = max(-0.5, min(0.5, offset_x))
            offset_y = max(-0.5, min(0.5, offset_y))

            # Calculate zoom (aim for face to fill ~60% of box)
            box_width = self.width_var.get()
            box_height = self.height_var.get()
            zoom_x = (w * 1.5) / box_width  # 1.5x face width
            zoom_y = (h * 1.6) / box_height  # 1.6x face height
            zoom = max(zoom_x, zoom_y)
            zoom = max(0.5, min(5.0, zoom))

            # Apply settings
            self.anchor_mode_var.set("center")
            self.settings["manual_crop_anchor_mode"] = "center"
            self.settings["manual_crop_center_offset_x"] = offset_x
            self.settings["manual_crop_center_offset_y"] = offset_y
            self.settings["manual_crop_zoom"] = zoom
            self.zoom_var.set(zoom)

            self._mark_as_changed()
            self._update_anchor_controls()
            self._update_preview()

            messagebox.showinfo(
                "Face Detected",
                f"Crop adjusted to center on detected face.\n\n"
                f"Offset: ({offset_x:+.1%}, {offset_y:+.1%})\n"
                f"Zoom: {zoom:.1f}x",
                parent=self
            )

        except Exception as e:
            messagebox.showerror(
                "Face Detection Error",
                f"Failed to detect face: {e}",
                parent=self
            )

    def _test_in_popup(self):
        """Test the current crop in a preview popup."""
        messagebox.showinfo(
            "Test Preview",
            "Test preview will be implemented in the full application.\n\n"
            "This would show how the crop looks in the actual prompt dialog.",
            parent=self
        )

    def _load_preset(self):
        """Load selected preset into the UI and immediately save to disk."""
        preset_name = self.preset_var.get()
        if not preset_name:
            messagebox.showwarning("No Preset Selected", "Please select a preset first.", parent=self)
            return

        presets = self.settings.get("manual_crop_presets", {})
        if preset_name not in presets:
            messagebox.showerror("Preset Not Found", f"Preset '{preset_name}' not found.", parent=self)
            return

        preset = presets[preset_name]

        # Apply preset settings
        self.settings["manual_crop_anchor_mode"] = preset.get("anchor_mode", "center")
        self.settings["manual_crop_zoom"] = preset.get("zoom", 1.0)

        if "box_width" in preset:
            self.settings["manual_crop_box_width"] = preset["box_width"]
            self.width_var.set(preset["box_width"])
        if "box_height" in preset:
            self.settings["manual_crop_box_height"] = preset["box_height"]
            self.height_var.set(preset["box_height"])

        # Mode-specific settings
        if preset.get("anchor_mode") == "center":
            self.settings["manual_crop_center_offset_x"] = preset.get("center_offset_x", 0.0)
            self.settings["manual_crop_center_offset_y"] = preset.get("center_offset_y", 0.0)
        elif preset.get("anchor_mode") == "edge":
            self.settings["manual_crop_edge"] = preset.get("edge", "top")
            self.settings["manual_crop_edge_offset"] = preset.get("edge_offset", 0.0)
        elif preset.get("anchor_mode") == "corner":
            self.settings["manual_crop_corner"] = preset.get("corner", "top_left")
            self.settings["manual_crop_corner_expand_x"] = preset.get("corner_expand_x", 1.0)
            self.settings["manual_crop_corner_expand_y"] = preset.get("corner_expand_y", 1.0)

        # Update UI
        self.anchor_mode_var.set(self.settings["manual_crop_anchor_mode"])
        self.zoom_var.set(self.settings["manual_crop_zoom"])

        self._update_anchor_controls()
        self._update_preview()

        # AUTOMATICALLY SAVE TO DISK - no extra step needed!
        if self._save_to_disk():
            messagebox.showinfo(
                "Preset Loaded",
                f"✓ Preset '{preset_name}' loaded and saved to disk successfully!",
                parent=self
            )

    def _save_preset(self):
        """Save current settings as a preset and persist to disk."""
        from tkinter import simpledialog

        preset_name = simpledialog.askstring(
            "Save Preset",
            "Enter a name for this preset:",
            parent=self
        )

        if not preset_name:
            return

        # Build preset dict
        preset = {
            "anchor_mode": self.settings["manual_crop_anchor_mode"],
            "zoom": self.settings["manual_crop_zoom"],
            "box_width": self.settings["manual_crop_box_width"],
            "box_height": self.settings["manual_crop_box_height"],
        }

        # Add mode-specific settings
        if self.settings["manual_crop_anchor_mode"] == "center":
            preset["center_offset_x"] = self.settings["manual_crop_center_offset_x"]
            preset["center_offset_y"] = self.settings["manual_crop_center_offset_y"]
        elif self.settings["manual_crop_anchor_mode"] == "edge":
            preset["edge"] = self.settings["manual_crop_edge"]
            preset["edge_offset"] = self.settings["manual_crop_edge_offset"]
        elif self.settings["manual_crop_anchor_mode"] == "corner":
            preset["corner"] = self.settings["manual_crop_corner"]
            preset["corner_expand_x"] = self.settings["manual_crop_corner_expand_x"]
            preset["corner_expand_y"] = self.settings["manual_crop_corner_expand_y"]

        # Save to presets
        if "manual_crop_presets" not in self.settings:
            self.settings["manual_crop_presets"] = {}

        self.settings["manual_crop_presets"][preset_name] = preset

        # Update preset combo
        presets = list(self.settings["manual_crop_presets"].keys())
        self.preset_combo.config(values=presets)
        self.preset_var.set(preset_name)

        # AUTOMATICALLY SAVE TO DISK
        if self._save_to_disk():
            messagebox.showinfo(
                "Preset Saved",
                f"✓ Preset '{preset_name}' saved to disk successfully!",
                parent=self
            )

    def _delete_preset(self):
        """Delete selected preset and persist to disk."""
        preset_name = self.preset_var.get()
        if not preset_name:
            return

        # Don't allow deleting default presets
        from ..settings.defaults import DEFAULT_SETTINGS
        if preset_name in DEFAULT_SETTINGS.get("manual_crop_presets", {}):
            messagebox.showerror(
                "Cannot Delete",
                "Cannot delete default presets.",
                parent=self
            )
            return

        if not messagebox.askyesno(
            "Delete Preset",
            f"Delete preset '{preset_name}'?",
            parent=self
        ):
            return

        del self.settings["manual_crop_presets"][preset_name]

        # Update preset combo
        presets = list(self.settings["manual_crop_presets"].keys())
        self.preset_combo.config(values=presets)
        self.preset_var.set(presets[0] if presets else "")

        # AUTOMATICALLY SAVE TO DISK
        if self._save_to_disk():
            messagebox.showinfo(
                "Preset Deleted",
                f"✓ Preset '{preset_name}' deleted and saved to disk!",
                parent=self
            )

    def _mark_as_changed(self):
        """Mark settings as having unsaved changes and update window title."""
        if not self.has_unsaved_changes:
            self.has_unsaved_changes = True
            self.title("Manual Crop Adjustment - Live Preview *")

    def _save_to_disk(self):
        """Save all manual_crop settings to disk and update window state."""
        try:
            # Extract all manual_crop settings from working copy
            manual_crop_settings = {}
            for key in self.settings:
                if key.startswith("manual_crop_"):
                    manual_crop_settings[key] = self.settings[key]

            # Write a candidate document first. The parent and editor state are
            # updated only after the durable write succeeds.
            candidate = dict(self.original_settings)
            candidate.update(manual_crop_settings)
            persist = getattr(self, "persist_settings", None) or save_settings
            result = persist(candidate)
            if not result:
                messagebox.showerror(
                    "Save Error",
                    getattr(result, "error", None) or "Crop settings could not be written durably.",
                    parent=self,
                )
                return False

            committed = getattr(result, "committed_settings", None)
            committed_crop = (
                {key: value for key, value in committed.items() if key.startswith("manual_crop_")}
                if isinstance(committed, dict)
                else manual_crop_settings
            )
            for key, value in committed_crop.items():
                self.original_settings[key] = value
            if callable(self.on_settings_updated):
                self.on_settings_updated(committed_crop)

            # Mark as saved
            self.has_unsaved_changes = False
            self.title("Manual Crop Adjustment - Live Preview")

            return True

        except Exception as e:
            messagebox.showerror(
                "Save Error",
                f"Failed to save settings to disk:\n{e}",
                parent=self
            )
            return False

    def _save_and_close(self):
        """Save settings to disk and close window."""
        if self._save_to_disk():
            # Show brief confirmation
            messagebox.showinfo(
                "Settings Saved",
                "✓ Crop settings saved to disk successfully!",
                parent=self
            )
            # Close window
            self._cleanup()
            self.destroy()

    def _on_cancel(self):
        """Cancel and close without applying."""
        # Check if there are unsaved changes
        if self.has_unsaved_changes:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes.\n\nSave before closing?",
                parent=self
            )
            if response is None:  # Cancel button
                return
            elif response:  # Yes - save
                if not self._save_to_disk():
                    return  # Save failed, don't close

        # Close window
        self._cleanup()
        self.destroy()

    def _cleanup(self):
        """Clean up resources."""
        self._camera_generation = getattr(self, "_camera_generation", 0) + 1

        timers = getattr(self, "_timers", None)
        if timers is not None:
            timers.close()
        else:
            if self._camera_init_timer:
                try:
                    self.after_cancel(self._camera_init_timer)
                except Exception:
                    pass
            if self.camera_update_timer:
                try:
                    self.after_cancel(self.camera_update_timer)
                except Exception:
                    pass
        self._camera_init_timer = None
        self.camera_update_timer = None

        # Release camera
        if self.camera:
            self.camera.release()
            self.camera = None

    def _center_window(self):
        """Center window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
