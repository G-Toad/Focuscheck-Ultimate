"""Test camera functionality to debug black screen issue."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import numpy as np
from focuscheck.settings.defaults import DEFAULT_SETTINGS

print("=" * 60)
print("CAMERA DEBUG TEST")
print("=" * 60)

# Check if OpenCV is available
print(f"\n1. OpenCV available: {cv2 is not None}")
print(f"   OpenCV version: {cv2.__version__}")

# Check camera settings
print(f"\n2. DEFAULT_SETTINGS camera values:")
print(f"   camera_feed_enabled: {DEFAULT_SETTINGS.get('camera_feed_enabled', False)}")
print(f"   camera_invert_colors: {DEFAULT_SETTINGS.get('camera_invert_colors', False)}")
print(f"   camera_adaptive_brightness_enabled: {DEFAULT_SETTINGS.get('camera_adaptive_brightness_enabled', False)}")
print(f"   camera_adaptive_brightness_overexposed: {DEFAULT_SETTINGS.get('camera_adaptive_brightness_overexposed', False)}")
print(f"   camera_adaptive_brightness_dim: {DEFAULT_SETTINGS.get('camera_adaptive_brightness_dim', False)}")
print(f"   camera_adaptive_brightness_intensity: {DEFAULT_SETTINGS.get('camera_adaptive_brightness_intensity', 0.5)}")

# Test camera capture
print(f"\n3. Testing camera capture...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("   ERROR: Could not open camera!")
    sys.exit(1)

print(f"   Camera opened successfully!")

# Capture a frame
ret, frame = cap.read()
if not ret or frame is None:
    print("   ERROR: Could not read frame from camera!")
    cap.release()
    sys.exit(1)

print(f"   Frame captured successfully!")
print(f"   Frame shape: {frame.shape}")
print(f"   Frame dtype: {frame.dtype}")
print(f"   Frame min/max values: {np.min(frame)} / {np.max(frame)}")
print(f"   Frame mean: {np.mean(frame):.2f}")

# Test with camera effects disabled (baseline)
print(f"\n4. Testing frame processing with ALL EFFECTS DISABLED...")
test_settings_disabled = {
    "camera_invert_colors": False,
    "camera_adaptive_brightness_enabled": False,
    "camera_adaptive_brightness_overexposed": False,
    "camera_adaptive_brightness_dim": False,
    "camera_adaptive_brightness_intensity": 0.5,
    "camera_flip_horizontal": True,
    "camera_feed_width": 320,
    "camera_feed_height": 240,
    "camera_sizing_mode": "aspect_ratio",
}

# Simple resize (no effects)
resized = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_LANCZOS4)
print(f"   Resized frame shape: {resized.shape}")
print(f"   Resized frame min/max: {np.min(resized)} / {np.max(resized)}")
print(f"   Resized frame mean: {np.mean(resized):.2f}")

# Test color inversion
print(f"\n5. Testing COLOR INVERSION effect...")
inverted = cv2.bitwise_not(resized)
print(f"   Inverted frame min/max: {np.min(inverted)} / {np.max(inverted)}")
print(f"   Inverted frame mean: {np.mean(inverted):.2f}")

# Test adaptive brightness
print(f"\n6. Testing ADAPTIVE BRIGHTNESS effect...")
lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
l_channel = lab[:, :, 0]
mean_brightness = np.mean(l_channel)
std_brightness = np.std(l_channel)
print(f"   LAB L-channel mean brightness: {mean_brightness:.2f}")
print(f"   LAB L-channel std: {std_brightness:.2f}")

# Simulate adaptive brightness logic
overexposed_threshold = 180
underexposed_threshold = 70
alpha = 1.0
beta = 0

if mean_brightness > overexposed_threshold:
    over_amount = min(1.0, (mean_brightness - overexposed_threshold) / (255 - overexposed_threshold))
    correction_strength = over_amount * 0.5
    alpha = 1.0 + (0.3 * correction_strength)
    beta = int(-30 * correction_strength)
    print(f"   Detected OVEREXPOSED (mean={mean_brightness:.2f} > {overexposed_threshold})")
    print(f"   Correction: alpha={alpha:.3f}, beta={beta}")
elif mean_brightness < underexposed_threshold:
    under_amount = min(1.0, (underexposed_threshold - mean_brightness) / underexposed_threshold)
    correction_strength = under_amount * 0.5
    alpha = 1.0 + (0.5 * correction_strength)
    beta = int(40 * correction_strength)
    print(f"   Detected UNDEREXPOSED (mean={mean_brightness:.2f} < {underexposed_threshold})")
    print(f"   Correction: alpha={alpha:.3f}, beta={beta}")
else:
    print(f"   Normal lighting (mean={mean_brightness:.2f})")

if alpha != 1.0 or beta != 0:
    enhanced = cv2.convertScaleAbs(resized, alpha=alpha, beta=beta)
    print(f"   Enhanced frame min/max: {np.min(enhanced)} / {np.max(enhanced)}")
    print(f"   Enhanced frame mean: {np.mean(enhanced):.2f}")

    # Check if frame is completely black
    if np.max(enhanced) == 0:
        print(f"   WARNING: Enhanced frame is COMPLETELY BLACK!")
    else:
        print(f"   Enhanced frame looks OK")

# Test combination of effects (CRITICAL TEST)
print(f"\n7. Testing COMBINED EFFECTS (brightness + inversion)...")
test_frame = resized.copy()

# First apply brightness
if alpha != 1.0 or beta != 0:
    test_frame = cv2.convertScaleAbs(test_frame, alpha=alpha, beta=beta)
    print(f"   After brightness: min/max = {np.min(test_frame)} / {np.max(test_frame)}, mean = {np.mean(test_frame):.2f}")

# Then apply inversion
if False:  # Would invert if enabled
    test_frame = cv2.bitwise_not(test_frame)
    print(f"   After inversion: min/max = {np.min(test_frame)} / {np.max(test_frame)}, mean = {np.mean(test_frame):.2f}")

# Final check
if np.max(test_frame) == 0:
    print(f"\n   CRITICAL ERROR: Combined effects resulted in BLACK FRAME!")
else:
    print(f"\n   Combined effects frame looks OK")

# Release camera
cap.release()

# Create GUI to display frames
print(f"\n8. Creating visual test window...")

class CameraDebugWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Camera Debug Test")
        self.configure(bg="#111")

        # Create frames to show different stages
        container = tk.Frame(self, bg="#111")
        container.pack(padx=20, pady=20)

        tk.Label(container, text="Camera Debug Test", fg="#eaeaea", bg="#111",
                font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        # Original frame
        tk.Label(container, text="1. Original Camera Feed", fg="#aaa", bg="#111",
                font=("Segoe UI", 10, "bold")).pack()
        self.label1 = tk.Label(container, bg="#000")
        self.label1.pack(pady=5)

        # Resized frame
        tk.Label(container, text="2. After Resize (No Effects)", fg="#aaa", bg="#111",
                font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        self.label2 = tk.Label(container, bg="#000")
        self.label2.pack(pady=5)

        # With adaptive brightness
        tk.Label(container, text="3. With Adaptive Brightness", fg="#aaa", bg="#111",
                font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        self.label3 = tk.Label(container, bg="#000")
        self.label3.pack(pady=5)

        # With inversion
        tk.Label(container, text="4. With Color Inversion", fg="#aaa", bg="#111",
                font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        self.label4 = tk.Label(container, bg="#000")
        self.label4.pack(pady=5)

        # Status label
        self.status = tk.Label(container, text="", fg="#0f0", bg="#111",
                              font=("Courier", 9))
        self.status.pack(pady=(10, 0))

        # Start camera feed
        self.cap = cv2.VideoCapture(0)
        self.update_feed()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_feed(self):
        ret, frame = self.cap.read()
        if ret and frame is not None:
            # 1. Original (small)
            small_orig = cv2.resize(frame, (160, 120))
            self.display_frame(self.label1, small_orig)

            # 2. Resized (no effects)
            resized = cv2.resize(frame, (320, 240))
            self.display_frame(self.label2, resized)

            # 3. With adaptive brightness
            test_bright = resized.copy()
            if alpha != 1.0 or beta != 0:
                test_bright = cv2.convertScaleAbs(test_bright, alpha=alpha, beta=beta)
            self.display_frame(self.label3, test_bright)

            # 4. With inversion
            test_inv = resized.copy()
            test_inv = cv2.bitwise_not(test_inv)
            self.display_frame(self.label4, test_inv)

            # Status
            self.status.config(text=f"Frame: {frame.shape} | Mean: {np.mean(frame):.1f} | " +
                                   f"Brightness: {mean_brightness:.1f} | " +
                                   f"Correction: α={alpha:.2f} β={beta}")

        self.after(33, self.update_feed)

    def display_frame(self, label, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        photo = ImageTk.PhotoImage(image=img)
        label.configure(image=photo)
        label.image = photo

    def on_close(self):
        self.cap.release()
        self.destroy()

print("Starting GUI...")
app = CameraDebugWindow()
app.mainloop()

print("\nTest completed!")
