"""QGraphicsScene + QGraphicsView: background and product layers with interactive transforms."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

from product_gallery_normalizer.config import ImageTransform
from product_gallery_normalizer.gallery import Gallery

logger = logging.getLogger(__name__)

_CANVAS_SIZE = 1000


class CanvasScene(QGraphicsScene):
    """Fixed 1000×1000 scene with a background layer and an interactive product layer."""

    def __init__(self, gallery: Gallery, parent: object = None) -> None:
        super().__init__(parent)
        self.setSceneRect(0, 0, _CANVAS_SIZE, _CANVAS_SIZE)
        self._gallery = gallery

        self._bg_item = QGraphicsPixmapItem()
        self._bg_item.setZValue(0)
        self.addItem(self._bg_item)

        self._product_item = QGraphicsPixmapItem()
        self._product_item.setZValue(1)
        self._product_item.setFlags(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.addItem(self._product_item)

    def load_background(self, path: Path) -> None:
        """Load and display a background image scaled to 1000×1000."""
        pixmap = QPixmap(str(path)).scaled(
            _CANVAS_SIZE,
            _CANVAS_SIZE,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._bg_item.setPixmap(pixmap)
        logger.info("Background loaded: %s", path)

    def load_product(self, path: Path, transform: ImageTransform) -> None:
        """Load a product image and apply its stored *transform*."""
        pixmap = QPixmap(str(path))
        self._product_item.setPixmap(pixmap)
        self.apply_transform(transform)
        logger.info("Product loaded: %s", path)

    def apply_transform(self, transform: ImageTransform) -> None:
        """Position, rotate and scale the product item from *transform*."""
        self._product_item.setPos(transform.x, transform.y)
        self._product_item.setRotation(transform.rotation)
        self._product_item.setScale(transform.scale)

    def current_transform(self) -> ImageTransform:
        """Read the product item's current geometry and return it as an ``ImageTransform``."""
        pos = self._product_item.pos()
        return ImageTransform(
            x=pos.x(),
            y=pos.y(),
            rotation=self._product_item.rotation(),
            scale=self._product_item.scale(),
        )


class CanvasView(QGraphicsView):
    """QGraphicsView that hosts a :class:`CanvasScene` and keeps it fit-in-view."""

    def __init__(self, scene: CanvasScene, parent: object = None) -> None:
        super().__init__(scene, parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(self.renderHints().RenderHint.Antialiasing)

    def resizeEvent(self, event: object) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
