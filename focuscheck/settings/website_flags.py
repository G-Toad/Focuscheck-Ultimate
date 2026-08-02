"""Canonical validation for persisted website-flag domains."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit


_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_website_domain(value) -> str:
    """Return a hostname suitable for exact/subdomain matching, or ``""``.

    Flag storage is hostname-only. URL-shaped input is accepted only when it
    contains an HTTP(S) hostname and no path, query, fragment, credentials, or
    port. Rejecting ambiguous input is safer than silently broadening a block.
    """
    text = str(value or "").strip()
    if not text or any(character.isspace() for character in text):
        return ""
    if text.startswith("*.") or "*" in text:
        return ""

    if "://" in text:
        parsed = urlsplit(text)
        if parsed.scheme.lower() not in ("http", "https"):
            return ""
        if parsed.username or parsed.password or parsed.port is not None:
            return ""
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            return ""
        host = parsed.hostname or ""
    else:
        if any(character in text for character in "/?#@"):
            return ""
        host = text

    host = host.strip().rstrip(".").lower()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not host or len(host) > 253:
        return ""

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        return address.compressed.lower()

    try:
        labels = [label.encode("idna").decode("ascii") for label in host.split(".")]
    except (UnicodeError, ValueError):
        return ""
    if not labels or any(not label or len(label) > 63 or not _LABEL_RE.fullmatch(label) for label in labels):
        return ""
    return ".".join(labels)
