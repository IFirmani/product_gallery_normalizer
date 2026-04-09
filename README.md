# product_gallery_normalizer

Desktop tool to normalize product images for e-commerce catalogs.

Composites product PNGs over a chosen background on a fixed 1000×1000 canvas,
with per-image position / rotation / scale adjustments. Exports the full gallery
in batch as PNG or WebP.

## Requirements

- Python 3.13+
- uv 0.11.5+

## Setup

```bash
uv venv --python 3.13
uv sync
```

## Run

```bash
uv run python -m product_gallery_normalizer
```

## Usage

1. **Open background** — select a PNG to use as the fixed background layer
2. **Open folder** — select a folder containing the product PNGs
3. **Navigate** the gallery with ← → or the sidebar thumbnail strip
4. **Adjust** — drag to move, drag corners to scale, drag top grip to rotate
5. **Export batch** — choose output folder and format (PNG or WebP)

## Development

```bash
uv run pytest
```

## Project layout

```
src/product_gallery_normalizer/
├── __main__.py      # Entry point
├── app.py           # QApplication bootstrap
├── window.py        # QMainWindow
├── canvas.py        # QGraphicsScene/View editing canvas
├── gallery.py       # Gallery state management
├── compositor.py    # Pillow compositing engine
├── exporter.py      # Batch export
├── config.py        # Pydantic models
└── utils.py         # Path and image helpers
```
