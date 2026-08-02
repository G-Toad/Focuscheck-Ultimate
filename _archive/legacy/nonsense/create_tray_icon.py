"""
Generate the FocusCheck tray icon - orange eye with triangles
"""
from PIL import Image, ImageDraw

# Create a 256x256 image with transparent background
size = 256
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Orange/gold color
orange = (237, 139, 0, 255)  # RGB orange
white = (255, 255, 255, 255)

# Draw top triangle (pointing up)
top_triangle = [
    (size // 2, 10),  # top point
    (size // 2 - 40, 70),  # bottom left
    (size // 2 + 40, 70)   # bottom right
]
draw.polygon(top_triangle, fill=orange)

# Draw eye shape (almond/ellipse)
eye_top = 85
eye_bottom = 170
eye_left = 50
eye_right = 206

# Outer eye shape
draw.ellipse([eye_left, eye_top, eye_right, eye_bottom], fill=orange)

# Inner white part of eye
inner_margin = 15
draw.ellipse([eye_left + inner_margin, eye_top + inner_margin,
              eye_right - inner_margin, eye_bottom - inner_margin], fill=white)

# Pupil (iris - orange circle in center)
pupil_size = 35
center_x = size // 2
center_y = (eye_top + eye_bottom) // 2
draw.ellipse([center_x - pupil_size, center_y - pupil_size,
              center_x + pupil_size, center_y + pupil_size], fill=orange)

# Draw bottom triangle (pointing down)
bottom_triangle = [
    (size // 2, 246),  # bottom point
    (size // 2 - 40, 186),  # top left
    (size // 2 + 40, 186)   # top right
]
draw.polygon(bottom_triangle, fill=orange)

# Save as PNG
output_path = r'C:\Users\singh\Documents\DEVRECON\Current\focuscheck\tray_icon.png'
img.save(output_path, 'PNG')
print(f"Icon saved to: {output_path}")

# Also save a smaller version for better tray display
small_img = img.resize((64, 64), Image.Resampling.LANCZOS)
small_path = r'C:\Users\singh\Documents\DEVRECON\Current\focuscheck\tray_icon_small.png'
small_img.save(small_path, 'PNG')
print(f"Small icon saved to: {small_path}")
