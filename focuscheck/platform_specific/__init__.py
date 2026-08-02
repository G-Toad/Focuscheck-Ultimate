"""
Platform-specific functionality.

Currently supports:
- Windows: Power events, session monitoring, startup management, overlays
- Future: Linux, macOS support
"""

import platform as _platform

from .startup import (
    compose_startup_command,
    install_startup,
    uninstall_startup,
    is_startup_installed
)

if _platform.system().lower() == "windows":
    from .windows import (
        enable_click_through_windows,
        install_httransparent_wndproc,
        WindowsWakeWatcher,
        WinClickThroughOverlay,
        ensure_gdiplus_started,
        create_hicon_from_image
    )
    __all__ = [
        'compose_startup_command',
        'install_startup',
        'uninstall_startup',
        'is_startup_installed',
        'enable_click_through_windows',
        'install_httransparent_wndproc',
        'WindowsWakeWatcher',
        'WinClickThroughOverlay',
        'ensure_gdiplus_started',
        'create_hicon_from_image',
    ]
else:
    __all__ = [
        'compose_startup_command',
        'install_startup',
        'uninstall_startup',
        'is_startup_installed',
    ]

