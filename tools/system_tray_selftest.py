"""Smoke test for the optional system tray integration."""

from __future__ import annotations


def main() -> None:
    from focuscheck.system_tray import SystemTray
    from focuscheck.settings import gates

    assert gates.is_start_stop_enabled({}) is True
    assert gates.is_settings_enabled({}) is True

    tray = SystemTray(name="FocusCheck Selftest", tooltip="FocusCheck Selftest")
    assert tray is not None

    print("tray-selftest: system tray module imports OK")


if __name__ == "__main__":
    main()
