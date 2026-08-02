"""Privacy-safe camera capability state helpers."""

from __future__ import annotations


def build_camera_capability(
    *,
    enabled: bool,
    opencv_available: bool,
    pillow_available: bool,
    device_open: bool | None = None,
    stream_active: bool = False,
    access: str | None = None,
    degraded: bool = False,
    error: BaseException | None = None,
) -> dict[str, object]:
    """Return bounded camera health metadata without device or image details."""
    dependencies = bool(opencv_available and pillow_available)
    if not enabled:
        state = "disabled"
        access_value = "not_requested"
    elif not dependencies:
        state = "dependency_missing"
        access_value = "unavailable"
    elif device_open is False:
        state = "failed" if error is not None else "device_unavailable"
        access_value = access or "failed"
    elif stream_active:
        state = "degraded" if degraded else "active"
        access_value = access or "granted"
    else:
        state = "ready"
        access_value = access or "not_started"

    return {
        "enabled": bool(enabled),
        "dependencies": {
            "opencv": bool(opencv_available),
            "pillow": bool(pillow_available),
        },
        "device": (
            "available" if device_open is True
            else "unavailable" if device_open is False
            else "not_requested"
        ),
        "access": access_value,
        "stream": "active" if stream_active else "inactive",
        "state": state,
        "error_type": type(error).__name__ if error is not None else "",
    }


__all__ = ["build_camera_capability"]
