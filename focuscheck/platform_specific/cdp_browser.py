"""Best-effort Chromium CDP discovery for URLs and tabs (no registry edits)."""

import json
import time
import urllib.request


_CANDIDATE_PORTS = list(range(9222, 9231))
_MAX_TARGETS = 256
_MAX_TITLE_LENGTH = 2048
_MAX_URL_LENGTH = 4096
_CACHE = {
    "timestamp": 0.0,
    "targets": [],
}


def _fetch_json(url, timeout=0.2):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FocusCheck"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
            return json.loads(data)
    except Exception:
        return None


def _discover_targets(timeout=1.0):
    targets = []
    deadline = time.monotonic() + max(0.0, float(timeout))
    for index, port in enumerate(_CANDIDATE_PORTS):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        ports_remaining = max(1, len(_CANDIDATE_PORTS) - index)
        # Share the overall deadline across every candidate so a healthy
        # browser on a later port is not starved by earlier closed ports.
        request_budget = min(0.2, max(0.01, remaining / (ports_remaining * 2)))
        version = _fetch_json(f"http://127.0.0.1:{port}/json/version", timeout=request_budget)
        if not isinstance(version, dict):
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        listing = _fetch_json(f"http://127.0.0.1:{port}/json/list", timeout=min(request_budget, remaining))
        if not isinstance(listing, list):
            continue
        for entry in listing[:_MAX_TARGETS]:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") and entry.get("type") != "page":
                continue
            entry = dict(entry)
            if isinstance(entry.get("title"), str):
                entry["title"] = entry["title"][:_MAX_TITLE_LENGTH]
            if isinstance(entry.get("url"), str):
                entry["url"] = entry["url"][:_MAX_URL_LENGTH]
            entry["cdp_port"] = port
            entry["cdp_browser"] = version.get("Browser", "")
            targets.append(entry)
            if len(targets) >= _MAX_TARGETS:
                return targets
    return targets


def get_cdp_targets(max_age=2.0, timeout=1.0):
    # Cache expiry must not depend on wall-clock adjustments while the app
    # is running (sleep/resume and time synchronization can move it backward).
    now = time.monotonic()
    if now - _CACHE["timestamp"] > max_age:
        _CACHE["targets"] = _discover_targets(timeout=timeout)
        _CACHE["timestamp"] = now
    return list(_CACHE["targets"])


def find_best_target(window_title):
    """Find the best CDP target for a given window title."""
    title = (window_title or "").lower()
    targets = get_cdp_targets()
    if not targets:
        return None
    # Prefer explicit active flag if present
    for entry in targets:
        if entry.get("active"):
            return entry
    if not title:
        return targets[0]
    # Try exact/substring title match
    for entry in targets:
        t = (entry.get("title") or "").lower()
        if t and t in title:
            return entry
    for entry in targets:
        t = (entry.get("title") or "").lower()
        if t and title in t:
            return entry
    return targets[0] if targets else None


def get_best_url_for_window(window_title):
    """Return the best URL for the given window title from CDP, or None."""
    target = find_best_target(window_title)
    if not target:
        return None
    url = target.get("url")
    return url or None


def list_tab_titles():
    """Return a list of tab titles from CDP targets."""
    titles = []
    for entry in get_cdp_targets()[:_MAX_TARGETS]:
        title = entry.get("title")
        if title:
            titles.append(str(title)[:_MAX_TITLE_LENGTH])
    # De-dup
    seen = set()
    unique = []
    for t in titles:
        if t in seen:
            continue
        seen.add(t)
        unique.append(t)
    return unique


__all__ = ["get_cdp_targets", "get_best_url_for_window", "list_tab_titles"]
