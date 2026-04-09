"""Batch export loop: reads gallery items and writes composited output files."""

import logging
from pathlib import Path
from typing import Literal

from product_gallery_normalizer.gallery import Gallery

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Raised when one or more images failed to export."""
    ...


def batch_export(
    gallery: Gallery,
    background: Path,
    output_dir: Path,
    format: Literal["PNG", "WEBP"],
) -> list[Path]:
    """Export every image in gallery composited over background."""
    ...
