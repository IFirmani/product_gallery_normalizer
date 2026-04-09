"""Procedural background generation: radial gradient with solid centre."""

import numpy as np
from PIL import Image


def generate_radial_gradient(
    color: tuple[int, int, int],
    canvas_size: int = 1000,
    solid_radius: float = 0.35,
    transition_width: float = 0.25,
) -> Image.Image:
    """Generate a radial gradient RGBA image: solid center, transparent edges.

    Args:
        color: RGB color of the solid center (e.g. (240, 240, 240)).
        canvas_size: Output image size in pixels (square).
        solid_radius: Radius of the fully solid zone, as a fraction of
                      half the canvas size. 1.0 = reaches the edge.
                      Default 0.35 keeps the solid area in the inner 35%.
        transition_width: Width of the gradient band from solid to transparent,
                          also as a fraction of half the canvas size.
                          solid_radius + transition_width defines where full
                          transparency begins.

    Returns:
        RGBA Image of size canvas_size × canvas_size.
    """
    cx = cy = canvas_size / 2
    y, x = np.ogrid[:canvas_size, :canvas_size]
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

    half = canvas_size / 2
    r_solid = solid_radius * half
    r_outer = (solid_radius + transition_width) * half

    alpha = np.where(
        dist <= r_solid,
        255.0,
        np.where(
            dist >= r_outer,
            0.0,
            (1.0 - (dist - r_solid) / (r_outer - r_solid)) * 255.0,
        ),
    )

    rgba = np.empty((canvas_size, canvas_size, 4), dtype=np.uint8)
    rgba[:, :, 0] = color[0]
    rgba[:, :, 1] = color[1]
    rgba[:, :, 2] = color[2]
    rgba[:, :, 3] = alpha.clip(0, 255).astype(np.uint8)

    return Image.fromarray(rgba, "RGBA")
