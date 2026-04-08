---
mode: agent
description: Implement the interactive editing canvas (canvas.py)
---

# Implement canvas.py

## Context

The stub `src/product_gallery_normalizer/canvas.py` exists with typed signatures
and docstrings. The `Gallery` class (`gallery.py`) and `ImageTransform` model
(`config.py`) are already defined.

## Goal

Fully implement `canvas.py` so the editing canvas works end-to-end.

## Requirements

### Scene / view setup

- `CanvasScene(QGraphicsScene)` — fixed scene rect `(0, 0, 1000, 1000)`
- `CanvasView(QGraphicsView)` — hosts the scene; fit-in-view on resize;
  disable scroll bars (the canvas is fixed size in the viewport)

### Layers

- **Layer 0 — background**: a `QGraphicsPixmapItem` at `zValue(0)`,
  **not** movable, **not** selectable, always fills 1000×1000
- **Layer 1 — product**: a `QGraphicsPixmapItem` at `zValue(1)` with flags
  `ItemIsMovable | ItemIsSelectable | ItemSendsGeometryChanges`

### Mouse interactions on the product item

- **Left-drag**: move item (Qt built-in with `ItemIsMovable`)
- **Scroll wheel**: scale the item (zoom in/out relative to item center)
- **Right-drag**: rotate the item around its center

### Transform handles

Add four corner `QGraphicsEllipseItem` dots (8×8 px, semi-transparent blue)
anchored to the corners of the product bounding rect. Dragging a corner scales
the product uniformly. Add a top-center `QGraphicsLineItem` grip for rotation.

### State sync

Override `itemChange` on the product item or use `QGraphicsScene.changed` to
detect geometry changes. On any change, compute the new `x`, `y`, `rotation`,
and `scale` values and write them to `gallery.current_transform`.

### Public API to implement

```python
def load_background(self, path: Path) -> None: ...
def load_product(self, path: Path, transform: ImageTransform) -> None: ...
def apply_transform(self, transform: ImageTransform) -> None: ...
def current_transform(self) -> ImageTransform: ...
```

## Constraints

- Do not import Pillow or any core-only module that imports Pillow inside this file
- All logging via `logging.getLogger(__name__)`
- No `print()` statements
