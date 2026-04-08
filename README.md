# product_gallery_normalizer

Desktop tool to normalize product images for e-commerce catalogs.
Composites product PNGs over a chosen background on a fixed 1000×1000 canvas,
with per-image position / rotation / scale adjustments. Exports the full gallery
in batch as PNG or WebP.

### Requirements

- Python 3.13+
- uv 0.11.5+

### Setup

```bash
uv venv --python 3.13
uv sync
```

### Run

```bash
uv run python -m product_gallery_normalizer
```

### Usage

1. **Open background** — select a PNG file to use as the fixed background layer
2. **Open folder** — select a folder containing the product PNGs
3. Navigate the gallery with ← → arrows or the sidebar
4. Drag to move, scroll to scale, right-drag to rotate the product image
5. **Export batch** — choose output folder and format (PNG or WebP)

### Project layout

```
src/product_gallery_normalizer/
├── __init__.py
├── __main__.py        # python -m product_gallery_normalizer entry point
├── app.py             # QApplication bootstrap
├── window.py          # QMainWindow: toolbar, panels, status bar
├── canvas.py          # QGraphicsScene/QGraphicsView: background + product layers
├── gallery.py         # Loads PNGs from folder, stores transform state per image
├── compositor.py      # Pillow: composites product over background at 1000×1000
├── exporter.py        # Batch export loop
├── config.py          # Pydantic models: AppConfig, ImageTransform
└── utils.py           # Path helpers, image validation, format detection

tests/
├── conftest.py
├── test_compositor.py
└── test_exporter.py
```

### Development

```bash
uv run pytest
```
