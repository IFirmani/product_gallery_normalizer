"""Pillow compositing engine: composites a product image over a background."""

from pathlib import Path

from PIL import Image

from product_gallery_normalizer.config import ImageTransform


def composite_image(
    background: Path,
    product: Path,
    transform: ImageTransform,
    canvas_size: int = 1000,
) -> Image.Image:
    """Composite product over background using transform and return the result."""
    ...
