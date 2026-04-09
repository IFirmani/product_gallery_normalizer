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

## ImageTransform convention
`transform.x` / `transform.y` are the **scene coordinates of the product image
centre** (default 500, 500 = canvas centre). Convert to a paste offset:
```python
paste_x = int(transform.x - (scaled_w / 2))
paste_y = int(transform.y - (scaled_h / 2))
```

## Steps

1. Open background, resize to `canvas_size x canvas_size` (LANCZOS), convert to RGBA.
2. Open product as RGBA.
3. Apply scale: `new_size = (int(w * transform.scale), int(h * transform.scale))`
4. Apply rotation: `product.rotate(-transform.rotation, expand=True, resample=BICUBIC)`
   (negate because Qt rotation is clockwise, Pillow is counter-clockwise)
5. Compute paste offset from the centre convention above.
6. Paste product onto background at `(paste_x, paste_y)` using the alpha channel as mask.
7. Return the composited PIL Image (do not save).

All Pillow operations must preserve alpha.
