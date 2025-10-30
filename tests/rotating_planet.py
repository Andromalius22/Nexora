from PIL import Image, ImageEnhance
import imageio.v2 as imageio
import numpy as np

# === SETTINGS ===
image_path = "assets/planets/Magma_05-256x256.png"      # Input image
output_gif = "planet_axis_rotation.gif"
num_frames = 60                # Number of frames in full rotation
duration_per_frame = 0.05      # Seconds per frame
resize_to = 512                # Resize (keep square)
apply_shading = True           # Add light falloff for 3D illusion

# === LOAD AND PREPARE IMAGE ===
img = Image.open(image_path).convert("RGBA")
if resize_to:
    img = img.resize((resize_to, resize_to), Image.LANCZOS)

w, h = img.size
planet = np.array(img)

frames = []
x = np.linspace(-1, 1, w)
y = np.linspace(-1, 1, h)
xx, yy = np.meshgrid(x, y)
mask = xx**2 + yy**2 <= 1  # circular mask for planet edges

# Optional shading for 3D effect
if apply_shading:
    shading = np.clip(0.3 + 0.7 * np.sqrt(1 - np.clip(xx**2 + yy**2, 0, 1)), 0, 1)
else:
    shading = np.ones_like(xx)

# === GENERATE FRAMES ===
for i in range(num_frames):
    shift = int(w * i / num_frames)
    shifted = np.roll(planet, shift, axis=1)

    # Create spherical projection
    sphere = np.zeros_like(shifted)
    for xi in range(w):
        # horizontal compression using cosine for sphere curvature
        src_x = int((np.sin(np.pi * (xi / w - 0.5)) * 0.5 + 0.5) * w)
        sphere[:, xi] = shifted[:, src_x % w]

    # Apply circular mask & shading
    sphere = (sphere * shading[..., None]).astype(np.uint8)
    sphere[~mask] = 0  # transparent outside circle
    frame = Image.fromarray(sphere, "RGBA")
    frames.append(frame)

# === SAVE AS GIF ===
frames[0].save(
    output_gif,
    save_all=True,
    append_images=frames[1:],
    duration=int(duration_per_frame * 1000),
    loop=0,
    disposal=2,
)

print(f"✅ Saved realistic rotating planet GIF as {output_gif}")
