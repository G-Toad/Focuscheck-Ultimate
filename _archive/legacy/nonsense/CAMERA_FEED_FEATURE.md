# Camera Feed Feature - FocusCheck

## Overview

The Camera Feed feature adds a powerful self-reflection mechanism to FocusCheck by displaying a live or static camera view in the popup window. This feature is designed to invoke self-awareness and accountability by showing users their own reflection when they're prompted to evaluate their activities.

## Purpose

This feature serves multiple psychological functions:

1. **Self-Reflection**: Seeing yourself creates a moment of self-awareness that can break distraction patterns
2. **Accountability**: The presence of the camera creates a psychological "witness" effect
3. **Photo Logging**: Optional photo capture on button clicks creates a visceral record of decisions
4. **Engagement Alternative**: Provides a less intrusive alternative to spam checks and challenge prompts while maintaining engagement

## Installation Requirements

To use the camera feed feature, you need to install two additional Python packages:

```bash
pip install opencv-python pillow
```

- **opencv-python** (`cv2`): For camera access and frame capture
- **pillow** (`PIL`): For image processing and display in Tkinter

## Configuration Settings

All camera feed settings are configurable through the FocusCheck settings. Here are the available options:

### Basic Settings

```json
{
  "camera_feed_enabled": false,
  "camera_feed_mode": "live",
  "camera_capture_on_click": false
}
```

- **`camera_feed_enabled`** (boolean, default: `false`)
  - Enables or disables the camera feed feature
  - Set to `true` to activate the camera feed

- **`camera_feed_mode`** (string, default: `"live"`)
  - Controls the camera display mode
  - Options:
    - `"live"`: Continuous live feed from the camera
    - `"static"`: Single snapshot taken when popup first appears (frozen image)
  - Static mode uses less resources and may be less distracting

- **`camera_capture_on_click`** (boolean, default: `false`)
  - Enables photo capture when either button is clicked
  - Photos are saved to `%APPDATA%/FocusCheck/camera_photos/` (Windows)
  - Filenames include timestamp and choice: `20250102_143045_123456_studying.jpg`
  - Purpose: Creates accountability logs and prevents users from dismissing the system as "easy to ignore"

### Display Settings

```json
{
  "camera_feed_width": 320,
  "camera_feed_height": 240,
  "camera_device_index": 0,
  "camera_fps": 30
}
```

- **`camera_feed_width`** (integer, default: `320`)
  - Width of camera display in pixels
  - Range: 160-1920
  - Smaller sizes reduce window clutter

- **`camera_feed_height`** (integer, default: `240`)
  - Height of camera display in pixels
  - Range: 120-1080
  - Aspect ratio: Consider using 4:3 or 16:9 ratios (e.g., 320x240, 640x480, 640x360)

- **`camera_device_index`** (integer, default: `0`)
  - Camera device to use
  - `0` = default/primary camera
  - `1`, `2`, etc. = additional cameras if available
  - If you have multiple cameras, change this to select which one to use

- **`camera_fps`** (integer, default: `30`)
  - Frame rate for live feed updates (frames per second)
  - Range: 1-60
  - Higher values = smoother feed but more CPU usage
  - 15-30 FPS is usually sufficient
  - Only applies in `"live"` mode

## Usage Examples

### Example 1: Enable Basic Camera Feed

Enable a live camera feed with default settings:

```json
{
  "camera_feed_enabled": true
}
```

This will show a 320x240 live feed at 30 FPS in the popup window.

### Example 2: Static Photo Mode

Show a frozen snapshot instead of live feed (less distracting, lower resource usage):

```json
{
  "camera_feed_enabled": true,
  "camera_feed_mode": "static"
}
```

### Example 3: Full Accountability Setup

Enable camera with photo capture for maximum accountability:

```json
{
  "camera_feed_enabled": true,
  "camera_feed_mode": "live",
  "camera_capture_on_click": true,
  "camera_feed_width": 480,
  "camera_feed_height": 360
}
```

This configuration:
- Shows a live 480x360 camera feed
- Captures a photo every time you click "Studying" or "Wasting time"
- Saves photos to your FocusCheck data directory for review

### Example 4: Minimal Resource Usage

Optimize for lower CPU usage:

```json
{
  "camera_feed_enabled": true,
  "camera_feed_mode": "static",
  "camera_feed_width": 240,
  "camera_feed_height": 180,
  "camera_fps": 15
}
```

## Layout and Sizing Considerations

The camera feed is carefully positioned in the popup window to maintain good visual hierarchy:

1. **Positioning**: Camera feed appears below buttons and other elements (task panel, time info, etc.)
2. **Styling**: Black background with subtle border, labeled "Reflection"
3. **Sizing**: The popup window automatically adjusts to accommodate the camera feed
4. **Recommendation**: Keep camera dimensions moderate (320x240 or 480x360) to prevent the window from becoming unwieldy

### Recommended Layouts

**Balanced Layout** (recommended for most users):
```json
{
  "camera_feed_width": 320,
  "camera_feed_height": 240,
  "show_time_info": true,
  "encouragement_enabled": true
}
```

**Minimal Layout** (reduce clutter):
```json
{
  "camera_feed_width": 240,
  "camera_feed_height": 180,
  "show_time_info": false,
  "encouragement_enabled": false,
  "hide_wasting_button": true
}
```

**Maximum Presence** (strong accountability):
```json
{
  "camera_feed_width": 640,
  "camera_feed_height": 480,
  "camera_capture_on_click": true,
  "show_time_info": true,
  "encouragement_enabled": true
}
```

## Photo Logs

When `camera_capture_on_click` is enabled, photos are saved to:

- **Windows**: `%APPDATA%\FocusCheck\camera_photos\`
- **Other**: `<script_directory>/camera_photos/`

### Filename Format

```
YYYYMMDD_HHMMSS_microseconds_choice.jpg
```

Example: `20250102_143045_123456_studying.jpg`

- Timestamp allows chronological sorting
- Choice suffix (`studying` or `wasting_time`) for quick filtering
- JPEG format for reasonable file sizes

### Managing Photo Logs

Photos accumulate over time. Consider:

1. **Periodic Review**: Review photos weekly to reflect on patterns
2. **Manual Cleanup**: Delete old photos you don't need
3. **Disk Space**: Each photo is typically 50-200 KB depending on resolution
4. **Privacy**: Photos are stored locally and never transmitted

## Troubleshooting

### Camera Not Appearing

1. **Check settings**: Ensure `camera_feed_enabled` is `true`
2. **Check dependencies**: Run `pip install opencv-python pillow`
3. **Check logs**: Look in `%APPDATA%/FocusCheck/focus_app.log` for errors
4. **Camera permissions**: Ensure FocusCheck has camera access (Windows Settings → Privacy → Camera)
5. **Camera in use**: Close other applications using the camera (Teams, Zoom, etc.)

### Wrong Camera Showing

If you have multiple cameras and the wrong one appears:

```json
{
  "camera_device_index": 1  // Try 1, 2, 3, etc. to find the right camera
}
```

### Performance Issues

If the camera feed causes lag:

1. **Reduce FPS**:
   ```json
   {"camera_fps": 15}
   ```

2. **Use static mode**:
   ```json
   {"camera_feed_mode": "static"}
   ```

3. **Reduce resolution**:
   ```json
   {
     "camera_feed_width": 240,
     "camera_feed_height": 180
   }
   ```

### Camera Feed Shows Black Screen

1. **Camera blocked**: Check camera privacy settings
2. **Driver issues**: Update camera drivers
3. **Hardware problem**: Test camera in another application
4. **Lighting**: Ensure adequate lighting for camera to activate

## Privacy Considerations

- **Local Only**: All photos are stored locally on your computer
- **No Transmission**: FocusCheck does not transmit camera data anywhere
- **Your Control**: You can disable the feature or delete photos at any time
- **Access**: Only you have access to the photos (standard file permissions apply)

## Technical Details

### Camera Initialization

1. Camera initializes when popup appears (if enabled)
2. Uses OpenCV's `VideoCapture` with specified device index
3. Sets requested resolution (camera may adjust to nearest supported resolution)
4. In static mode, captures one frame immediately
5. In live mode, starts update loop at specified FPS

### Resource Management

- Camera is properly released when popup closes
- Update timers are cancelled on dialog destruction
- No memory leaks from retained frames (PIL Images are garbage collected)
- Minimal CPU usage in static mode (no continuous capture)

### Error Handling

- Feature degrades gracefully if dependencies unavailable
- Camera initialization failures are logged but don't crash the app
- If camera can't be opened, popup continues without camera feed
- Photo capture failures are logged but don't interrupt the user flow

## Design Philosophy

The camera feed feature aligns with FocusCheck's psychological approach:

1. **Non-Intrusive Alternative**: Provides engagement without requiring text responses
2. **Visceral Accountability**: Photos create tangible evidence of decisions
3. **Self-Awareness**: Seeing yourself triggers metacognition
4. **Configurable Intensity**: From subtle static image to full live feed with photo logging
5. **Respectful**: Optional and easily disabled, respects user privacy

## Recommendations

### For New Users

Start with a gentle introduction:

```json
{
  "camera_feed_enabled": true,
  "camera_feed_mode": "static",
  "camera_feed_width": 320,
  "camera_feed_height": 240,
  "camera_capture_on_click": false
}
```

### For Serious Users

Full accountability mode:

```json
{
  "camera_feed_enabled": true,
  "camera_feed_mode": "live",
  "camera_feed_width": 480,
  "camera_feed_height": 360,
  "camera_capture_on_click": true,
  "challenge_system_enabled": false,  // Use camera instead of challenges
  "spam_detection_enabled": false     // Let camera provide the accountability
}
```

### Alternative to Challenge System

The camera feed can replace challenge prompts for users who find them irritating:

```json
{
  "camera_feed_enabled": true,
  "camera_capture_on_click": true,
  "challenge_system_enabled": false,
  "focus_prompt_ask_doing": false,
  "wasting_prompt_ask_what": false
}
```

This configuration provides accountability through the camera instead of requiring typed reflections.

## Future Enhancements

Potential future improvements to consider:

1. **Face detection**: Ensure user is actually present
2. **Emotion detection**: Log emotional state for pattern analysis
3. **Posture analysis**: Detect slouching or poor ergonomics
4. **Session highlights**: Automatically compile photos into daily review
5. **Multiple cameras**: Show different angles simultaneously
6. **Video clips**: Record short clips instead of static photos

---

## Quick Start

**Minimal setup to try the feature:**

1. Install dependencies: `pip install opencv-python pillow`
2. Edit settings (Settings → Camera Feed or edit `focus_settings.json`)
3. Set `camera_feed_enabled` to `true`
4. Restart FocusCheck or trigger a new prompt
5. Your camera feed should appear below the buttons!

**Questions or issues?** Check the logs at `%APPDATA%/FocusCheck/focus_app.log`
