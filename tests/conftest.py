"""Shared test fixtures for product_gallery_normalizer."""

from pathlib import Path

import pytest
from PIL import Image

from product_gallery_normalizer.config import ImageTransform


@pytest.fixture()
def background_png(tmp_path: Path) -> Path:
    """A 10×10 solid blue PNG to use as a background."""
    path = tmp_path / "background.png"
    img = Image.new("RGBA", (10, 10), color=(0, 0, 255, 255))
    img.save(path)
    return path


@pytest.fixture()
def product_png(tmp_path: Path) -> Path:
    """A 10×10 solid red PNG with full opacity to use as a product image."""
    path = tmp_path / "product.png"
    img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 255))
    img.save(path)
    return path


@pytest.fixture()
def default_transform() -> ImageTransform:
    """An ``ImageTransform`` at the origin with no rotation and scale 1."""
    return ImageTransform(x=0.0, y=0.0, rotation=0.0, scale=1.0)


@pytest.fixture()
def product_folder(tmp_path: Path) -> Path:
    """A folder with three 10×10 product PNGs."""
    folder = tmp_path / "products"
    folder.mkdir()
    colors = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]
    for i, color in enumerate(colors):
        img = Image.new("RGBA", (10, 10), color=color)
        img.save(folder / f"product_{i:02d}.png")
    return folder
