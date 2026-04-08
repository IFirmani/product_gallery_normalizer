---
mode: agent
description: Implement the Pillow compositing engine (compositor.py)
---

# Implement compositor.py

## Context

The stub `src/product_gallery_normalizer/compositor.py` exists.
`ImageTransform` is defined in `config.py` with fields `x`, `y`, `rotation`
(degrees, float), and `scale` (float, default 1.0).

## Goal

Implement `composite_image` so the exporter and tests can use it.

## Function signature

```python
def composite_image(
    background: Path,
    product: Path,
    transform: ImageTransform,
) -> Image.Image:
```

## Requirements

1. Open `background` with Pillow, resize to `1000×1000` using `LANCZOS`,
   convert to `RGBA`.
2. Open `product` with Pillow, convert to `RGBA`.
3. Apply `transform.scale` — resize product to
   `(int(w * scale), int(h * scale))` using `LANCZOS`.
4. Apply `transform.rotation` — rotate by `-transform.rotation` degrees
   (negative because PIL rotates counter-clockwise; canvas rotates clockwise),
   `expand=True`, fill with transparent pixels.
5. Paste the product onto the background at `(int(transform.x), int(transform.y))`
   using the product's alpha channel as a mask.
6. Return the composited `Image.Image` (do **not** save to disk).

## Constraints

- No PySide6 imports — this is a pure Pillow module
- All logging via `logging.getLogger(__name__)`
- Raise `ValueError` if either path does not point to a valid image file
- Do not modify files on disk
