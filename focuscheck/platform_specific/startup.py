"""Windows startup registry management."""

import sys
import os
import platform as _platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StartupInspection:
    """Observed state of the application's per-user startup value."""

    status: str
    command: str = ""
    expected_command: str = ""
    detail: str = ""
    launcher_path: str = ""
    launcher_present: bool = False

    @property
    def present(self) -> bool:
        return self.status in {"valid", "stale", "malformed", "legacy", "duplicate"}

    @property
    def repairable(self) -> bool:
        return self.status in {"stale", "malformed", "legacy", "duplicate"}


def _startup_launcher_path() -> Path | None:
    """Return the legacy Startup-folder launcher path when discoverable."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "RunFocusCheckSupervisor.cmd"


def compose_startup_command(entrypoint=None):
    """Generate command for Windows startup."""
    try:
        if getattr(sys, 'frozen', False):
            child = Path(sys.executable).resolve()
            supervisor = child.with_name("FocusCheckSupervisor.exe")
            return f'"{supervisor}" --run --base-dir "{child.parent}"'
        if entrypoint is None:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            entrypoint = os.path.join(root, "focuscheck_supervisor.py")
        supervisor = os.path.abspath(entrypoint)
        root = os.path.dirname(supervisor)
        return f'"{sys.executable}" "{supervisor}" --run --base-dir "{root}"'
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
    key = None
    try:
        from ..utils.logging_utils import get_logger
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        except FileNotFoundError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, cmd)
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
    finally:
        if key is not None:
            try:
                winreg.CloseKey(key)
            except Exception:
                pass


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
    except FileNotFoundError:
        # A missing Run key already represents the requested uninstalled state.
        print(f"No startup registry key found; startup entry '{name}' is absent.")
        try:
            from ..utils.logging_utils import get_logger
            get_logger().info("uninstalled startup: %s (registry key absent)", name)
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


def repair_startup(name: str = "FocusCheck") -> bool:
    """Repair startup to the canonical registry route and remove its legacy duplicate."""
    inspection = inspect_startup(name)
    if inspection.status == "unsupported":
        return False
    if inspection.status == "valid":
        return True
    if not install_startup(name):
        return False
    if inspection.launcher_present and inspection.launcher_path:
        try:
            legacy_launcher = Path(inspection.launcher_path)
            # The path came from the fixed Startup-folder filename in inspection.
            if legacy_launcher.name == "RunFocusCheckSupervisor.cmd":
                legacy_launcher.unlink(missing_ok=True)
        except OSError:
            return False
    return True


def is_startup_installed(name: str = "FocusCheck") -> bool:
    """Check whether a non-empty startup entry exists."""
    return inspect_startup(name).present


def inspect_startup(name: str = "FocusCheck") -> StartupInspection:
    """Inspect the current user's startup value without modifying the registry."""
    if _platform.system().lower() != 'windows':
        return StartupInspection("unsupported", detail="Windows startup registry is unavailable")
    launcher = _startup_launcher_path()
    launcher_present = bool(launcher and launcher.exists())
    launcher_text = str(launcher) if launcher else ""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            val, typ = winreg.QueryValueEx(key, name)
            command = str(val or "").strip()
        except FileNotFoundError:
            if launcher_present:
                return StartupInspection(
                    "legacy",
                    detail="legacy Startup-folder launcher exists without the official registry entry",
                    launcher_path=launcher_text,
                    launcher_present=True,
                )
            return StartupInspection("absent", launcher_path=launcher_text, launcher_present=False)
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        if launcher_present:
            return StartupInspection(
                "legacy",
                detail="legacy Startup-folder launcher exists without the official registry entry",
                launcher_path=launcher_text,
                launcher_present=True,
            )
        return StartupInspection("absent", launcher_path=launcher_text, launcher_present=False)
    except Exception as exc:
        return StartupInspection("error", detail=str(exc), launcher_path=launcher_text, launcher_present=launcher_present)

    if typ != getattr(winreg, "REG_SZ", 1):
        return StartupInspection(
            "duplicate" if launcher_present else "malformed",
            command=command,
            detail=f"startup registry value has unsupported type {typ!r}",
            launcher_path=launcher_text,
            launcher_present=launcher_present,
        )

    if not command:
        return StartupInspection(
            "duplicate" if launcher_present else "malformed",
            detail="startup value is empty" if not launcher_present else "registry entry is empty and legacy launcher also exists",
            launcher_path=launcher_text,
            launcher_present=launcher_present,
        )

    expected = compose_startup_command()
    normalize = lambda value: " ".join(str(value).replace("/", "\\").casefold().split())
    if normalize(command) == normalize(expected):
        if launcher_present:
            return StartupInspection(
                "duplicate",
                command=command,
                expected_command=expected,
                detail="official registry entry is valid but legacy Startup-folder launcher also exists",
                launcher_path=launcher_text,
                launcher_present=True,
            )
        return StartupInspection("valid", command=command, expected_command=expected)
    return StartupInspection(
        "duplicate" if launcher_present else "stale",
        command=command,
        expected_command=expected,
        detail=(
            "startup command is stale and legacy Startup-folder launcher also exists"
            if launcher_present
            else "startup command does not target the current installation"
        ),
        launcher_path=launcher_text,
        launcher_present=launcher_present,
    )

