import time
import ctypes
import os
import sys
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from focuscheck.platform_specific.windows import WinClickThroughOverlay, _get_last_error_info


def _get_virtual_screen_rect():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return int(x), int(y), int(w), int(h)


def _apply_spotlight_region(hwnd, screen_w, screen_h, cx, cy, r):
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    region_args = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    gdi32.CreateRectRgn.argtypes = region_args
    gdi32.CreateRectRgn.restype = wintypes.HANDLE
    gdi32.CreateEllipticRgn.argtypes = region_args
    gdi32.CreateEllipticRgn.restype = wintypes.HANDLE
    gdi32.CombineRgn.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE, ctypes.c_int]
    gdi32.CombineRgn.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.DeleteObject.restype = wintypes.BOOL
    user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
    user32.SetWindowRgn.restype = ctypes.c_int
    full = gdi32.CreateRectRgn(0, 0, int(screen_w), int(screen_h))
    hole = gdi32.CreateEllipticRgn(int(cx - r), int(cy - r), int(cx + r), int(cy + r))
    combined = gdi32.CreateRectRgn(0, 0, 1, 1)
    RGN_DIFF = 4
    gdi32.CombineRgn(combined, full, hole, RGN_DIFF)
    ok = user32.SetWindowRgn(hwnd, combined, True)
    gdi32.DeleteObject(full)
    gdi32.DeleteObject(hole)
    return bool(ok)


def main():
    x, y, w, h = _get_virtual_screen_rect()
    print(f"virtual screen rect: x={x} y={y} w={w} h={h}")
    cycles = max(1, int(os.environ.get("FOCUSCHECK_NATIVE_OVERLAY_CYCLES", "3")))
    seconds = max(0.1, float(os.environ.get("FOCUSCHECK_NATIVE_OVERLAY_SECONDS", "0.75")))
    radius = 140
    ok_count = 0
    total = 0
    for cycle in range(cycles):
        overlay = None
        try:
            overlay = WinClickThroughOverlay(x, y, w, h, color_hex="#000000", log_tag="spotlight-selftest")
            print(f"overlay cycle={cycle + 1}/{cycles} hwnd={overlay.hwnd}")
            overlay.set_alpha(0.7)
            start = time.time()
            while (time.time() - start) < seconds:
                t = time.time() - start
                cx = int(w / 2 + (w / 4) * (1.0 if int(t * 2) % 2 == 0 else -1.0))
                cy = int(h / 2)
                ok = _apply_spotlight_region(overlay.hwnd, w, h, cx, cy, radius)
                total += 1
                if ok:
                    ok_count += 1
                time.sleep(0.05)
        finally:
            if overlay is not None:
                overlay.destroy()

    if ok_count != total:
        code, msg = _get_last_error_info()
        print(f"SetWindowRgn failures: {total - ok_count} last_error={code} msg={msg}")
        raise RuntimeError("native overlay region update failure")
    print(f"region updates OK ({ok_count}/{total}); lifecycle cycles OK ({cycles}/{cycles})")


if __name__ == "__main__":
    main()
