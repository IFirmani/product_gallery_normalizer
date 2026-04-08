"""Path helpers, image validation, and format detection."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp"})


def is_valid_image(path: Path) -> bool:
    """Return True if *path* points to a supported image file that exists."""
    return path.is_file() and path.suffix.lower() in _SUPPORTED_EXTENSIONS


def collect_images(directory: Path) -> list[Path]:
    """Return a sorted list of supported image files in *directory* (non-recursive)."""
    if not directory.is_dir():
        logger.warning("collect_images: %s is not a directory", directory)
        return []
    return sorted(p for p in directory.iterdir() if is_valid_image(p))


def output_extension(fmt: str) -> str:
    """Map an export format string (``'PNG'`` or ``'WEBP'``) to a file extension."""
    mapping: dict[str, str] = {"PNG": ".png", "WEBP": ".webp"}
    ext = mapping.get(fmt.upper())
    if ext is None:
        raise ValueError(f"Unsupported export format: {fmt!r}")
    return ext
