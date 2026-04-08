"""Pillow compositing engine: composites a product image over a background."""

import logging
from pathlib import Path

from PIL import Image

from product_gallery_normalizer.config import ImageTransform

logger = logging.getLogger(__name__)

_CANVAS_SIZE: tuple[int, int] = (1000, 1000)


def composite_image(
    background: Path,
    product: Path,
    transform: ImageTransform,
) -> Image.Image:
    """Composite *product* over *background* using *transform* and return the result.

    The background is always resized to 1000×1000. The product is scaled and
    rotated according to *transform* then pasted at ``(transform.x, transform.y)``.
    The composited image is returned; nothing is written to disk.
    """
    if not background.is_file():
        raise ValueError(f"Background path is not a valid file: {background}")
    if not product.is_file():
        raise ValueError(f"Product path is not a valid file: {product}")

    bg = Image.open(background).convert("RGBA").resize(_CANVAS_SIZE, Image.LANCZOS)

    prod = Image.open(product).convert("RGBA")

    # Apply scale
    w, h = prod.size
    new_w = max(1, int(w * transform.scale))
    new_h = max(1, int(h * transform.scale))
    prod = prod.resize((new_w, new_h), Image.LANCZOS)

    # Apply rotation (PIL is counter-clockwise; canvas is clockwise → negate)
    prod = prod.rotate(-transform.rotation, expand=True)

    # Paste with alpha mask
    paste_x = int(transform.x)
    paste_y = int(transform.y)
    bg.paste(prod, (paste_x, paste_y), prod)

    logger.debug("Composited %s at (%d, %d) rot=%.1f scale=%.2f", product.name, paste_x, paste_y, transform.rotation, transform.scale)
    return bg
