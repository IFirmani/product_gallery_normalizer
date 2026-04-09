# Copilot workspace instructions

## Stack
- Python 3.13, PySide6 6.11, Pillow 12, Pydantic v2, numpy, pytest, uv

## Code style
- Type hints on every function signature
- Docstrings on public functions and classes only
- snake_case for variables/functions, PascalCase for classes
- No print() — use logging in core modules, Qt signals in GUI modules
- Small functions with single responsibility

## Architecture rule (strict)
GUI layer (app.py, window.py, canvas.py) may import from core.
Core layer (compositor.py, exporter.py, gallery.py, config.py, utils.py,
bg_remover.py, bg_generator.py) must NEVER import PySide6.

## Canvas architecture
- QGraphicsScene locked to 1000×1000 px
- Layer 0 (zValue 0): background QGraphicsPixmapItem — no interaction flags
- Layer 0.5 (zValue 0.5): centre crosshair guide lines (snap target indicator)
- Layer 1 (zValue 1): product `_ProductItem(QGraphicsPixmapItem)` — ItemIsMovable,
  ItemIsSelectable, ItemSendsGeometryChanges
- Transform origin is always the **centre** of the product pixmap
  (`setTransformOriginPoint(w/2, h/2)`)
- `ImageTransform.x / .y` store the **scene-space centre** of the image, not the
  top-left corner
- Snap: while dragging, if the image centre is within 20 scene-px of (500, 500)
  it snaps exactly to canvas centre
- `CanvasScene.product_transform_changed = Signal(float, float, float, float)`
  emitted on every drag (x_centre, y_centre, rotation, scale)
- `_ProductItem._mute` flag prevents signal re-entrancy during programmatic moves

## Window layout
```
[Left panel 165px | QGraphicsView flex | Right panel 200px]
[Bottom gallery bar 80px + 24px padding]
```
- Left panel: Background (Open PNG / Generate…), Product (Open folder / Remove BG…), Export
- Right panel: Properties — X spinbox, Y spinbox, Rotation spinbox + slider,
  Scale spinbox + slider, Reset button
- Bottom bar: scrollable thumbnail strip (80×80) + ◄ ► nav buttons
- Keyboard: ← / → for prev/next thumbnail

## Dialogs
- `GenerateBackgroundDialog`: 280px live preview, colour picker, solid-radius slider,
  transition-width slider. Calls `bg_generator.generate_radial_gradient()`. Result is
  applied directly to the canvas (no save dialog).
- `RemoveBackgroundDialog`: side-by-side before/after 280px preview. Click the
  "before" image to eyedrop the background colour. Tolerance and softness sliders.
  Calls `bg_remover.remove_background_by_color()`. Result replaces the gallery item
  path in-place (no save dialog).

## No-save-dialog rule
Generated backgrounds and BG-removed images are written to a `tempfile.mkdtemp()`
directory automatically. No QFileDialog is shown for these artefacts.

## ImageTransform
```python
class ImageTransform(BaseModel):
    x: float = 500.0     # scene X of image centre
    y: float = 500.0     # scene Y of image centre
    rotation: float = 0.0
    scale: float = 1.0   # gt=0
```

## Tests
Use real PNG fixtures (10×10 px generated with Pillow). No mocks for image data.
