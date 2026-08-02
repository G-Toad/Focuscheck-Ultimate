"""
Test just the slider UI without camera.
"""
import tkinter as tk

root = tk.Tk()
root.title("Slider Test")
root.configure(bg="#111")
root.geometry("900x700")

main_frame = tk.Frame(root, bg="#111")
main_frame.pack(fill="both", expand=True, padx=20, pady=20)

# Title
title = tk.Label(main_frame, text="Slider Test", fg="#fff", bg="#111",
                font=("Segoe UI", 14, "bold"))
title.pack(pady=10)

# Controls container
controls = tk.Frame(main_frame, bg="#1a1a1a", highlightthickness=2,
                   highlightbackground="#333")
controls.pack(fill="both", expand=False, pady=10)

controls_inner = tk.Frame(controls, bg="#1a1a1a")
controls_inner.pack(fill="both", expand=True, padx=15, pady=15)

# Create sliders
sliders_frame = tk.Frame(controls_inner, bg="#1a1a1a")
sliders_frame.pack(fill="x")

left_col = tk.Frame(sliders_frame, bg="#1a1a1a")
left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

right_col = tk.Frame(sliders_frame, bg="#1a1a1a")
right_col.pack(side="left", fill="both", expand=True)

def create_slider(parent, name):
    frame = tk.Frame(parent, bg="#1a1a1a")
    frame.pack(fill="x", pady=8)

    label = tk.Label(frame, text=name, fg="#fff", bg="#1a1a1a",
                    font=("Segoe UI", 9, "bold"))
    label.pack(anchor="w")

    var = tk.DoubleVar(value=0.5)
    slider = tk.Scale(frame, from_=0.0, to=1.0, resolution=0.01,
                     orient="horizontal", variable=var,
                     bg="#2a2a2a", fg="#fff", troughcolor="#000",
                     highlightthickness=0, sliderlength=30,
                     length=300, width=20,
                     font=("Segoe UI", 8))
    slider.pack(fill="x", pady=(2, 0), ipady=5)

    hint = tk.Label(frame, text="Test slider", fg="#666", bg="#1a1a1a",
                   font=("Segoe UI", 7, "italic"))
    hint.pack(anchor="w")

# Left column
create_slider(left_col, "Brightness")
create_slider(left_col, "Contrast")
create_slider(left_col, "Saturation")

# Right column
create_slider(right_col, "Sharpness")
create_slider(right_col, "Gamma")
create_slider(right_col, "Tint")

# Info label
info = tk.Label(main_frame, text="If you can see 6 sliders above, the UI is working!",
               fg="#0f0", bg="#111", font=("Segoe UI", 12, "bold"))
info.pack(pady=20)

root.mainloop()
