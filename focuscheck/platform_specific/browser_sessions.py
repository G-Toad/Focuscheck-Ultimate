"""Read-only browser session recovery fallbacks.

These collectors are deliberately conservative. They never modify browser
profiles, never treat recovered data as the active foreground tab, and apply
strict file, item, and text budgets before returning anything to the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

from .browser_info import normalize_browser_process


_MAX_FILE_BYTES = 16 * 1024 * 1024
_MAX_TABS = 256
_MAX_TITLE_LENGTH = 2048
_MAX_URL_LENGTH = 4096
_MAX_PROFILE_FILES = 32
_MOZ_HEADER = b"mozLz40\x00"
_URL_RE = re.compile(rb"https?://[^\x00\s\"'<>]{1,4096}")

_CHROMIUM_ROOTS = {
    "chrome.exe": ("LOCALAPPDATA", "Google", "Chrome", "User Data"),
    "msedge.exe": ("LOCALAPPDATA", "Microsoft", "Edge", "User Data"),
    "brave.exe": ("LOCALAPPDATA", "BraveSoftware", "Brave-Browser", "User Data"),
    "opera.exe": ("APPDATA", "Opera Software", "Opera Stable"),
    "opera_gx.exe": ("APPDATA", "Opera Software", "Opera GX Stable"),
}


@dataclass(frozen=True)
class BrowserTab:
    """A bounded recovered tab; recovery does not imply foreground status."""

    title: str = ""
    url: str = ""
    window_index: int | None = None
    source: str = "session"


def _bounded(value, limit: int) -> str:
    return str(value or "")[:limit]


def _safe_url(value) -> str:
    """Keep session URLs useful for matching without retaining query data."""
    raw = _bounded(value, _MAX_URL_LENGTH)
    try:
        parts = urlsplit(raw)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except ValueError:
        return ""


def _unique_tabs(tabs: Iterable[BrowserTab]) -> list[BrowserTab]:
    result: list[BrowserTab] = []
    seen: set[tuple[str, str, int | None]] = set()
    for tab in tabs:
        key = (tab.title, tab.url, tab.window_index)
        if not tab.url or key in seen:
            continue
        seen.add(key)
        result.append(tab)
        if len(result) >= _MAX_TABS:
            break
    return result


def _lz4_block_decompress(payload: bytes, *, max_output: int = _MAX_FILE_BYTES) -> bytes:
    """Decode a raw LZ4 block without adding a runtime dependency."""
    output = bytearray()
    index = 0
    while index < len(payload):
        token = payload[index]
        index += 1
        literal_length = token >> 4
        if literal_length == 15:
            while True:
                if index >= len(payload):
                    raise ValueError("truncated LZ4 literal length")
                extra = payload[index]
                index += 1
                literal_length += extra
                if extra != 255:
                    break
        end = index + literal_length
        if end > len(payload) or len(output) + literal_length > max_output:
            raise ValueError("LZ4 literal exceeds budget")
        output.extend(payload[index:end])
        index = end
        if index == len(payload):
            break
        if index + 2 > len(payload):
            raise ValueError("truncated LZ4 match offset")
        offset = payload[index] | (payload[index + 1] << 8)
        index += 2
        if offset <= 0 or offset > len(output):
            raise ValueError("invalid LZ4 match offset")
        match_length = token & 0x0F
        if match_length == 15:
            while True:
                if index >= len(payload):
                    raise ValueError("truncated LZ4 match length")
                extra = payload[index]
                index += 1
                match_length += extra
                if extra != 255:
                    break
        match_length += 4
        if len(output) + match_length > max_output:
            raise ValueError("LZ4 match exceeds budget")
        for _ in range(match_length):
            output.append(output[-offset])
    return bytes(output)


def parse_firefox_recovery(data: bytes) -> list[BrowserTab]:
    """Parse Firefox's ``recovery.jsonlz4`` selected tab entries."""
    if not isinstance(data, (bytes, bytearray)) or not bytes(data).startswith(_MOZ_HEADER):
        return []
    try:
        decoded = _lz4_block_decompress(bytes(data)[len(_MOZ_HEADER):])
        payload = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError, TypeError):
        return []
    if not isinstance(payload, dict) or not isinstance(payload.get("windows"), list):
        return []
    tabs: list[BrowserTab] = []
    for window_index, window in enumerate(payload["windows"][:_MAX_TABS]):
        if not isinstance(window, dict) or not isinstance(window.get("tabs"), list):
            continue
        for tab in window["tabs"][:_MAX_TABS]:
            if not isinstance(tab, dict) or not isinstance(tab.get("entries"), list):
                continue
            entries = tab["entries"]
            try:
                selected = int(tab.get("index", len(entries))) - 1
            except (TypeError, ValueError):
                selected = len(entries) - 1
            selected = min(max(selected, 0), len(entries) - 1)
            entry = entries[selected]
            if not isinstance(entry, dict):
                continue
            url = _safe_url(entry.get("url"))
            title = _bounded(entry.get("title"), _MAX_TITLE_LENGTH)
            if url.startswith(("http://", "https://")):
                tabs.append(BrowserTab(title=title, url=url, window_index=window_index, source="firefox-session"))
    return _unique_tabs(tabs)


def parse_chromium_session(data: bytes) -> list[BrowserTab]:
    """Recover URL-bearing Chromium session strings conservatively.

    Chromium session files are protobuf streams whose exact schema varies by
    browser version. URL extraction is therefore intentionally limited to
    valid HTTP(S) strings; callers must use UIA/CDP for active-tab identity.
    """
    if not isinstance(data, (bytes, bytearray)):
        return []
    tabs = [BrowserTab(url=_safe_url(match.group(0).decode("utf-8", "ignore")), source="chromium-session")
            for match in _URL_RE.finditer(bytes(data)[:_MAX_FILE_BYTES])]
    return _unique_tabs(tabs)


def _safe_read(path: Path, root: Path) -> bytes | None:
    try:
        if _has_symlink_component(path, root) or not path.is_file():
            return None
        resolved_root = root.resolve()
        resolved = path.resolve()
        resolved.relative_to(resolved_root)
        if resolved.stat().st_size > _MAX_FILE_BYTES:
            return None
        with resolved.open("rb") as stream:
            data = stream.read(_MAX_FILE_BYTES + 1)
        return None if len(data) > _MAX_FILE_BYTES else data
    except (OSError, RuntimeError, ValueError):
        return None


def _has_symlink_component(path: Path, root: Path) -> bool:
    """Reject reparse-like profile components before resolving a session file."""
    current = Path(path)
    boundary = Path(root)
    try:
        while True:
            if current.is_symlink():
                return True
            if current == boundary or current.parent == current:
                return boundary.is_symlink() if current != boundary else False
            current = current.parent
    except OSError:
        return True


def _candidate_paths(process_name: str, env: Mapping[str, str]) -> list[tuple[Path, str, Path]]:
    process = normalize_browser_process(process_name)
    candidates: list[tuple[Path, str, Path]] = []
    if process == "firefox.exe":
        appdata = env.get("APPDATA")
        if appdata:
            root = Path(appdata) / "Mozilla" / "Firefox" / "Profiles"
            for profile in sorted(root.glob("*"))[:_MAX_PROFILE_FILES]:
                candidates.append((profile / "sessionstore-backups" / "recovery.jsonlz4", "firefox", root))
    elif process in _CHROMIUM_ROOTS:
        variable, *parts = _CHROMIUM_ROOTS[process]
        base = env.get(variable)
        if base:
            root = Path(base).joinpath(*parts)
            profiles = [root] if process.startswith("opera") else sorted(root.glob("*"))[:_MAX_PROFILE_FILES]
            for profile in profiles:
                session_dir = profile / "Sessions"
                candidates.extend((session_dir / name, "chromium", root) for name in ("Current Tabs", "Current Session"))
    return candidates[:_MAX_PROFILE_FILES * 2]


def collect_browser_tabs(process_name: str, *, env: Mapping[str, str] | None = None,
                         roots: Iterable[Path] | None = None) -> list[BrowserTab]:
    """Collect bounded session tabs for a browser process without mutation."""
    environment = dict(os.environ if env is None else env)
    if roots is not None:
        candidates = [(Path(root), "firefox" if normalize_browser_process(process_name) == "firefox.exe" else "chromium", Path(root).parent)
                      for root in roots]
    else:
        candidates = _candidate_paths(process_name, environment)
    tabs: list[BrowserTab] = []
    for path, kind, root in candidates[:_MAX_PROFILE_FILES * 2]:
        data = _safe_read(path, root)
        if data is None:
            continue
        parsed = parse_firefox_recovery(data) if kind == "firefox" else parse_chromium_session(data)
        tabs.extend(parsed)
        if len(tabs) >= _MAX_TABS:
            break
    return _unique_tabs(tabs)


__all__ = ["BrowserTab", "collect_browser_tabs", "parse_chromium_session", "parse_firefox_recovery"]
