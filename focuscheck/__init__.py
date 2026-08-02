"""
FocusCheck - Focus and productivity reminder application.

A modular application to help maintain focus through periodic reminders
with configurable intensity levels, task tracking, and smart pause detection.

Usage:
    from focuscheck import App
    app = App()
    app.run()

Or run directly:
    python main.py
"""

__version__ = "1.0.0"
__author__ = "FocusCheck Team"

# Expose main components at package level for easy imports
from .config import APP_NAME, APP_VERSION
from .app import App

__all__ = ['APP_NAME', 'APP_VERSION', 'App']

