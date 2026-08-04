"""Composed data-control operations used by tray and shell adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


class DataControlService:
    """Own the external data operations behind the App command boundary."""

    def __init__(self, _app: Any = None) -> None:
        self._app = _app

    def export_data(self, source_root: Path, destination: Path, *, categories: Iterable[str]):
        from ..utils.data_export import export_data

        return export_data(source_root, destination, categories=tuple(categories))

    def inventory_data(self, source_root: Path):
        from ..utils.data_export import inventory_data

        return inventory_data(source_root)

    def clear_data(self, source_root: Path, *, categories: Iterable[str], confirmed: bool):
        from ..utils.data_export import clear_data

        return clear_data(source_root, categories=tuple(categories), confirmed=confirmed)

    def apply_retention(self, source_root: Path, *, max_age_days: int, apply: bool):
        from ..utils.data_retention import apply_retention

        return apply_retention(source_root, max_age_days=max_age_days, apply=apply)

    def preview_bundle(self, source_root: Path):
        from ..utils.diagnostics import preview_bundle

        return preview_bundle(source_root)

    def create_bundle(self, source_root: Path, destination: Path):
        from ..utils.diagnostics import create_bundle

        return create_bundle(source_root, destination)


__all__ = ["DataControlService"]
