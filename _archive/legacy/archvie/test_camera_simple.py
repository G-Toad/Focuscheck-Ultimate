"""Simple camera test to check basic camera availability."""

import cv2
import sys

print("=" * 60)
print("SIMPLE CAMERA TEST")
print("=" * 60)

# Try different camera indices
for idx in range(3):
    print(f"\n{idx+1}. Testing camera index {idx}...")
    cap = cv2.VideoCapture(idx)

    if cap.isOpened():
        print(f"   ✓ Camera {idx} opened successfully")

        # Try to read a frame
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"   ✓ Frame captured successfully")
            print(f"   Frame shape: {frame.shape}")
            print(f"   Frame type: {frame.dtype}")

            # Display the frame
            cv2.imshow(f"Camera {idx} Test", frame)
            print(f"   Press any key to continue...")
            cv2.waitKey(3000)  # Wait 3 seconds
            cv2.destroyAllWindows()
        else:
            print(f"   ✗ Failed to capture frame (Error code: {ret})")

        cap.release()
    else:
        print(f"   ✗ Could not open camera {idx}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)

# Additional diagnostics
print("\nDiagnostics:")
print(f"OpenCV version: {cv2.__version__}")
print(f"OpenCV build info:")
print(cv2.getBuildInformation())
