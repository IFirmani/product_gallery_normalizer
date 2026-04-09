# Copilot workspace instructions

## Stack
- Python 3.13, PySide6, Pillow, Pydantic v2, pytest, uv

## Code style
- Type hints on every function signature
- Docstrings on public functions and classes only
- snake_case for variables/functions, PascalCase for classes
- No print() — use logging in core modules, Qt signals in GUI modules
- Small functions with single responsibility

## Architecture rule (strict)
GUI layer (app.py, window.py, canvas.py) may import from core.
Core layer (compositor.py, exporter.py, gallery.py, config.py, utils.py)
must NEVER import PySide6.

## Canvas architecture
- QGraphicsScene locked to 1000×1000 px
- Layer 0: background QGraphicsPixmapItem — no interaction flags
- Layer 1: product QGraphicsPixmapItem — ItemIsMovable, ItemIsSelectable,
  ItemSendsGeometryChanges
- Product item geometry changes write back to the active ImageTransform
- ImageTransform is the single source of truth for each image's state

## Tests
Use real PNG fixtures (10×10 px generated with Pillow). No mocks for image data.
