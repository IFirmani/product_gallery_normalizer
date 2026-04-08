# Copilot Instructions — product_gallery_normalizer

## Stack

- **Python 3.13+**
- **PySide6** — GUI framework (QApplication, QMainWindow, QGraphicsScene/View)
- **Pillow** — image compositing and export
- **Pydantic v2** — config and transform state validation
- **pytest** — test runner
- **uv** — package manager (pyproject.toml, no setup.py)

## Code style

- Type hints on **all** function signatures (parameters and return types)
- Naming: `snake_case` for functions/variables/modules, `PascalCase` for classes
- No `print()` statements — use `logging` throughout
- Docstrings only on public API (public classes and their public methods/properties)
- Keep functions focused; prefer composition over inheritance

## Architecture rules

- `canvas.py` and `window.py` are the **only** modules that may import PySide6
- `compositor.py`, `exporter.py`, `gallery.py`, `config.py`, and `utils.py` must
  **never** import from PySide6 — they are pure Python / Pillow / Pydantic
- GUI modules may import from core modules; core modules must not import from GUI modules

## Canvas architecture

- The `QGraphicsScene` is fixed at 1000×1000 px
- **Layer 0** — background: a `QGraphicsPixmapItem`, not interactive
  (no `ItemIsMovable`, no `ItemIsSelectable`)
- **Layer 1** — product: a `QGraphicsPixmapItem` with flags
  `ItemIsMovable | ItemIsSelectable | ItemSendsGeometryChanges`
- Transform handles: corner dots for scale, top-center grip for rotation
- On any geometry change of the product item, write back to the active
  `ImageTransform` in the `Gallery` immediately

## State management

- `ImageTransform` (defined in `config.py`) is the **single source of truth** for
  each image's position, rotation, and scale
- The canvas reads `ImageTransform` to position the product item on navigation
- The canvas writes `ImageTransform` on every interactive change
- The exporter reads `ImageTransform` and never touches the GUI

## Testing

- Tests use real small PNG fixtures (10×10 px) generated with Pillow — **never
  mock image data**
- Fixtures are defined in `tests/conftest.py`
- Tests for compositing logic go in `test_compositor.py`
- Tests for export logic go in `test_exporter.py`
- Aim for deterministic, side-effect-free tests (use `tmp_path`)
