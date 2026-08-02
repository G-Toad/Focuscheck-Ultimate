"""
Color parsing utilities.

Handles parsing of color strings in various formats.
"""


def parse_rgb_hex(s, default=(0, 0, 0)):
    """
    Parse a hex color string (e.g. '#FF0000') into an RGB tuple.
    
    Supports formats:
    - '#RRGGBB' (6 hex digits)
    - '#RGB' (3 hex digits, expanded to RRGGBB)
    
    Args:
        s: Color string to parse
        default: Default RGB tuple if parsing fails
        
    Returns:
        Tuple of (R, G, B) values in range 0-255
    """
    s = (s or "").strip()
    if not s.startswith("#"):
        return default
    s = s[1:]
    try:
        if len(s) == 6:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        elif len(s) == 3:
            return (int(s[0]*2, 16), int(s[1]*2, 16), int(s[2]*2, 16))
    except Exception:
        pass
    return default

