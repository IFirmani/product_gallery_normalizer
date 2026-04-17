"""QGraphicsScene + QGraphicsView for the editing canvas."""

import io
import logging
from pathlib import Path

from PIL import Image as PilImage
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

from product_gallery_normalizer.config import ImageTransform
from product_gallery_normalizer.utils import apply_edge_feather

logger = logging.getLogger(__name__)

_SIZE = 1000
_HALF = _SIZE / 2.0
_SNAP_RADIUS = 20.0   # scene pixels within which the centre snaps to canvas centre
_CROSS_ARM = 18       # half-length of crosshair arms (scene pixels)


class _ProductItem(QGraphicsPixmapItem):
    """Movable product item with centre-based transform origin and centre-snap."""

    def __init__(self, on_changed, parent=None) -> None:
        super().__init__(parent)
        self._on_changed = on_changed
        self._mute: bool = False

    def itemChange(self, change, value):
        # Snap centre to canvas centre BEFORE the move is applied
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and not self._mute
            and not self.pixmap().isNull()
        ):
            pw = self.pixmap().width()
            ph = self.pixmap().height()
            # pos() + transformOriginPoint() == scene position of image centre
            cx = value.x() + pw / 2.0
            cy = value.y() + ph / 2.0
            if abs(cx - _HALF) < _SNAP_RADIUS and abs(cy - _HALF) < _SNAP_RADIUS:
                return QPointF(_HALF - pw / 2.0, _HALF - ph / 2.0)

        result = super().itemChange(change, value)
        if (
            not self._mute
            and change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
        ):
            self._on_changed()
        return result


def _pil_to_pixmap(img: PilImage.Image) -> QPixmap:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return QPixmap.fromImage(QImage.fromData(buf.getvalue()))


class CanvasScene(QGraphicsScene):
    """Fixed 1000x1000 scene with a background layer and an interactive product layer."""

    product_transform_changed = Signal(float, float, float, float)

    def __init__(self, parent: object = None) -> None:
        super().__init__(parent)
        self.setSceneRect(0, 0, _SIZE, _SIZE)

        self._bg = QGraphicsPixmapItem()
        self._bg.setZValue(0)
        self.addItem(self._bg)

        self._product = _ProductItem(self._on_product_changed)
        self._product.setZValue(1)
        self._product.setFlags(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.addItem(self._product)

        # Centre snap target: subtle crosshair at (500, 500); zValue 0.5 = above bg, below product
        _cp = QPen(QColor(200, 200, 200, 150))
        _cp.setWidth(1)
        self.addLine(_HALF - _CROSS_ARM, _HALF, _HALF + _CROSS_ARM, _HALF, _cp).setZValue(0.5)
        self.addLine(_HALF, _HALF - _CROSS_ARM, _HALF, _HALF + _CROSS_ARM, _cp).setZValue(0.5)
        _dot = self.addEllipse(
            _HALF - 3, _HALF - 3, 6, 6,
            QPen(QColor(220, 220, 220, 180)),
            QBrush(QColor(220, 220, 220, 100)),
        )
        _dot.setZValue(0.5)

    # ------------------------------------------------------------------ slots

    def _on_product_changed(self) -> None:
        t = self.get_current_transform()
        self.product_transform_changed.emit(t.x, t.y, t.rotation, t.scale)

    # ------------------------------------------------------------------ public

    def set_background(self, path: Path) -> None:
        """Load and display a background image scaled to 1000x1000 from a file."""
        px = QPixmap(str(path)).scaled(
            _SIZE,
            _SIZE,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._bg.setPixmap(px)
        logger.info("Background loaded: %s", path.name)

    def set_background_pil(self, img: PilImage.Image) -> None:
        """Display a PIL Image directly as background without touching the filesystem."""
        px = _pil_to_pixmap(img.resize((_SIZE, _SIZE), PilImage.LANCZOS))
        self._bg.setPixmap(px)
        logger.info("Background set from PIL image (%dx%d)", *img.size)

    def set_product(self, path: Path, transform: ImageTransform) -> None:
        """Load a product image and apply its stored transform.

        ``transform.x`` and ``transform.y`` are the scene coordinates of the
        **centre** of the image.  The transform origin is set to the pixmap
        centre so that rotation and scale always happen around the centre.
        """
        self._product._mute = True
        try:
            if transform.edge_feather > 0:
                pil_img = PilImage.open(path)
                pil_img = apply_edge_feather(pil_img, transform.edge_feather)
                px = _pil_to_pixmap(pil_img)
            else:
                px = QPixmap(str(path))
            pw, ph = px.width(), px.height()
            self._product.setPixmap(px)
            # Anchor: rotate/scale around the centre of the image
            self._product.setTransformOriginPoint(pw / 2.0, ph / 2.0)
            self._product.setRotation(transform.rotation)
            self._product.setScale(transform.scale)
            # pos() = top-left origin in scene; centre = pos() + (pw/2, ph/2)
            self._product.setPos(transform.x - pw / 2.0, transform.y - ph / 2.0)
        finally:
            self._product._mute = False
        logger.info("Product loaded: %s", path.name)

    def apply_transform(self, transform: ImageTransform) -> None:
        """Apply a transform to the product item without emitting signals."""
        self._product._mute = True
        try:
            pw = self._product.pixmap().width()
            ph = self._product.pixmap().height()
            self._product.setRotation(transform.rotation)
            self._product.setScale(transform.scale)
            self._product.setPos(transform.x - pw / 2.0, transform.y - ph / 2.0)
        finally:
            self._product._mute = False

    def get_current_transform(self) -> ImageTransform:
        """Read the product item's current geometry.

        Returns x/y as the scene coordinates of the **centre** of the image.
        """
        pos = self._product.pos()
        pw = self._product.pixmap().width()
        ph = self._product.pixmap().height()
        return ImageTransform(
            x=pos.x() + pw / 2.0,
            y=pos.y() + ph / 2.0,
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
