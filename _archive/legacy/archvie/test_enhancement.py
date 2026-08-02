"""
Test the new aggressive enhancement pipeline on the reference image.
"""
import cv2
import numpy as np
import sys

def apply_aggressive_enhancement(frame, intensity=0.8):
    """Apply the new 8-step aggressive enhancement pipeline."""

    if frame is None or frame.size == 0:
        return frame

    enhanced = frame.copy()

    print("Step 1: Bilateral filtering for edge-preserving denoising...")
    d = int(5 + (4 * intensity))
    sigma_color = 50 + (50 * intensity)
    sigma_space = 50 + (50 * intensity)
    enhanced = cv2.bilateralFilter(enhanced, d, sigma_color, sigma_space)

    print("Step 2: Aggressive histogram stretching (percentile)...")
    for c in range(3):
        channel = enhanced[:, :, c]
        p_low = np.percentile(channel, 1)
        p_high = np.percentile(channel, 99)

        if p_high > p_low:
            stretched = np.clip((channel - p_low) * (255.0 / (p_high - p_low)), 0, 255)
            enhanced[:, :, c] = stretched.astype(np.uint8)

    print("Step 3: LAB color space - aggressive CLAHE...")
    lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]

    tile_size = max(4, int(16 - (12 * intensity)))
    clip_limit = 2.5 + (4.5 * intensity)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    l_channel = clahe.apply(l_channel)

    lab[:, :, 0] = l_channel
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    print("Step 4: Adaptive gamma correction...")
    mean_brightness = np.mean(cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY))

    if mean_brightness < 127:
        gamma = 0.8 - (0.3 * intensity)
    else:
        gamma = 1.0 + (0.2 * intensity)

    inv_gamma = 1.0 / gamma
    gamma_table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    enhanced = cv2.LUT(enhanced, gamma_table)

    print("Step 5: High-pass sharpening (unsharp mask)...")
    gaussian_kernel = int(3 + (6 * intensity))
    if gaussian_kernel % 2 == 0:
        gaussian_kernel += 1

    gaussian_blur = cv2.GaussianBlur(enhanced, (gaussian_kernel, gaussian_kernel), 0)
    high_pass = cv2.subtract(enhanced, gaussian_blur)

    sharp_amount = 1.5 + (2.5 * intensity)
    enhanced = cv2.addWeighted(enhanced, 1.0, high_pass, sharp_amount, 0)
    enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)

    print("Step 6: Detail enhancement using Laplacian...")
    if intensity > 0.5:
        laplacian = cv2.Laplacian(enhanced, cv2.CV_64F)
        laplacian_amount = 0.3 * intensity
        enhanced = np.clip(enhanced + laplacian_amount * laplacian, 0, 255).astype(np.uint8)

    print("Step 7: Saturation boost...")
    hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
    saturation_boost = 1.0 + (0.5 * intensity)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_boost, 0, 255)
    enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    print("Step 8: Final contrast boost...")
    contrast_alpha = 1.0 + (0.3 * intensity)
    contrast_beta = -10 * intensity
    enhanced = cv2.convertScaleAbs(enhanced, alpha=contrast_alpha, beta=int(contrast_beta))

    return enhanced


if __name__ == "__main__":
    # Load the reference image
    input_path = "Untitled picture.png"

    print(f"Loading image: {input_path}")
    frame = cv2.imread(input_path)

    if frame is None:
        print(f"ERROR: Could not load image: {input_path}")
        sys.exit(1)

    print(f"Image loaded: {frame.shape}")
    print(f"Original - Min: {frame.min()}, Max: {frame.max()}, Mean: {frame.mean():.1f}")

    # Test at different intensity levels
    intensities = [0.5, 0.8, 1.0]

    for intensity in intensities:
        print(f"\n{'='*60}")
        print(f"Testing with intensity: {intensity * 100}%")
        print(f"{'='*60}")

        enhanced = apply_aggressive_enhancement(frame, intensity)

        print(f"Enhanced - Min: {enhanced.min()}, Max: {enhanced.max()}, Mean: {enhanced.mean():.1f}")

        # Save output
        output_path = f"enhanced_intensity_{int(intensity*100)}.png"
        cv2.imwrite(output_path, enhanced)
        print(f"Saved: {output_path}")

        # Create side-by-side comparison
        comparison = np.hstack([frame, enhanced])
        comparison_path = f"comparison_intensity_{int(intensity*100)}.png"
        cv2.imwrite(comparison_path, comparison)
        print(f"Saved comparison: {comparison_path}")

    print("\n" + "="*60)
    print("Enhancement test complete!")
    print("="*60)
    print(f"\nGenerated {len(intensities) * 2} output images:")
    for intensity in intensities:
        print(f"  - enhanced_intensity_{int(intensity*100)}.png")
        print(f"  - comparison_intensity_{int(intensity*100)}.png")
