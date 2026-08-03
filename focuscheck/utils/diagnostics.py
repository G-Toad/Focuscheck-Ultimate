"""Previewable, sanitized diagnostic bundle service."""

from __future__ import annotations

import json
import os
import re
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


_SECRET_PATTERNS = (
    re.compile(r"(?i)(password|token|secret|api[_ -]?key)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"),
)
_PRIVATE_FIELD_PATTERNS = (
    re.compile(r"(?i)(response(?:_summary)?|user[_ -]?response|window[_ -]?title|title|url)\s*[:=]\s*[^\r\n,}]+"),
    re.compile(r"(?i)(response(?:_summary)?|user[_ -]?response|window[_ -]?title|title|url)\s*[:=]\s*(['\"]).*?\2"),
)
DIAGNOSTIC_FORMAT_VERSION = 1


def format_status_snapshot(snapshot: dict) -> str:
    """Render a bounded, privacy-safe health snapshot for the status window."""
    if not isinstance(snapshot, dict):
        raise TypeError("diagnostic status snapshot must be a mapping")
    rows = (
        ("Application", snapshot.get("application", "FocusCheck")),
        ("Version", snapshot.get("version", "unknown")),
        ("Lifecycle", snapshot.get("lifecycle", "unknown")),
        ("Monitoring", snapshot.get("monitoring", "unknown")),
        ("Paused", snapshot.get("paused", "unknown")),
        ("Prompt active", snapshot.get("prompt_active", "unknown")),
        ("Intervention active", snapshot.get("intervention_active", "unknown")),
        ("Camera", snapshot.get("camera", {}).get("state", "unknown") if isinstance(snapshot.get("camera"), dict) else "unknown"),
        ("Guard", snapshot.get("guard_status", "unknown")),
        ("Tray backend", snapshot.get("tray_backend", "unknown")),
        ("Settings schema keys", snapshot.get("settings_schema_keys", "unknown")),
        ("Doctor anomalies", snapshot.get("doctor_anomalies", "unknown")),
        ("Process ID", snapshot.get("pid", "unknown")),
        ("Data root", snapshot.get("data_root", "unknown")),
    )
    return "\n".join(f"{label}: {value}" for label, value in rows)


def _candidates(root: Path) -> list[Path]:
    paths = sorted(root.glob("*.log"))
    paths.extend((root / name for name in ("verification.json", "structured_events.jsonl", "runtime_state.jsonl")))
    unique = []
    seen = set()
    for path in paths:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        if path.is_symlink():
            raise ValueError(f"refusing symlink diagnostic source: {path.name}")
        unique.append(path)
    return unique


def _redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if not parsed.scheme or not parsed.netloc:
            return "<url-redacted>"
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except ValueError:
        return "<url-redacted>"


def sanitize(text: str, *, root: Path) -> str:
    """Redact credentials, local paths, URLs' query/fragment, and private fields."""
    result = text.replace(str(root), "<verification-root>")
    result = result.replace(str(Path.home()), "<user-home>")
    result = re.sub(r"(?i)C:\\Users\\[^\\\r\n]+", "<windows-user-path>", result)
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(
            lambda match: f"{match.group(1)}=<redacted>" if "=" in match.group(0) or ":" in match.group(0) else "Bearer <redacted>",
            result,
        )
    result = re.sub(r"https?://[^\s\"'<>]+", lambda match: _redact_url(match.group(0)), result)
    for pattern in _PRIVATE_FIELD_PATTERNS:
        result = pattern.sub(lambda match: f"{match.group(1)}=<redacted>", result)
    return result


def preview_bundle(runtime: Path) -> dict:
    """Return filenames and sizes without reading or returning their contents."""
    root = Path(runtime).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    files = [{"path": path.name, "size": path.stat().st_size} for path in _candidates(root)]
    return {"root": str(root), "files": files, "excluded": ["settings", "tasks", "camera", "exports"]}


def _bundle_manifest(root: Path) -> dict:
    """Build archive metadata without embedding the user's absolute path."""
    preview = preview_bundle(root)
    return {
        "format_version": DIAGNOSTIC_FORMAT_VERSION,
        "files": preview["files"],
        "excluded": preview["excluded"],
        "root": "<runtime-root>",
    }


def create_bundle(runtime: Path, output: Path, *, overwrite: bool = False) -> Path:
    """Create an atomic sanitized diagnostic ZIP from allowlisted sources."""
    root = Path(runtime).resolve()
    destination = Path(output).resolve()
    preview_bundle(root)
    if destination.exists() and not overwrite:
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in _candidates(root):
                archive.writestr(source.name, sanitize(source.read_text(encoding="utf-8", errors="replace"), root=root))
            archive.writestr(
                "DIAGNOSTIC_MANIFEST.json",
                json.dumps(_bundle_manifest(root), indent=2, sort_keys=True),
            )
        os.replace(temporary, destination)
        return destination
    finally:
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


__all__ = [
    "DIAGNOSTIC_FORMAT_VERSION",
    "create_bundle",
    "format_status_snapshot",
    "preview_bundle",
    "sanitize",
]
