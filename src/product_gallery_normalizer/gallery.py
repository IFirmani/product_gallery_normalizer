"""Gallery: loads product PNGs from a folder and stores per-image transform state."""

import logging
from pathlib import Path

from product_gallery_normalizer.config import ImageTransform
from product_gallery_normalizer.utils import collect_images

logger = logging.getLogger(__name__)


class Gallery:
    """Holds an ordered list of product image paths and their associated transforms."""

    def __init__(self) -> None:
        self._paths: list[Path] = []
        self._transforms: dict[Path, ImageTransform] = {}
        self._index: int = 0

    def load(self, directory: Path) -> None:
        """Load all supported image files from *directory*.

        Existing transforms for paths that appear again are preserved.
        """
        paths = collect_images(directory)
        self._paths = paths
        for path in paths:
            if path not in self._transforms:
                self._transforms[path] = ImageTransform()
        self._index = 0
        logger.info("Gallery loaded %d images from %s", len(paths), directory)

    @property
    def current_path(self) -> Path | None:
        """Return the path of the currently selected image, or ``None`` if empty."""
        if not self._paths:
            return None
        return self._paths[self._index]

    @property
    def current_transform(self) -> ImageTransform | None:
        """Return the ``ImageTransform`` for the currently selected image."""
        path = self.current_path
        if path is None:
            return None
        return self._transforms[path]

    @current_transform.setter
    def current_transform(self, transform: ImageTransform) -> None:
        """Write back *transform* for the currently selected image."""
        path = self.current_path
        if path is None:
            raise RuntimeError("Gallery is empty — cannot set transform")
        self._transforms[path] = transform

    @property
    def index(self) -> int:
        """Zero-based index of the currently selected image."""
        return self._index

    @property
    def count(self) -> int:
        """Total number of images in the gallery."""
        return len(self._paths)

    def go_next(self) -> bool:
        """Advance to the next image. Return True if the index changed."""
        if self._index < len(self._paths) - 1:
            self._index += 1
            return True
        return False

    def go_prev(self) -> bool:
        """Move to the previous image. Return True if the index changed."""
        if self._index > 0:
            self._index -= 1
            return True
        return False

    def go_to(self, index: int) -> None:
        """Jump to a specific zero-based *index*."""
        if not 0 <= index < len(self._paths):
            raise IndexError(f"Gallery index {index} out of range (0–{len(self._paths) - 1})")
        self._index = index

    def items(self) -> list[tuple[Path, ImageTransform]]:
        """Return all (path, transform) pairs — used by the exporter."""
        return [(p, self._transforms[p]) for p in self._paths]

    def __len__(self) -> int:
        return len(self._paths)
