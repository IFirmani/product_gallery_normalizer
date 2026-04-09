---
mode: agent
description: Implement the interactive editing canvas (canvas.py)
---

# Implement canvas.py

`CanvasScene(QGraphicsScene)` fixed at 1000x1000 px inside `CanvasView(QGraphicsView)`.

## Layer 0 — background
- `QGraphicsPixmapItem`, `zValue=0`
- Not movable, not selectable
- Fills the scene exactly (scaled on load)

## Layer 0.5 — centre guide
- Two `QGraphicsLineItem` lines forming a crosshair at (500, 500), `zValue=0.5`
- One `QGraphicsEllipseItem` dot at (500, 500), `zValue=0.5`
- Colour: semi-transparent white — visual snap target, always present

## Layer 1 — product (`_ProductItem`)
- Subclass of `QGraphicsPixmapItem`, `zValue=1`
- Flags: `ItemIsMovable | ItemIsSelectable | ItemSendsGeometryChanges`
- **Transform origin always at the image centre**: call
  `setTransformOriginPoint(w/2, h/2)` whenever a new pixmap is loaded
- **Snap logic** in `itemChange(ItemPositionChange)`: if image centre would land
  within 20 scene-px of (500, 500), snap position to exact centre
- `_mute: bool` flag — when True, suppress all signal emissions (prevents
  re-entrancy during programmatic moves)

## Signal
```python
product_transform_changed = Signal(float, float, float, float)
# emits: x_centre, y_centre, rotation, scale
```
Emitted on every user drag. x/y are the **scene coordinates of the image centre**.

## ImageTransform convention
`transform.x` and `transform.y` are the scene coordinates of the image centre,
**not** the top-left corner. Convert when setting/getting position:
```python
setPos(transform.x - pw/2, transform.y - ph/2)
get: pos().x() + pw/2, pos().y() + ph/2
```

## Public API
```python
def set_background(self, path: Path) -> None: ...
def set_background_pil(self, img: Image.Image) -> None: ...
def set_product(self, path: Path, transform: ImageTransform) -> None: ...
def apply_transform(self, transform: ImageTransform) -> None: ...   # muted
def get_current_transform(self) -> ImageTransform: ...
def clear_product(self) -> None: ...
```
