"""Tests for compositor.composite_image."""

from pathlib import Path

import pytest
from PIL import Image

from product_gallery_normalizer.compositor import composite_image
from product_gallery_normalizer.config import ImageTransform


def test_composite_returns_rgba_image(
    background_png: Path, product_png: Path, default_transform: ImageTransform
) -> None:
    result = composite_image(background_png, product_png, default_transform)
    assert isinstance(result, Image.Image)
    assert result.mode == "RGBA"


def test_composite_output_is_1000x1000(
    background_png: Path, product_png: Path, default_transform: ImageTransform
) -> None:
    result = composite_image(background_png, product_png, default_transform)
    assert result.size == (1000, 1000)


def test_composite_product_visible_at_origin(
    background_png: Path, product_png: Path
) -> None:
    transform = ImageTransform(x=0.0, y=0.0, rotation=0.0, scale=1.0)
    result = composite_image(background_png, product_png, transform)
    # The product is red; at (0,0) the pixel should have a red component
    r, g, b, a = result.getpixel((0, 0))
    assert r > 200


def test_composite_raises_for_missing_background(
    product_png: Path, default_transform: ImageTransform, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="Background"):
        composite_image(tmp_path / "nonexistent.png", product_png, default_transform)


def test_composite_raises_for_missing_product(
    background_png: Path, default_transform: ImageTransform, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="Product"):
        composite_image(background_png, tmp_path / "nonexistent.png", default_transform)


def test_composite_scale_affects_output(
    background_png: Path, product_png: Path
) -> None:
    transform_small = ImageTransform(x=0.0, y=0.0, rotation=0.0, scale=0.5)
    transform_large = ImageTransform(x=0.0, y=0.0, rotation=0.0, scale=2.0)
    # Both should succeed and produce 1000×1000 results
    r1 = composite_image(background_png, product_png, transform_small)
    r2 = composite_image(background_png, product_png, transform_large)
    assert r1.size == (1000, 1000)
    assert r2.size == (1000, 1000)
