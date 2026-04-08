"""Batch export loop: reads gallery + transforms, writes composited output files."""

import logging
from pathlib import Path
from typing import Literal

from product_gallery_normalizer import compositor
from product_gallery_normalizer.gallery import Gallery
from product_gallery_normalizer.utils import output_extension

logger = logging.getLogger(__name__)


class ExportError(RuntimeError):
    """Raised when one or more images failed to export."""

    def __init__(self, message: str, failed: list[Path]) -> None:
        super().__init__(message)
        self.failed: list[Path] = failed


def batch_export(
    gallery: Gallery,
    background: Path,
    output_dir: Path,
    fmt: Literal["PNG", "WEBP"] = "PNG",
) -> list[Path]:
    """Export every image in *gallery* composited over *background*.

    Files are written to *output_dir* with the same stem as the product image
    and the extension determined by *fmt*. Returns a list of successfully written
    paths. Raises :class:`ExportError` (after processing all items) if any image
    failed; the ``failed`` attribute lists the product paths that errored.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = output_extension(fmt)

    written: list[Path] = []
    failed: list[Path] = []

    for product_path, transform in gallery.items():
        output_path = output_dir / (product_path.stem + ext)
        try:
            img = compositor.composite_image(background, product_path, transform)
            img.save(output_path, format=fmt)
            logger.info("Exported %s", output_path)
            written.append(output_path)
        except Exception as exc:
            logger.error("Failed to export %s: %s", product_path, exc)
            failed.append(product_path)

    if failed:
        raise ExportError(
            f"{len(failed)} image(s) failed to export",
            failed=failed,
        )

    return written
