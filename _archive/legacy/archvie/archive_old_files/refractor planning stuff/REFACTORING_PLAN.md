# FocusCheck Refactoring Plan

## Overview
Refactor the monolithic `guard.py` (~5000 lines) into a modular, maintainable structure following Python best practices (PEP8).

## Proposed Structure

```
focuscheck/
├── main.py                          # Entry point with CLI
├── requirements.txt                 # Dependencies
├── README.md                        # Usage documentation
├── focuscheck/
│   ├── __init__.py                 # Package initialization
│   ├── config.py                   # Constants (APP_NAME, Windows API constants)
│   ├── app.py                      # Main App class (~600 lines)
│   │
│   ├── utils/                      # Utility functions
│   │   ├── __init__.py
│   │   ├── paths.py                # Path management (get_data_dir, resource_path, etc.)
│   │   ├── logging_utils.py        # Logging setup (get_logger, log_exception)
│   │   ├── file_ops.py             # File operations (locks, single-instance)
│   │   └── colors.py               # Color parsing (parse_rgb_hex)
│   │
│   ├── settings/                   # Settings management
│   │   ├── __init__.py
│   │   ├── defaults.py             # DEFAULT_SETTINGS dictionary
│   │   └── manager.py              # load_settings, save_settings, validate_settings
│   │
│   ├── database/                   # Database and logging
│   │   ├── __init__.py
│   │   ├── task_db.py              # TaskDB class (SQLite operations)
│   │   └── csv_logger.py           # CSV logging (ensure_log_header, append_log, etc.)
│   │
│   ├── platform/                   # Platform-specific code
│   │   ├── __init__.py
│   │   ├── windows.py              # Windows integration (WakeWatcher, overlay, GDI+)
│   │   └── startup.py              # Startup management (install/uninstall/check)
│   │
│   ├── ui/                         # UI components
│   │   ├── __init__.py
│   │   ├── guards.py               # PauseGuard class
│   │   ├── overlay.py              # Overlay classes (WinClickThroughOverlay)
│   │   ├── dialogs.py              # Dialog windows (~1500 lines)
│   │   │                           # - PromptDialog
│   │   │                           # - TaskEntryDialog
│   │   │                           # - WastePromptDialog
│   │   │                           # - TaskChangeDialog
│   │   └── windows.py              # Main windows (~1000 lines)
│   │                               # - SettingsWindow
│   │                               # - TaskHistoryWindow
│   │
│   └── system_tray.py              # System tray (already modular, move as-is)
```

## Module Breakdown

### 1. **config.py** (~50 lines)
- Application metadata: `APP_NAME`, `APP_VERSION`
- Windows API constants: `WM_WTSSESSION_CHANGE`, `GWL_EXSTYLE`, etc.
- All constant definitions

### 2. **utils/** (4 files, ~300 lines total)
#### paths.py
- `get_base_dir()`: Get application base directory
- `get_data_dir()`: Get data directory (APPDATA on Windows)
- `resource_path()`: Handle PyInstaller bundled resources
- `choose_path()`: Legacy path compatibility

#### logging_utils.py
- `get_logger()`: Singleton logger with rotation
- `log_exception()`: Exception logging helper
- `rotate_log_if_needed()`: Log rotation management

#### file_ops.py
- `get_file_lock()`: Thread-safe file locking
- `acquire_single_instance()`: Windows mutex for single instance

#### colors.py
- `parse_rgb_hex()`: Parse hex color strings to RGB tuples

### 3. **settings/** (2 files, ~400 lines total)
#### defaults.py
- `DEFAULT_SETTINGS`: Complete default settings dictionary

#### manager.py
- `validate_settings()`: Validate and sanitize settings
- `load_settings()`: Load from JSON with fallback
- `save_settings()`: Atomic save with temp file

### 4. **database/** (2 files, ~600 lines total)
#### task_db.py
- `TaskDB` class: SQLite database wrapper
  - Task CRUD operations
  - Session tracking
  - Response logging
  - History queries

#### csv_logger.py
- `ensure_log_header()`: Create CSV headers
- `append_log()`: Log responses to CSV
- `append_waste_log()`: Log wasted time
- `rotate_csv_if_needed()`: CSV rotation

### 5. **platform/** (2 files, ~800 lines total)
#### windows.py
- `enable_click_through_windows()`: Window transparency
- `install_httransparent_wndproc()`: Window procedure hook
- `WindowsWakeWatcher`: Power/session event monitoring
- `WinClickThroughOverlay`: Full-screen overlay
- GDI+ integration for icons

#### startup.py
- `compose_startup_command()`: Generate startup command
- `install_startup()`: Add to Windows startup
- `uninstall_startup()`: Remove from startup
- `is_startup_installed()`: Check startup status

### 6. **ui/** (4 files, ~2500 lines total)
#### guards.py
- `PauseGuard`: Manages pause state based on idle/lock/sleep

#### overlay.py
- `WinClickThroughOverlay`: Multi-monitor dimming overlay

#### dialogs.py
- `PromptDialog`: Main focus check prompt (~1000 lines)
  - Button handling
  - Intensity levels
  - Overdrive stages
  - Animations

- `TaskEntryDialog`: Task creation dialog
- `WastePromptDialog`: Waste time reflection
- `TaskChangeDialog`: Task change with reason

#### windows.py
- `SettingsWindow`: Settings UI (~700 lines)
  - Tabbed interface
  - Real-time validation
  - Settings persistence

- `TaskHistoryWindow`: Task history viewer

### 7. **app.py** (~600 lines)
- `App` class: Main application orchestrator
  - Initialization
  - Event scheduling
  - Prompt management
  - System tray integration
  - Settings management
  - Task database interaction

### 8. **main.py** (~150 lines)
- Entry point
- CLI argument handling:
  - `--selftest`: Run diagnostics
  - `--tray-selftest`: Test system tray
  - `--install-startup`: Install to startup
  - `--uninstall-startup`: Remove from startup
  - `--tray-test`: Test tray icon
- Global exception handler
- Single instance check
- App instantiation and run

### 9. **system_tray.py** (existing, ~485 lines)
- Already well-structured
- Move as-is into package

## Benefits of Refactoring

### Maintainability
- **Clear separation of concerns**: Each module has a single responsibility
- **Easier navigation**: Find code by logical grouping
- **Reduced cognitive load**: Smaller files are easier to understand

### Testability
- **Unit testing**: Each module can be tested independently
- **Mocking**: Dependencies are explicit and can be mocked
- **CI/CD ready**: Modular structure supports automated testing

### Scalability
- **Easy feature addition**: New features fit into existing structure
- **Plugin architecture**: UI components can be extended
- **Platform expansion**: Easy to add Linux/Mac support

### Code Quality
- **PEP8 compliance**: Proper module structure and naming
- **Docstrings**: Each module and function documented
- **Type hints**: Better IDE support and error catching
- **DRY principle**: Eliminate duplication through proper factoring

## Migration Strategy

1. **Create new structure** (don't delete original yet)
2. **Move code module by module** (start with utils, then settings, etc.)
3. **Update imports** as modules are created
4. **Test incrementally** after each module
5. **Keep original guard.py** until full migration complete
6. **Final validation** with all features working
7. **Delete guard.py** and update documentation

## Import Examples

### Before (monolithic):
```python
# Everything in one file
from guard import App, load_settings, get_logger
```

### After (modular):
```python
# Clear, logical imports
from focuscheck.app import App
from focuscheck.settings import load_settings
from focuscheck.utils import get_logger
from focuscheck.ui.dialogs import PromptDialog
from focuscheck.database import TaskDB
```

## File Size Comparison

| Original | Refactored | Reduction |
|----------|------------|-----------|
| guard.py (5258 lines) | Largest module: dialogs.py (~1000 lines) | 80% smaller files |
| 1 file | 20+ files | Better organization |

## Next Steps

1. Review and approve structure
2. Begin implementation:
   - ✅ Create directory structure
   - ✅ Implement config.py
   - ✅ Implement utils/* modules
   - 🔄 Implement settings/* modules
   - ⏳ Implement database/* modules
   - ⏳ Implement platform/* modules
   - ⏳ Implement ui/* modules
   - ⏳ Implement app.py
   - ⏳ Implement main.py
3. Test each module
4. Update documentation
5. Create requirements.txt

## Notes

- **No functionality changes**: This is a pure refactoring
- **Backward compatibility**: Maintain same behavior
- **Settings migration**: Existing config files work unchanged
- **PyInstaller compatible**: Structure works with frozen builds

