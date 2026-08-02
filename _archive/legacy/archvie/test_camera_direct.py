"""Direct camera access test."""

import cv2
import numpy as np

print("=" * 60)
print("DIRECT CAMERA TEST")
print("=" * 60)

# Test camera 0
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow backend
print(f"\n1. Opening camera with DirectShow backend...")

if cap.isOpened():
    print("   Camera opened successfully")

    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Capture a frame
    ret, frame = cap.read()

    if ret and frame is not None:
        print("   Frame captured successfully!")
        print(f"   Frame shape: {frame.shape}")
        print(f"   Frame min/max: {np.min(frame)} / {np.max(frame)}")

        # Save the frame
        cv2.imwrite("test_frame.jpg", frame)
        print("   Saved frame to test_frame.jpg")

        # Display for 3 seconds
        cv2.imshow("Camera Test", frame)
        cv2.waitKey(3000)
        cv2.destroyAllWindows()
    else:
        print(f"   ERROR: Could not read frame! Return code: {ret}")
        print(f"   Frame is None: {frame is None}")

    cap.release()
else:
    print("   ERROR: Could not open camera!")

print("\nTest completed!")
