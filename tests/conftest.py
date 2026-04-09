"""Shared test fixtures for product_gallery_normalizer."""

from pathlib import Path

import pytest
from PIL import Image

from product_gallery_normalizer.config import ImageTransform


@pytest.fixture
def tmp_png(tmp_path: Path) -> Path:
    """A real 10×10 RGBA PNG written to a temp file."""
    img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 255))
    path = tmp_path / "product.png"
    img.save(path)
    return path


@pytest.fixture
def tmp_background(tmp_path: Path) -> Path:
    """A real 100×100 RGBA PNG for use as background."""
    img = Image.new("RGBA", (100, 100), color=(200, 200, 200, 255))
    path = tmp_path / "background.png"
    img.save(path)
    return path


@pytest.fixture
def default_transform() -> ImageTransform:
    """An ImageTransform at the origin with no rotation and scale 1."""
    return ImageTransform(x=0.0, y=0.0, rotation=0.0, scale=1.0)


@pytest.fixture
def offset_transform() -> ImageTransform:
    """An ImageTransform offset and rotated."""
    return ImageTransform(x=50.0, y=50.0, rotation=45.0, scale=0.5)
