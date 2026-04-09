"""Background removal by color using Euclidean distance with feathered edges."""

import numpy as np
from PIL import Image


def remove_background_by_color(
    image: Image.Image,
    target_color: tuple[int, int, int],
    tolerance: int = 30,
    softness: int = 10,
) -> Image.Image:
    """Remove pixels near target_color, with a feathered edge transition.

    Args:
        image: Input image, any mode. Converted to RGBA internally.
        target_color: RGB color to remove (e.g. (255, 255, 255) for white).
        tolerance: Pixels within this Euclidean RGB distance become fully
                   transparent (alpha = 0).
        softness: Width of the transition band beyond tolerance, in distance
                  units. Pixels in this band get linearly interpolated alpha
                  from 0 to 255. Set to 0 for a hard edge.

    Returns:
        RGBA Image with the background color removed.
    """
    arr: np.ndarray = np.array(image.convert("RGBA"), dtype=np.uint8).copy()

    rgb = arr[:, :, :3].astype(np.float32)
    diff = rgb - np.array(target_color, dtype=np.float32)
    dist = np.sqrt((diff**2).sum(axis=2))

    if softness > 0:
        new_alpha = ((dist - tolerance) / softness * 255).clip(0, 255)
    else:
        new_alpha = np.where(dist <= tolerance, 0.0, 255.0)

    # Preserve existing transparency by multiplying normalised alphas
    original_alpha = arr[:, :, 3].astype(np.float32)
    combined = (new_alpha / 255.0) * original_alpha
    arr[:, :, 3] = combined.clip(0, 255).astype(np.uint8)

    return Image.fromarray(arr, "RGBA")
