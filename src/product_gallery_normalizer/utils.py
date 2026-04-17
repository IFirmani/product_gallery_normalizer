"""Path helpers and image validation utilities."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def collect_images(directory: Path) -> list[Path]:
    """Return a sorted list of PNG files in directory."""
    ...


def is_valid_image(path: Path) -> bool:
    """Return True if path is a supported image file that exists."""
    ...


def apply_edge_feather(img: Image.Image, radius: int) -> Image.Image:
    """Feather the edges of a product image by softening its alpha channel.

    Blurs the alpha channel with a Gaussian kernel of the given radius, then
    takes the per-pixel minimum of the original and blurred alpha values.
    This means interior pixels stay fully opaque while pixels near the
    transparent boundary gradually fade, without ever adding opacity where
    the original image was already transparent.

    Args:
        img: Input image (any mode). Converted to RGBA internally.
        radius: Gaussian blur radius in pixels. 0 disables the effect.

    Returns:
        RGBA Image with softened edges.
    """
    if radius <= 0:
        return img
    img_rgba = img.convert("RGBA")
    r, g, b, a = img_rgba.split()
    a_blurred = a.filter(ImageFilter.GaussianBlur(radius=radius))
    new_alpha = Image.fromarray(
        np.minimum(np.array(a, dtype=np.uint8), np.array(a_blurred, dtype=np.uint8)),
        mode="L",
    )
    result = img_rgba.copy()
    result.putalpha(new_alpha)
    return result
