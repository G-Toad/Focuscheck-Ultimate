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


def camera_capability_message(capability: dict[str, object]) -> str:
    """Return a short user-facing explanation without exposing paths/errors."""
    state = str(capability.get("state", "unknown"))
    dependencies = capability.get("dependencies")
    if state == "dependency_missing" and isinstance(dependencies, dict):
        missing = [
            name for name, available in dependencies.items()
            if not bool(available)
        ]
        labels = {"opencv": "OpenCV", "pillow": "Pillow"}
        names = ", ".join(labels.get(name, name) for name in missing) or "camera support"
        return f"Camera unavailable: install {names} to enable camera features."
    if state == "device_unavailable":
        return "Camera unavailable: no camera device could be opened."
    if state == "failed":
        return "Camera unavailable: camera access failed."
    if state == "degraded":
        return "Camera running in degraded mode."
    return "Camera unavailable: camera features could not be started."


__all__ = ["build_camera_capability", "camera_capability_message"]
