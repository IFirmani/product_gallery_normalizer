---
mode: agent
description: Implement the Pillow compositing engine (compositor.py)
---

# Implement compositor.py

No PySide6 imports allowed.

```python
def composite_image(
    background: Path,
    product: Path,
    transform: ImageTransform,
    canvas_size: int = 1000,
) -> Image.Image:
```

## Steps

1. Open background, resize to `canvas_size×canvas_size` (LANCZOS)
2. Open product (RGBA). Apply scale:
   `new_size = (int(w * transform.scale), int(h * transform.scale))`
3. Apply rotation: `product.rotate(transform.rotation, expand=True, resample=BICUBIC)`
4. Paste product onto background at `(int(transform.x), int(transform.y))` using alpha mask
5. Return the composited PIL Image (do not save)

All Pillow operations must preserve alpha. Background converted to RGBA before paste.
