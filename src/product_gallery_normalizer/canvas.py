"""QGraphicsScene + QGraphicsView for the editing canvas."""

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

logger = logging.getLogger(__name__)

_SIZE = 1000


class CanvasScene(QGraphicsScene):
    """Fixed 1000x1000 scene with a background layer and an interactive product layer."""

    def __init__(self, parent: object = None) -> None:
        super().__init__(parent)
        self.setSceneRect(0, 0, _SIZE, _SIZE)

        self._bg = QGraphicsPixmapItem()
        self._bg.setZValue(0)
        self.addItem(self._bg)

        self._product = QGraphicsPixmapItem()
        self._product.setZValue(1)
        self._product.setFlags(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.addItem(self._product)

    def set_background(self, path: Path) -> None:
        """Load and display a background image scaled to 1000x1000."""
        px = QPixmap(str(path)).scaled(
            _SIZE, _SIZE,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._bg.setPixmap(px)
        logger.info("Background loaded: %s", path.name)

    def set_product(self, path: Path, transform: ImageTransform) -> None:
        """Load a product image and apply its stored transform."""
        self._product.setPixmap(QPixmap(str(path)))
        self._product.setPos(transform.x, transform.y)
        self._product.setRotation(transform.rotation)
        self._product.setScale(transform.scale)
        logger.info("Product loaded: %s", path.name)

    def get_current_transform(self) -> ImageTransform:
        """Read the product item current geometry as an ImageTransform."""
        pos = self._product.pos()
        return ImageTransform(
            x=pos.x(),
            y=pos.y(),
            rotation=self._product.rotation(),
            scale=self._product.scale(),
        )

    def clear_product(self) -> None:
        """Remove the product image from the scene."""
        self._product.setPixmap(QPixmap())


class CanvasView(QGraphicsView):
    """QGraphicsView that hosts a CanvasScene."""

    def __init__(self, scene: CanvasScene, parent: object = None) -> None:
        super().__init__(scene, parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def resizeEvent(self, event: object) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
