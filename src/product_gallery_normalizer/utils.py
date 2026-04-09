"""Path helpers and image validation utilities."""

from pathlib import Path


def collect_images(directory: Path) -> list[Path]:
    """Return a sorted list of PNG files in directory."""
    ...


def is_valid_image(path: Path) -> bool:
    """Return True if path is a supported image file that exists."""
    ...
