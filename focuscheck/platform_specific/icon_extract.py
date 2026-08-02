"""Windows app icon extraction (best effort)."""

import platform
import ctypes
from ctypes import wintypes


def _configure_icon_api(shell32, user32):
    """Declare shell/user32 signatures before icon handle operations."""
    shell32.ExtractIconExW.argtypes = [
        wintypes.LPCWSTR,
        ctypes.c_int,
        ctypes.POINTER(wintypes.HICON),
        ctypes.POINTER(wintypes.HICON),
        wintypes.UINT,
    ]
    shell32.ExtractIconExW.restype = wintypes.UINT
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    user32.DestroyIcon.restype = wintypes.BOOL


def get_app_icon_image(exe_path, size=24):
    """Return a PIL Image of the app icon for an exe path, or None."""
    if platform.system().lower() != "windows":
        return None
    if not exe_path:
        return None
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        _configure_icon_api(shell32, user32)
        large = wintypes.HICON()
        small = wintypes.HICON()
        count = shell32.ExtractIconExW(exe_path, 0, ctypes.byref(large), ctypes.byref(small), 1)
        if count == 0:
            return None
        hicon = small if small else large
        if not hicon:
            return None
        try:
            image = _hicon_to_image(hicon)
        finally:
            try:
                user32.DestroyIcon(hicon)
            except Exception:
                pass
        if image and size:
            try:
                image = image.resize((size, size), Image.LANCZOS)
            except Exception:
                pass
        return image
    except Exception:
        return None


def _hicon_to_image(hicon):
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    class ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", wintypes.HBITMAP),
            ("hbmColor", wintypes.HBITMAP),
        ]

    class BITMAP(ctypes.Structure):
        _fields_ = [
            ("bmType", wintypes.LONG),
            ("bmWidth", wintypes.LONG),
            ("bmHeight", wintypes.LONG),
            ("bmWidthBytes", wintypes.LONG),
            ("bmPlanes", wintypes.WORD),
            ("bmBitsPixel", wintypes.WORD),
            ("bmBits", ctypes.c_void_p),
        ]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", BITMAPINFOHEADER),
            ("bmiColors", wintypes.DWORD * 3),
        ]

    user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(ICONINFO)]
    user32.GetIconInfo.restype = wintypes.BOOL
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
    gdi32.GetObjectW.restype = ctypes.c_int
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC,
        wintypes.HBITMAP,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.POINTER(BITMAPINFO),
        wintypes.UINT,
    ]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.DeleteObject.restype = wintypes.BOOL

    iconinfo = ICONINFO()
    if not user32.GetIconInfo(hicon, ctypes.byref(iconinfo)):
        return None

    bmp = BITMAP()
    if not gdi32.GetObjectW(iconinfo.hbmColor, ctypes.sizeof(BITMAP), ctypes.byref(bmp)):
        return None

    width = bmp.bmWidth
    height = bmp.bmHeight
    if width <= 0 or height <= 0:
        return None

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height  # top-down DIB
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0  # BI_RGB

    buf_len = width * height * 4
    buffer = ctypes.create_string_buffer(buf_len)

    hdc = user32.GetDC(0)
    try:
        res = gdi32.GetDIBits(
            hdc,
            iconinfo.hbmColor,
            0,
            height,
            buffer,
            ctypes.byref(bmi),
            0,
        )
        if not res:
            return None
    finally:
        user32.ReleaseDC(0, hdc)
        if iconinfo.hbmColor:
            gdi32.DeleteObject(iconinfo.hbmColor)
        if iconinfo.hbmMask:
            gdi32.DeleteObject(iconinfo.hbmMask)

    image = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)
    return image


__all__ = ["get_app_icon_image"]
