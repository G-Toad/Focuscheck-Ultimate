"""Windows startup registry management."""

import sys
import os
import platform as _platform


def compose_startup_command(entrypoint=None):
    """Generate command for Windows startup."""
    try:
        if getattr(sys, 'frozen', False):
            return f'"{sys.executable}"'
        if entrypoint is None:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            entrypoint = os.path.join(root, "focuscheck_supervisor.py")
            return f'"{sys.executable}" "{os.path.abspath(entrypoint)}" --run --base-dir "{root}"'
        return f'"{sys.executable}" "{os.path.abspath(entrypoint)}"'
    except Exception:
        return os.path.abspath(entrypoint or sys.argv[0] or __file__)


def install_startup(name: str = "FocusCheck"):
    """Add application to Windows startup."""
    if _platform.system().lower() != 'windows':
        print("Startup install is supported on Windows only.")
        return False
    try:
        import winreg
    except Exception:
        print("winreg unavailable; cannot install startup entry.")
        return False
    
    cmd = compose_startup_command()
    try:
        from ..utils.logging_utils import get_logger
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        except FileNotFoundError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        try:
            get_logger().info("installed startup: %s -> %s", name, cmd)
        except Exception:
            pass
        print(f"Installed startup entry: {name} -> {cmd}")
        return True
    except Exception as e:
        try:
            from ..utils.logging_utils import get_logger
            get_logger().error("install_startup failed: %s", e)
        except Exception:
            pass
        print(f"Failed to install startup entry: {e}")
        return False


def uninstall_startup(name: str = "FocusCheck"):
    """Remove application from Windows startup."""
    if _platform.system().lower() != 'windows':
        print("Startup uninstall is supported on Windows only.")
        return False
    try:
        import winreg
    except Exception:
        print("winreg unavailable; cannot uninstall startup entry.")
        return False
    
    try:
        from ..utils.logging_utils import get_logger
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, name)
            print(f"Removed startup entry: {name}")
        except FileNotFoundError:
            print(f"No startup entry named '{name}' found.")
        finally:
            winreg.CloseKey(key)
        try:
            get_logger().info("uninstalled startup: %s", name)
        except Exception:
            pass
        return True
    except Exception as e:
        try:
            from ..utils.logging_utils import get_logger
            get_logger().error("uninstall_startup failed: %s", e)
        except Exception:
            pass
        print(f"Failed to uninstall startup entry: {e}")
        return False


def is_startup_installed(name: str = "FocusCheck") -> bool:
    """Check if startup entry exists."""
    if _platform.system().lower() != 'windows':
        return False
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            val, typ = winreg.QueryValueEx(key, name)
            return bool(val)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False

