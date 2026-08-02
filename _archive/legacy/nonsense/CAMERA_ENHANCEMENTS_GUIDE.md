# Camera Feed Enhancements - FocusCheck

## Overview

The enhanced camera feed system now includes intelligent sizing modes, facial detection, and aspect ratio preservation. This provides a more sophisticated and less distracting self-reflection experience.

## What's New

### ✅ Fixed Issues
- **Arrow Display**: Fixed the flashing arrows that were showing as question marks. They now properly display as ← and → arrows

### 🎯 New Features

1. **Three Sizing Modes**
   - **Aspect Ratio Mode** (Default): Maintains natural camera aspect ratio
   - **Fixed Size Mode**: Fills exact dimensions (may distort)
   - **Face Tracking Mode**: Intelligently zooms/crops to your face

2. **Facial Detection**
   - Uses OpenCV Haar Cascades for real-time face detection
   - Automatically crops and zooms to keep your face centered
   - Configurable zoom factor and max dimensions
   - Fallback modes when no face detected

3. **Smart Settings UI**
   - Settings automatically grey out when not applicable
   - Clear visual organization by mode
   - Recommended values with helpful hints

## Sizing Modes Explained

### 1. Aspect Ratio Mode (Recommended for Most Users)

**How it works:**
- Maintains the natural aspect ratio of your camera (e.g., 16:9, 4:3)
- Resizes to fit within specified max dimensions without distortion
- Clean, professional look that respects your camera's native format

**Settings:**
- `camera_sizing_mode`: `"aspect_ratio"`
- `camera_feed_width`: 320 (max width)
- `camera_feed_height`: 240 (max height)

**Best for:**
- Users who want a clean, undistorted view
- Standard use cases
- When you don't need face tracking

**Example:**
```json
{
  "camera_sizing_mode": "aspect_ratio",
  "camera_feed_width": 400,
  "camera_feed_height": 300
}
```
Result: Camera displays at natural ratio, scaled to fit within 400x300

---

### 2. Fixed Size Mode

**How it works:**
- Stretches/squishes camera feed to fill exact dimensions
- May distort aspect ratio if dimensions don't match camera ratio
- Predictable, consistent size every time

**Settings:**
- `camera_sizing_mode`: `"fixed_size"`
- `camera_feed_width`: Exact width in pixels
- `camera_feed_height`: Exact height in pixels

**Best for:**
- Users who need precise, predictable dimensions
- When distortion is acceptable
- Specific layout requirements

**Example:**
```json
{
  "camera_sizing_mode": "fixed_size",
  "camera_feed_width": 320,
  "camera_feed_height": 240
}
```
Result: Camera will always be exactly 320x240, even if it distorts

---

### 3. Face Tracking Mode (Most Engaging)

**How it works:**
- Detects your face in real-time using OpenCV
- Automatically crops and zooms to keep your face prominent
- Dynamic sizing based on face detection
- Falls back gracefully when no face detected

**Settings:**
- `camera_sizing_mode`: `"face_tracking"`
- `camera_face_max_width`: 400 (recommended)
- `camera_face_max_height`: 300 (recommended)
- `camera_face_zoom_factor`: 1.5 (face + context)
- `camera_face_fallback_mode`: `"aspect_ratio"` or `"fixed_size"`

**Zoom Factor Explained:**
- **1.0**: Just the face (tight crop, may feel claustrophobic)
- **1.5**: Face + context (recommended - shows face plus some background)
- **2.0**: Wider view (more context, less zoomed)
- **3.0**: Very wide (minimal zoom, almost full frame)

**Fallback Modes:**
When no face is detected (looking away, poor lighting, etc.):
- `aspect_ratio`: Shows full camera view at natural ratio
- `fixed_size`: Shows full camera at fixed dimensions

**Best for:**
- Maximum accountability and self-awareness
- Creating "visceral" self-reflection moments
- Users who want the system to focus on them specifically
- Strong psychological impact

**Example - Recommended Setup:**
```json
{
  "camera_sizing_mode": "face_tracking",
  "camera_face_max_width": 400,
  "camera_face_max_height": 300,
  "camera_face_zoom_factor": 1.5,
  "camera_face_fallback_mode": "aspect_ratio"
}
```

**Example - Aggressive Setup:**
```json
{
  "camera_sizing_mode": "face_tracking",
  "camera_face_max_width": 640,
  "camera_face_max_height": 480,
  "camera_face_zoom_factor": 1.0,
  "camera_face_fallback_mode": "aspect_ratio"
}
```
Result: Large, tight crop on face - maximum presence and impact

---

## Complete Settings Reference

### Core Settings

```json
{
  // Enable/disable camera feed
  "camera_feed_enabled": false,

  // Live feed or static snapshot
  "camera_feed_mode": "live",  // "live" | "static"

  // Capture photos when buttons clicked
  "camera_capture_on_click": false,

  // Camera device (0 = default)
  "camera_device_index": 0,

  // Frame rate for live mode
  "camera_fps": 30
}
```

### Sizing Mode Settings

```json
{
  // Main sizing mode selector
  "camera_sizing_mode": "aspect_ratio",  // "aspect_ratio" | "fixed_size" | "face_tracking"

  // FIXED SIZE MODE (only used when camera_sizing_mode = "fixed_size")
  "camera_feed_width": 320,
  "camera_feed_height": 240,

  // FACE TRACKING MODE (only used when camera_sizing_mode = "face_tracking")
  "camera_face_tracking_enabled": false,
  "camera_face_max_width": 400,        // Recommended: 400 for good presence
  "camera_face_max_height": 300,       // Recommended: 300 for reasonable size
  "camera_face_zoom_factor": 1.5,      // 1.0-3.0, recommended: 1.5
  "camera_face_fallback_mode": "aspect_ratio"  // "aspect_ratio" | "fixed_size"
}
```

## Recommended Configurations

### Minimal & Clean
**For users who want subtle self-reflection without distraction:**
```json
{
  "camera_feed_enabled": true,
  "camera_feed_mode": "static",
  "camera_sizing_mode": "aspect_ratio",
  "camera_feed_width": 240,
  "camera_feed_height": 180,
  "camera_capture_on_click": false
}
```

### Balanced (Recommended)
**Good mix of presence and practicality:**
```json
{
  "camera_feed_enabled": true,
  "camera_feed_mode": "live",
  "camera_sizing_mode": "aspect_ratio",
  "camera_feed_width": 320,
  "camera_feed_height": 240,
  "camera_capture_on_click": true,
  "camera_fps": 30
}
```

### Maximum Impact with Face Tracking
**For users who want strong accountability:**
```json
{
  "camera_feed_enabled": true,
  "camera_feed_mode": "live",
  "camera_sizing_mode": "face_tracking",
  "camera_capture_on_click": true,
  "camera_face_max_width": 400,
  "camera_face_max_height": 300,
  "camera_face_zoom_factor": 1.5,
  "camera_face_fallback_mode": "aspect_ratio",
  "camera_fps": 30
}
```

### Ultra-Aggressive Face Tracking
**Maximum psychological pressure:**
```json
{
  "camera_feed_enabled": true,
  "camera_feed_mode": "live",
  "camera_sizing_mode": "face_tracking",
  "camera_capture_on_click": true,
  "camera_face_max_width": 640,
  "camera_face_max_height": 480,
  "camera_face_zoom_factor": 1.0,
  "camera_face_fallback_mode": "aspect_ratio",
  "camera_fps": 30
}
```

## Using the Settings UI

1. **Open Settings**: Right-click tray icon → Settings → Behavior tab
2. **Scroll to Camera Feed Reflection section**
3. **Enable camera feed**: Toggle "Enable camera feed" ON
4. **Choose sizing mode**: Select from dropdown:
   - `aspect_ratio` - Natural ratio (default)
   - `fixed_size` - Exact dimensions
   - `face_tracking` - AI face detection

5. **Configure mode-specific settings**:
   - Settings for inactive modes are automatically greyed out
   - Only relevant settings are shown

6. **Set common settings**:
   - Camera device index
   - Frame rate (for live mode)
   - Photo capture option

7. **Click Save**

## Technical Details

### Face Detection

**How it works:**
- Uses OpenCV's Haar Cascade Classifier (`haarcascade_frontalface_default.xml`)
- Runs face detection on every frame in live mode
- Caches last known face position for smooth transitions
- Applies zoom factor padding around detected face
- Crops frame to face region and resizes to max dimensions

**Performance:**
- Face detection adds minimal CPU overhead (~5-10ms per frame)
- Higher FPS will use more CPU for face detection
- Recommended: 15-30 FPS for smooth tracking without excessive CPU

**Fallback Behavior:**
- When no face detected: Uses cached position if available
- If no cached position: Falls back to configured fallback mode
- Smooth transitions prevent jarring jumps

### Aspect Ratio Preservation

**Algorithm:**
```python
# Calculate aspect ratio
aspect_ratio = frame_width / frame_height

# Fit within max dimensions while maintaining ratio
if landscape:
    new_width = min(max_width, frame_width)
    new_height = new_width / aspect_ratio
    if new_height > max_height:
        new_height = max_height
        new_width = new_height * aspect_ratio
```

**Result:**
- No distortion
- Maximum size that fits within constraints
- Preserves original camera aspect ratio

### Camera Resolution

The camera is initialized at **1280x720** internally to allow for:
- High-quality face detection
- Smooth cropping/zooming without pixelation
- Better image quality when zoomed to face

The final display is then resized based on your settings.

## Troubleshooting

### Face Detection Not Working

**Symptoms:**
- Face tracking mode active but feed looks like aspect_ratio mode
- No zoom/crop happening

**Solutions:**
1. **Check dependencies**: Ensure `opencv-python` is installed:
   ```bash
   pip install opencv-python
   ```

2. **Check lighting**: Face detection requires adequate lighting

3. **Check angle**: Face must be relatively frontal to be detected

4. **Check logs**: Look in `%APPDATA%/FocusCheck/focus_app.log` for errors

5. **Try fallback**: If face detection fails to initialize, system automatically falls back to aspect_ratio mode

### Camera Feed Too Large

**Problem:** Camera taking up too much space in popup

**Solutions:**
- Reduce `camera_feed_width` and `camera_feed_height` (aspect_ratio mode)
- Reduce `camera_face_max_width` and `camera_face_max_height` (face_tracking mode)
- Recommended safe max: 400x300

### Camera Feed Too Small

**Problem:** Can't see yourself clearly

**Solutions:**
- Increase max dimensions
- Use face_tracking mode with zoom_factor 1.0-1.5
- Ensure good lighting so face is detected

### Face Jumps Around

**Problem:** In face_tracking mode, feed is jittery

**Solutions:**
- Reduce FPS to 15-20 (less frequent face detection)
- Increase `camera_face_zoom_factor` to 2.0+ (wider view = more stable)
- Ensure stable lighting and camera position

### Settings Greyed Out

**Problem:** Can't edit certain camera settings

**Explanation:** This is intentional! Settings are automatically greyed out when they don't apply to the current mode:
- Fixed Size settings only active when `camera_sizing_mode = "fixed_size"`
- Face Tracking settings only active when `camera_sizing_mode = "face_tracking"`

**Solution:** Change the "Sizing mode" dropdown to enable relevant settings

## Performance Considerations

### CPU Usage by Configuration

**Lowest CPU Usage:**
- Mode: `static`
- No face detection
- Result: ~0% CPU (one-time capture)

**Low CPU Usage:**
- Mode: `live`
- Sizing: `fixed_size` or `aspect_ratio`
- FPS: 15
- Result: ~2-5% CPU

**Medium CPU Usage:**
- Mode: `live`
- Sizing: `aspect_ratio`
- FPS: 30
- Result: ~5-10% CPU

**Higher CPU Usage:**
- Mode: `live`
- Sizing: `face_tracking`
- FPS: 15
- Result: ~8-15% CPU (face detection overhead)

**Highest CPU Usage:**
- Mode: `live`
- Sizing: `face_tracking`
- FPS: 30
- Result: ~15-25% CPU

### Optimization Tips

1. **Use static mode** if you don't need live updates
2. **Reduce FPS** to 15-20 for face tracking (still smooth)
3. **Use aspect_ratio mode** if you don't need face tracking
4. **Reduce max dimensions** if you don't need large display

## Privacy & Data

- All camera processing happens **locally** on your computer
- No camera data is transmitted anywhere
- Photos (if enabled) are saved to `%APPDATA%/FocusCheck/camera_photos/`
- You can delete photos at any time
- Face detection runs entirely offline using OpenCV

## Future Enhancements

Potential features for future versions:
- Multiple face tracking (group settings)
- Emotion detection
- Posture analysis
- Eye tracking for focus detection
- Custom face detection models (DNN-based for better accuracy)

---

## Quick Start

**Minimum setup to try the feature:**

1. Install dependencies:
   ```bash
   pip install opencv-python pillow
   ```

2. Open FocusCheck Settings → Behavior tab

3. Enable camera feed and select a mode:
   - **Beginners**: Start with `aspect_ratio` mode
   - **Advanced**: Try `face_tracking` mode

4. Save and trigger a prompt to see it in action!

**Questions?** Check the logs at `%APPDATA%/FocusCheck/focus_app.log`
