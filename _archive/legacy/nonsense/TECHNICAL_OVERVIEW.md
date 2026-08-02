# FocusCheck - Technical Architecture & Implementation Guide

## Executive Summary

**FocusCheck** is a productivity monitoring application that periodically prompts users to categorize their current activity (studying/focused vs. wasting time). It implements progressive escalation mechanics to prevent users from ignoring or dismissing prompts habitually, and includes task management, analytics, and anti-spam features.

**Target Platform:** Primarily Windows (with cross-platform considerations)
**Tech Stack:** Python 3, Tkinter (GUI), SQLite (data persistence), OpenCV (optional camera feed)
**Architecture:** Monolithic desktop application with modular component organization

---

## 1. High-Level Architecture

### 1.1 Application Flow

```
main.py (Entry Point)
    └─> focuscheck.App (Core Application Loop)
        ├─> Settings Management (JSON-based configuration)
        ├─> Task Database (SQLite for task tracking)
        ├─> System Tray Integration (pystray + Windows native fallback)
        ├─> Platform-Specific Watchers (Sleep/Wake/Lock detection)
        ├─> Periodic Scheduler (Tkinter event loop)
        └─> Prompt Dialog (Main user interaction)
            ├─> Challenge System (Anti-habit mechanisms)
            ├─> Intensification Engine (Progressive escalation)
            ├─> Camera Feed (Optional user accountability)
            └─> Task Management UI (Inline task tracking)
```

### 1.2 Core Design Principles

1. **Interruption-Based Architecture**: The app operates on scheduled interruptions rather than passive monitoring
2. **Progressive Escalation**: Increasing urgency if user delays response (visual/audio/screen effects)
3. **Anti-Habit System**: Randomization and challenges to prevent automatic/thoughtless responses
4. **Modular Mixins**: PromptDialog uses multiple mixins for separation of concerns
5. **Graceful Degradation**: Optional features (camera, tray) fail silently if dependencies unavailable

---

## 2. Project Structure

```
focuscheck/
├── __init__.py                    # Package initialization
├── app.py                         # Main App class (event loop coordinator)
├── config.py                      # Constants and Windows API definitions
├── system_tray.py                 # Cross-platform system tray (pystray)
│
├── database/                      # Data persistence layer
│   ├── __init__.py
│   ├── task_db.py                # SQLite task/session management
│   └── csv_logger.py             # CSV logging for analytics
│
├── settings/                      # Configuration management
│   ├── __init__.py
│   ├── defaults.py               # Default settings schema
│   └── manager.py                # Settings load/save/validation
│
├── platform_specific/             # OS-specific implementations
│   ├── __init__.py
│   ├── windows.py                # Windows wake/sleep/lock watchers
│   └── startup.py                # Startup registry management
│
├── ui/                           # User interface components
│   ├── __init__.py
│   ├── guards.py                 # Pause/idle detection
│   ├── windows.py                # Settings window
│   └── dialogs/                  # Dialog components
│       ├── prompt_dialog.py      # Main check-in dialog (mixin composition)
│       ├── task_entry_dialog.py  # Task creation form
│       ├── phrase_acronym_dialog.py  # Challenge: acronym puzzle
│       ├── challenge_system.py   # Challenge selection/execution
│       ├── spam_detection.py     # Input validation
│       └── prompt_dialog_mixins/ # Feature mixins
│           ├── button_handling.py        # Button events/randomization
│           ├── window_placement.py       # Multi-monitor positioning
│           ├── time_display.py           # Time/progress info
│           ├── anti_habit.py             # Press-and-hold logic
│           ├── intensification.py        # Progressive escalation
│           ├── task_management.py        # Task panel integration
│           ├── camera_feed.py            # OpenCV camera integration
│           └── windows_integration.py    # Windows-specific helpers
│
└── utils/                        # Shared utilities
    ├── logging_utils.py          # Logging configuration
    ├── paths.py                  # Path resolution
    ├── colors.py                 # Color utilities
    └── audio.py                  # Audio alert system
```

---

## 3. Core Components

### 3.1 Application Entry (`main.py` → `app.py`)

**`main.py`**: Command-line entry point
- Handles CLI arguments (`--selftest`, `--install-startup`, etc.)
- Single instance enforcement (prevents multiple app instances)
- Exception handling setup
- Delegates to `App().run()`

**`focuscheck/app.py`**: Main application class
- **Tkinter Event Loop**: Drives entire application via `root.mainloop()`
- **Scheduling**: Uses `root.after()` for periodic prompts
- **Settings Refresh**: Reloads settings on each prompt cycle
- **Tray Integration**: Dual strategy:
  1. Try `pystray` (cross-platform) first
  2. Fall back to Windows native tray if pystray fails
- **Wake/Sleep Handling**: Subscribes to `WindowsWakeWatcher` events

**Key Initialization Flow:**
```python
App.__init__():
  1. Create hidden Tk root window
  2. Load settings from JSON
  3. Initialize TaskDB (SQLite)
  4. Set up PauseGuard (idle/lock detection)
  5. Prepare tray icon (PIL image conversion)
  6. Start system tray (pystray or Windows native)
  7. Initialize WindowsWakeWatcher (power/session events)
  8. Schedule first prompt (2 seconds quick test)
  9. Start heartbeat loops (pause detection, file heartbeat)
```

### 3.2 Settings Management (`settings/`)

**Architecture**: JSON-based configuration with validation layer

**Files:**
- `defaults.py`: Schema definition with default values (150+ settings)
- `manager.py`: Load/save with atomic writes and thread-safe locking

**Key Features:**
- **Atomic Writes**: Temp file + rename to prevent corruption
- **Validation**: Type coercion, range clamping (e.g., intervals clamped to ≥10s)
- **Unknown Key Preservation**: Allows forward/backward compatibility
- **Thread Safety**: Uses `threading.Lock()` for concurrent access

**Storage Location:**
- Windows: `%APPDATA%\FocusCheck\focus_settings.json`
- Cross-platform fallback to user home directory

**Critical Settings Categories:**
1. **Timing**: `interval_seconds`, `intensify_after_seconds`, `overdrive_after_seconds`
2. **UI Behavior**: `always_on_top`, `center_on_show`, `popup_layout_mode`
3. **Challenges**: Challenge system enable flags and frequencies
4. **Camera**: Camera feed mode, device index, face tracking parameters
5. **Pause Conditions**: `pause_on_idle`, `pause_on_lock`, `pause_on_sleep`

### 3.3 Task Database (`database/task_db.py`)

**Technology**: SQLite with WAL mode for concurrent access

**Schema:**
```sql
tasks:
  - id (PRIMARY KEY)
  - created_utc, title, why, consequences, due_utc
  - status (active|completed|failed|changed)
  - completed_utc, change_reason, timed_out

waste_events:
  - id, created_utc, what, consequences, active_task_id

focus_events:
  - id, created_utc, doing, benefits, active_task_id
```

**Key Operations:**
- `get_active()`: Retrieve current active task
- `start_task()`: Create new task, sets status='active'
- `mark_completed()`: Task succeeded
- `mark_failed()`: Task failed (timeout or explicit)
- `mark_changed()`: User switched tasks
- `overdue_active_to_failed()`: Automatic timeout on due date

**Analytics**: Calculated from event tables (waste vs. focus ratios)

### 3.4 Prompt Dialog (`ui/dialogs/prompt_dialog.py`)

**Architecture**: Mixin-based composition for modularity

```python
class PromptDialog(
    ButtonHandlingMixin,      # Button randomization, focus, events
    WindowPlacementMixin,     # Multi-monitor positioning
    TimeDisplayMixin,         # Time/progress display
    AntiHabitMixin,          # Press-and-hold logic
    IntensificationMixin,     # Progressive escalation
    TaskManagementMixin,      # Task panel UI
    WindowsIntegrationMixin,  # Windows-specific APIs
    CameraFeedMixin,         # OpenCV camera feed
    tk.Toplevel
):
```

**Lifecycle:**
1. **Initialization**: Build UI based on `popup_layout_mode` (vertical/horizontal/compact)
2. **Window Placement**: Center on active monitor or specific monitor
3. **Focus Forcing**: Multiple attempts to grab focus (Windows `SetForegroundWindow`)
4. **Timer Scheduling**: Intensification and overdrive timers
5. **Response Handling**: Validate input, show challenges if needed, log to database
6. **Cleanup**: Camera feed cleanup, timer cancellation, window destruction

**Critical Timing:**
- `intensify_after_seconds`: Start visual/audio escalation (default: 20s)
- `overdrive_after_seconds`: Aggressive escalation (default: 60s)
- Stage 4: Rapid flashing, shake effects
- Stage 5: Screen dimming/blackout overlays or gamma manipulation

**Anti-Minimize Protection:**
- `_prevent_minimize()`: Bound to `<Unmap>` event, immediately restores window
- `_ignore_close()`: X button disabled via `WM_DELETE_WINDOW` protocol
- Windows API: `GWL_STYLE` modified to remove minimize button

---

## 4. Key Features & Implementation

### 4.1 Progressive Intensification

**Goal**: Prevent users from ignoring prompts

**Stages:**
1. **Initial (0-20s)**: Normal dialog, subtle jiggle if enabled
2. **Intensification (20s-60s)**: Escalating visual effects
   - Button pulsing/shaking
   - Audio alerts (if enabled)
   - Taskbar flashing (Windows)
3. **Overdrive Stage 3 (60s+)**: Aggressive escalation
   - Background flashing
   - Continuous shake loop
   - Button jiggling
4. **Overdrive Stage 4**: Rapid full-screen flashing
5. **Overdrive Stage 5**: Screen dimming/blackout
   - **Overlay Mode**: Transparent overlay windows on all monitors
   - **Gamma Mode**: Direct display gamma ramp manipulation (Windows)
   - Progressive dimming to max alpha (configurable)
   - Optional hold requirement: Must hold button to proceed

**Implementation Details:**
- `IntensificationMixin`: Manages stage transitions via timers
- `_active_timers`: Registry for cleanup on dialog close
- Configurable thresholds allow disabling stages

### 4.2 Anti-Habit System

**Problem**: Users can develop muscle memory to dismiss prompts without thinking

**Solutions:**

**1. Press-and-Hold Buttons** (`AntiHabitMixin`):
```python
# User must hold button for configurable duration
on_press: Start timer and visual feedback
on_motion: Track if mouse moved (drag detection)
on_release: Only submit if held long enough without moving
```
- Prevents accidental clicks
- Requires deliberate action
- Configurable threshold (default: 1000ms for "studying")

**2. Button Randomization** (`ButtonHandlingMixin`):
- `randomize_buttons`: Shuffle button positions on each prompt
- Prevents positional muscle memory

**3. Challenge System** (`dialogs/challenge_system.py`):
- **Frequency-based**: Configurable percentage per response type
- **Challenge Types**:
  - **Studying Challenges**:
    - Learning Specificity: "What specifically are you learning?"
    - Goal Connection: "How does this connect to your goals?"
    - Will Commitment: "Are you committed to finishing?"
    - Output Expectation: "What output will you produce?"
  - **Wasting Challenges**:
    - Wasting Acknowledgment: Type "I am wasting time"
    - Should/Gap Analysis: "What should you be doing? Why the gap?"
    - Because Reasoning: "Because [reason]" completion
    - Hour Projection: "What will you have accomplished in an hour?"
    - Tomorrow Regret: "Will you regret this tomorrow?"
    - Fear Acknowledgment: Confront avoidance behavior
    - Lying Confrontation: Address dishonest responses

**4. Acronym Puzzle** (`phrase_acronym_dialog.py`):
- User presented with phrase (e.g., "By any means necessary")
- Must form acronym by clicking/dragging/typing letters (e.g., "BAMN")
- Only correct letters are accepted
- Letters disappear from pool when correctly placed
- Auto-completes when all correct

### 4.3 Spam Detection

**Purpose**: Prevent users from bypassing challenges with gibberish

**`spam_detection.py` Checks:**
1. **Gibberish Detection**:
   - Vowel ratio analysis (too few or too many vowels)
   - Consecutive character limits
   - Unique character ratio
2. **Repetition Check**: Detects repeated patterns
3. **Spacing Check**: Requires spaces for longer inputs
4. **Keyboard Pattern Check**: Detects sequences like "asdfgh"
5. **Dictionary Check**: Real word ratio threshold
6. **Timing Check**: Minimum time to submit (prevents instant spam)
7. **Banned Words**: Blacklist of vague/evasive words ("stuff", "things", "idk")

**Action on Spam**: Challenge is rejected and re-shown with warning

### 4.4 Camera Feed Integration

**Purpose**: Accountability through self-observation

**Technology**: OpenCV (`cv2`) with optional face detection

**Modes:**
1. **Live Feed**: Real-time camera display during prompt
2. **Static Capture**: Snapshot on button click

**Face Tracking** (`camera_feed.py`):
- **Detection Methods**:
  - Haar Cascade (fast, less accurate)
  - DNN (slower, more accurate)
- **Zoom Modes**:
  - Standard: Fixed zoom factor on detected face
  - Edge-Aware: Increased zoom if face near frame edge
  - Maximize: Fill display with face region
- **Centering**: Vertical bias and crop multipliers for framing

**Camera Settings**:
- Device index selection (multi-camera support)
- FPS control
- Sizing modes: aspect_ratio, fixed_size, face_tracking
- Horizontal flip option (mirror mode)

**Performance Optimization:**
- Frame skipping if detection expensive
- Fallback to non-face mode if detection fails

### 4.5 Platform-Specific Integration

**Windows (`platform_specific/windows.py`):**

**WindowsWakeWatcher**: Subclasses `tk.Toplevel` to receive Windows messages
```python
class WindowsWakeWatcher(tk.Toplevel):
    def __init__(..., on_resume_callable, on_pause_callable):
        # Register custom window procedure
        self.hwnd = self.winfo_id()
        self._proc = self._create_win32_callback()
        self._oldWndProc = user32.SetWindowLongPtrW(
            self.hwnd, GWL_WNDPROC, self._proc
        )
```

**Monitored Events:**
- `WM_POWERBROADCAST`: Sleep/resume (`PBT_APMSUSPEND`, `PBT_APMRESUMESUSPEND`)
- `WM_WTSSESSION_CHANGE`: Lock/unlock (`WTS_SESSION_LOCK`, `WTS_SESSION_UNLOCK`)
- `WM_DISPLAYCHANGE`: Monitor configuration changes

**Callbacks**: Notify `App` to clear pause flags or trigger immediate prompt

**Startup Management** (`platform_specific/startup.py`):
- Windows: Registry key in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Writes absolute path to Python executable + script

**System Tray (`system_tray.py`):**
- Uses `pystray` library (cross-platform)
- Menu items: Pause/Resume, Settings, Tasks, Startup, Logs, Exit
- Icon: PNG converted to ICO with multiple resolutions
- Thread-safe: Runs in separate thread, uses `app._call_on_ui_thread()` for Tk operations

### 4.6 Pause/Idle Detection

**`PauseGuard` (`ui/guards.py`):**

**Conditions:**
1. **Windows Idle**: `GetLastInputInfo()` API (keyboard/mouse activity)
2. **Windows Lock**: Event-driven flag from `WindowsWakeWatcher`
3. **Windows Sleep**: Event-driven flag from `WindowsWakeWatcher`
4. **Linux Lid**: Read `/proc/acpi/button/lid/*/state`
5. **macOS Clamshell**: Execute `ioreg` command, parse output

**Behavior**:
- If any condition true: Reschedule prompt with poll interval (default: 5s)
- Heartbeat loop checks pause state every 1 second
- On pause→unpause transition: Immediate prompt scheduled

**Override**: `force_always_on` setting disables all pause logic

---

## 5. Data Flow & Event Handling

### 5.1 Scheduling Loop

```
App.run() → root.mainloop()
    ↓
_schedule_next(delay_ms)
    ↓ (after delay)
_maybe_show_prompt()
    ├─> Check global pause toggle
    ├─> Check PauseGuard conditions
    ├─> Prevent duplicate prompts
    └─> Create PromptDialog
        ↓
    User interaction (button click)
        ↓
    _on_button_click() [ButtonHandlingMixin]
        ├─> Check hold requirement
        ├─> Show challenge if required
        └─> _do_submit()
            ├─> Validate input (spam detection)
            ├─> Log to database (CSV + SQLite)
            ├─> Call on_submit callback
            └─> Destroy dialog
                ↓
    _on_prompt_done() [App]
        ↓
    _schedule_next() → loop continues
```

### 5.2 Task Decision Flow

**Problem**: Evaluate if active task is being worked on

**Evaluation Modes:**
1. **Before Due Date**: Prompt appears X minutes before deadline
2. **After Start**: Prompt appears X minutes after task start

**Decision Dialog:**
- Shows task details (title, why, consequences, time remaining)
- Options: "Yes, still working" | "Completed" | "Failed" | "Changed task"
- Integrated into main PromptDialog via `TaskManagementMixin`

**Database Actions:**
- Completed → `mark_completed()`
- Failed → `mark_failed()`
- Changed → `mark_changed()` + show `TaskEntryDialog` for new task

### 5.3 Logging & Analytics

**CSV Logging** (`database/csv_logger.py`):
- One row per prompt response
- Columns: timestamp, category, task_id, response_time, intensity_level, etc.
- Used for historical analysis

**SQLite Events:**
- `waste_events`: Log what user was wasting time on
- `focus_events`: Log what user was focused on
- Linked to active task via `active_task_id`

**Analytics Display**:
- Timescale selection: Lifetime, Today, 7d, 30d
- Focus ratio: `focus_events / (focus_events + waste_events)`
- Average response time
- Task success rate

---

## 6. Build & Deployment

### 6.1 Dependencies

**Core:**
- `tkinter`: GUI framework (included with Python)
- `sqlite3`: Database (included with Python)
- Standard library: `json`, `os`, `time`, `threading`, `ctypes`

**Optional:**
- `pystray`: Cross-platform system tray
- `Pillow (PIL)`: Image processing for tray icon
- `opencv-python (cv2)`: Camera feed
- `pygame`: Audio alerts (fallback to system beep if unavailable)

**Installation:**
```bash
pip install pystray Pillow opencv-python pygame
```

### 6.2 Running

**Development:**
```bash
python main.py
```

**CLI Options:**
```bash
python main.py --selftest           # Test Windows event hooks
python main.py --install-startup    # Add to Windows startup
python main.py --uninstall-startup  # Remove from startup
python main.py --tray-test          # Test tray icon (20s)
```

### 6.3 Packaging (PyInstaller)

**Typical Command:**
```bash
pyinstaller --onefile --windowed --icon=icon.ico \
    --add-data "imageedit_5_9158249849.png;." \
    --add-data "focuscheck;focuscheck" \
    main.py
```

**Considerations:**
- `--windowed`: No console window
- `--onefile`: Single executable (slower startup) vs. `--onedir` (faster)
- Include all asset files (images, sounds) via `--add-data`
- Exclude unnecessary modules to reduce size

### 6.4 Data Locations

**Windows Paths (via `%APPDATA%`):**
```
C:\Users\<username>\AppData\Roaming\FocusCheck\
├── focus_settings.json       # Settings
├── focus_tasks.db            # SQLite database
├── focus_log.csv             # CSV event log
├── focus_heartbeat.json      # Watchdog heartbeat
└── logs\
    └── focus.log             # Application log
```

**Path Resolution** (`utils/paths.py`):
- Supports `--portable` mode (data in executable directory)
- Falls back to home directory if AppData unavailable

---

## 7. Design Patterns & Best Practices

### 7.1 Mixin Pattern

**Rationale**: `PromptDialog` has 8+ distinct responsibilities. Mixins provide:
- Separation of concerns
- Easier testing (test mixins independently)
- Reusability across dialog variants

**Example:**
```python
class TimeDisplayMixin:
    def _build_time_panel(self):
        # Only responsible for time display logic
        ...

    def _update_time_display(self):
        # Timer updates
        ...
```

### 7.2 Callback Architecture

**Pattern**: Inversion of control for dialog results

```python
def _show_dialog():
    def on_complete(result):
        # Process result
        ...

    MyDialog(parent, on_complete=on_complete)
```

**Benefits:**
- Non-blocking UI (no `wait_window()` blocking)
- Cleaner error handling
- Easier to chain dialogs

### 7.3 Graceful Degradation

**Examples:**
1. **TaskDB unavailable**: Continue without task features
2. **pystray fails**: Fall back to Windows native tray
3. **Camera unavailable**: Disable camera panel
4. **Audio fails**: Fall back to system beep

**Implementation:**
```python
try:
    from .system_tray import SystemTray
except ImportError:
    SystemTray = None  # Optional feature

# Later:
if SystemTray is not None:
    self._tray = SystemTray(...)
```

### 7.4 Thread Safety

**Main Thread**: Tkinter UI thread (not thread-safe)
**Background Threads**: pystray tray (runs in own thread)

**Solution**: `_call_on_ui_thread()` marshals callbacks
```python
def _call_on_ui_thread(self, callback):
    self.root.after(0, callback)  # Schedule on UI thread
```

### 7.5 Resource Cleanup

**Pattern**: Timer registry for cleanup

```python
class PromptDialog:
    def __init__(self):
        self._active_timers = set()

    def _schedule_timer(self, delay, callback):
        timer_id = self.after(delay, callback)
        self._active_timers.add(timer_id)
        return timer_id

    def _cleanup_all_timers(self):
        for tid in self._active_timers:
            try:
                self.after_cancel(tid)
            except:
                pass
        self._active_timers.clear()
```

**Cleanup Checklist:**
- Cancel all `after()` timers
- Release camera resources (`cv2.VideoCapture.release()`)
- Destroy overlay windows (Stage 5)
- Restore gamma ramps (if modified)

---

## 8. Testing & Debugging

### 8.1 Self-Test Mode

```bash
python main.py --selftest
```

**Tests:**
- Python bitness (32-bit vs 64-bit)
- Windows message handling (lock/unlock/suspend/resume)
- Callback firing

### 8.2 Logging

**Location**: `%APPDATA%\FocusCheck\logs\focus.log`

**Usage:**
```python
from focuscheck.utils import get_logger
get_logger().info("message")
get_logger().exception("error", exc_info=True)
```

**Configuration**: Rotating file handler (max 5 files, 1MB each)

### 8.3 Common Issues

**Problem**: Tray icon not appearing
**Diagnosis**: Check log for pystray import errors
**Solution**: Install Pillow and pystray, or rely on Windows native tray

**Problem**: Camera not detected
**Diagnosis**: Check `camera_device_index` setting
**Solution**: Try index 0, 1, 2 until camera found

**Problem**: Prompts paused unexpectedly
**Diagnosis**: Check PauseGuard conditions (`pause_on_idle`, etc.)
**Solution**: Disable pause conditions or set `force_always_on: true`

**Problem**: Stage 5 gamma not restoring
**Diagnosis**: App crashed without cleanup
**Solution**: Restart display driver or reboot

---

## 9. Extension Points

### 9.1 Adding New Challenges

**Steps:**
1. Create challenge class in `ui/dialogs/`
2. Implement required interface (show dialog, return result)
3. Register in `challenge_system.py` challenge pool
4. Add settings flag and frequency to `defaults.py`
5. Add UI controls in `SettingsWindow`

**Example Interface:**
```python
class MyChallenge:
    def __init__(self, parent, on_complete):
        self.dialog = tk.Toplevel(parent)
        # Build UI

    def show(self):
        # Show dialog modally or non-blocking
        ...
```

### 9.2 Custom Intensification Stages

**Location**: `IntensificationMixin._begin_intensify()`

**Customization:**
```python
def _begin_intensify(self):
    self.intensity_level += 1
    if self.intensity_level == 1:
        # Your custom effect here
        self._my_custom_effect()
    # ... existing stages
```

### 9.3 Additional Data Logging

**CSV**: Edit `csv_logger.py` to add columns
**SQLite**: Add tables via `task_db.py._ensure_schema()`

---

## 10. Performance Considerations

### 10.1 Tkinter Event Loop

- **Single-threaded**: All UI updates must run on main thread
- **Non-blocking**: Use `after()` instead of `sleep()` or blocking calls
- **Overhead**: Each timer callback has small overhead (~1-5ms)

### 10.2 Camera Feed

**Bottlenecks:**
- Frame capture: ~10-30ms per frame
- Face detection: Haar ~5-20ms, DNN ~50-200ms per frame

**Optimizations:**
- Skip face detection every N frames
- Lower FPS setting (10-15 FPS sufficient for accountability)
- Use Haar instead of DNN if speed critical

### 10.3 Database Operations

- **WAL Mode**: Allows concurrent reads while writing
- **Connection Pooling**: Not implemented (single-user app, low frequency)
- **Batch Inserts**: Not needed (one row per minute typical)

### 10.4 Memory Usage

**Typical**: 50-100MB RAM
**Camera Enabled**: +50-100MB (OpenCV buffers)
**Stage 5 Overlays**: +10MB per monitor (transparent windows)

---

## 11. Security & Privacy

### 11.1 Data Storage

- **Local Only**: All data stored on user's machine
- **No Network**: No telemetry or cloud sync (except optional webhook)
- **Plaintext**: Settings and database not encrypted (user can inspect)

### 11.2 Camera Data

- **Not Saved**: Camera frames not persisted (unless user implements capture)
- **Local Processing**: Face detection runs entirely locally (no cloud API)

### 11.3 Webhook Integration

**Optional Feature**: POST to custom URL on each prompt response

**Payload Example:**
```json
{
  "timestamp": "2024-11-06T10:30:00Z",
  "category": "studying",
  "task_id": 42,
  "response_time_seconds": 15.3
}
```

**Security**: User responsible for securing webhook endpoint

---

## 12. Future Architecture Improvements

### 12.1 Potential Refactorings

1. **Separate UI and Logic**:
   - Extract business logic from Tkinter widgets
   - Enable headless mode or alternate UI frameworks

2. **Plugin System**:
   - Dynamic loading of challenges
   - User-contributed challenge packs

3. **Multi-User Support**:
   - Profile switching
   - Separate databases per user

4. **Cross-Platform Enhancements**:
   - Native tray for Linux/macOS (not just pystray)
   - Better idle detection for non-Windows

### 12.2 Scalability

**Current**: Single-user desktop app, no scaling concerns

**If Multi-User**:
- Consider client-server architecture
- Centralized database (PostgreSQL)
- User authentication

---

## 13. Development Workflow

### 13.1 Development Environment Setup

```bash
# Clone/download project
git clone <repo_url>
cd FocusCheck

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python main.py
```

### 13.2 Making Changes

**Settings Changes:**
1. Add default to `settings/defaults.py`
2. Add validation in `settings/manager.py`
3. Add UI controls in `ui/windows.py` (SettingsWindow)
4. Use setting in relevant component

**UI Changes:**
1. Locate relevant mixin or dialog
2. Modify `_build_*_layout()` methods
3. Test with different `ui_scale_percent` values
4. Test on multiple monitors if placement-related

**Database Changes:**
1. Add migration logic in `task_db.py._ensure_schema()`
2. Use `ALTER TABLE` for adding columns
3. Check for column existence before altering
4. Test migration with existing databases

---

## 14. Conclusion

**FocusCheck** is a well-structured, modular productivity application with sophisticated user engagement mechanics. The architecture prioritizes:

1. **Modularity**: Mixin pattern enables independent feature development
2. **Reliability**: Graceful degradation and error handling throughout
3. **Flexibility**: Extensive settings system supports diverse user needs
4. **Platform Integration**: Deep Windows integration with cross-platform considerations

**Key Strengths:**
- Progressive escalation effectively prevents prompt dismissal
- Anti-habit mechanisms force conscious decision-making
- Task management integration provides actionable accountability
- Modular codebase facilitates maintenance and extension

**Areas for Improvement:**
- Tighter separation of UI and business logic
- More comprehensive automated testing
- Enhanced cross-platform support (macOS, Linux)
- Plugin architecture for community contributions

This technical overview should provide a senior engineer with sufficient context to understand, maintain, and extend the FocusCheck application.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-06
**Maintainer:** FocusCheck Development Team
