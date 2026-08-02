# FocusCheck Assets

## Custom Tray Icon

To use a custom tray icon:

1. Save your icon as **`tray_icon.png`** in this directory (`focuscheck/assets/`)
2. The icon should be a PNG file (transparent background recommended)
3. Recommended size: 32x32 to 128x128 pixels (will be automatically resized)
4. Restart FocusCheck for the new icon to take effect

### Current Setup

The icon loading priority is:
1. **`focuscheck/assets/tray_icon.png`** (highest priority - custom icon)
2. Default icon from the base directory
3. Any PNG/ICO files found in the application directory

### Icon Requirements

- Format: PNG (recommended) or ICO
- Transparency: Supported (RGBA)
- Size: Will be automatically converted to multiple sizes for the system tray (16x16, 20x20, 24x24, 32x32, 48x48, 64x64, 128x128)

### Example

Your eye icon with triangles should be saved as:
```
focuscheck/assets/tray_icon.png
```

After placing the file, restart FocusCheck and you'll see your custom icon in the system tray!
