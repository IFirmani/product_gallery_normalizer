---
mode: agent
description: Implement the interactive editing canvas (canvas.py)
---

# Implement canvas.py

QGraphicsScene fixed at 1000×1000 px inside a QGraphicsView.

## Layer 0 — background
- QGraphicsPixmapItem, zValue=0
- Not movable, not selectable
- Fills the scene exactly

## Layer 1 — product
- QGraphicsPixmapItem, zValue=1
- Flags: ItemIsMovable, ItemIsSelectable, ItemSendsGeometryChanges
- On itemChange(ItemPositionHasChanged / ItemTransformHasChanged):
  write x, y, rotation, scale back to the current ImageTransform via a signal

## Transform handles (drawn as QGraphicsEllipseItem children of the product item)
- Four corner dots for scale (drag changes scale uniformly)
- One dot at top-center for rotation (drag changes rotation)

## Public API
```python
def set_background(self, path: Path) -> None: ...
def set_product(self, path: Path, transform: ImageTransform) -> None: ...
def get_current_transform(self) -> ImageTransform: ...
def clear_product(self) -> None: ...
```
