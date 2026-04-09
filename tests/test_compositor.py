"""Tests for compositor.composite_image."""

from pathlib import Path

import pytest
from PIL import Image

from product_gallery_normalizer.compositor import composite_image
from product_gallery_normalizer.config import ImageTransform


def test_composite_returns_rgba_image(
    tmp_background: Path, tmp_png: Path, default_transform: ImageTransform
) -> None:
    result = composite_image(tmp_background, tmp_png, default_transform)
    assert isinstance(result, Image.Image)
    assert result.mode == "RGBA"


def test_composite_output_is_canvas_size(
    tmp_background: Path, tmp_png: Path, default_transform: ImageTransform
) -> None:
    result = composite_image(tmp_background, tmp_png, default_transform, canvas_size=1000)
    assert result.size == (1000, 1000)


def test_composite_product_visible_at_origin(
    tmp_background: Path, tmp_png: Path
) -> None:
    transform = ImageTransform(x=0.0, y=0.0, rotation=0.0, scale=1.0)
    result = composite_image(tmp_background, tmp_png, transform)
    r, g, b, a = result.getpixel((0, 0))
    assert r > 200  # product is red


def test_composite_scale_produces_correct_size(
    tmp_background: Path, tmp_png: Path
) -> None:
    for scale in (0.5, 1.0, 2.0):
        transform = ImageTransform(x=0.0, y=0.0, rotation=0.0, scale=scale)
        result = composite_image(tmp_background, tmp_png, transform)
        assert result.size == (1000, 1000)


def test_composite_missing_background_raises(
    tmp_png: Path, default_transform: ImageTransform, tmp_path: Path
) -> None:
    with pytest.raises(Exception):
        composite_image(tmp_path / "no_bg.png", tmp_png, default_transform)


def test_composite_missing_product_raises(
    tmp_background: Path, default_transform: ImageTransform, tmp_path: Path
) -> None:
    with pytest.raises(Exception):
        composite_image(tmp_background, tmp_path / "no_prod.png", default_transform)
