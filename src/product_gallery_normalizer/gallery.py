"""Gallery: loads product PNGs from a folder and stores per-image transform state."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from product_gallery_normalizer.config import ImageTransform

logger = logging.getLogger(__name__)


@dataclass
class GalleryItem:
    """A single product image and its associated transform."""

    path: Path
    transform: ImageTransform = field(default_factory=ImageTransform)


class Gallery:
    """Manages the ordered collection of product images and their transforms."""

    def __init__(self) -> None:
        self._items: list[GalleryItem] = []
        self._index: int = 0

    def load_folder(self, folder: Path) -> None:
        """Load all PNG files from folder, sorted by name. Resets all transforms."""
        paths = sorted(folder.glob("*.png"))
        if not paths:
            logger.warning("No PNG files found in %s", folder)
        self._items = [GalleryItem(path=p) for p in paths]
        self._index = 0
        logger.info("Loaded %d images from %s", len(self._items), folder)

    @property
    def current(self) -> GalleryItem | None:
        """Return the currently selected item, or None if the gallery is empty."""
        if not self._items:
            return None
        return self._items[self._index]

    @property
    def index(self) -> int:
        """Zero-based index of the currently selected image."""
        return self._index

    @property
    def count(self) -> int:
        """Total number of images in the gallery."""
        return len(self._items)

    def next(self) -> GalleryItem | None:
        """Advance to the next image and return it (or current if already at end)."""
        if not self._items or self._index >= len(self._items) - 1:
            return self.current
        self._index += 1
        return self.current

    def previous(self) -> GalleryItem | None:
        """Move to the previous image and return it (or current if already at start)."""
        if not self._items or self._index <= 0:
            return self.current
        self._index -= 1
        return self.current

    def go_to(self, index: int) -> GalleryItem | None:
        """Jump to a specific zero-based index. Returns None if index is out of range."""
        if not self._items or not (0 <= index < len(self._items)):
            return None
        self._index = index
        return self.current

    def update_current_transform(self, transform: ImageTransform) -> None:
        """Write transform back to the active item."""
        if self.current is not None:
            self.current.transform = transform

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)
