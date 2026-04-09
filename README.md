# product_gallery_normalizer

Desktop tool to normalize product images for e-commerce catalogs.

Composites product PNGs over a chosen background on a fixed 1000x1000 canvas,
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

### Background
- **Open PNG** — load any PNG as the fixed 1000x1000 background layer.
- **Generate** — create a radial-gradient background in real time: pick a
  colour, adjust the solid-core radius and the fade width. Applied instantly
  (no save dialog).

### Product
- **Open folder** — load all PNGs in a folder into the gallery.
- **Remove BG** — open a live before/after dialog. Click the *Original* preview
  to eyedrop the background colour; fine-tune with Tolerance and Softness
  sliders. Result replaces the gallery item automatically (no save dialog).

### Canvas
- Drag the product to reposition it.
- Rotation and scale are controlled from the **Properties** panel on the right.
- The image **anchor is always its centre** — rotation and scale pivot around
  the visual centre regardless of image size.
- A **snap guide** (crosshair + dot) sits at the canvas centre (500, 500).
  While dragging, the product snaps to centre when within 20 px.

### Properties panel (right)
| Control | Range |
|---------|-------|
| X (centre) | -5000 … 5000 px |
| Y (centre) | -5000 … 5000 px |
| Rotation | -360 … 360 ° — spinbox + slider |
| Scale | 0.01 … 20 × — spinbox + slider |
| Reset | returns to x=500, y=500, rot=0, scale=1 |

The panel syncs bidirectionally with the canvas drag.

### Gallery bar (bottom)
- Scrollable 80x80 thumbnail strip.
- Click a thumbnail or use **◄ ►** buttons (or ← / → keys) to navigate.
- Per-image transforms are preserved when switching images.

### Export
- **Export batch** — choose an output folder; every gallery item is composited
  over the background using its saved transform and written as PNG or WebP.

## Development

```bash
uv run pytest
```

## Project layout

```
src/product_gallery_normalizer/
├── __main__.py      # Entry point
├── app.py           # QApplication bootstrap
├── window.py        # QMainWindow: left panel | canvas | right panel, gallery bar
├── canvas.py        # QGraphicsScene/View — background, snap guide, product
├── dialogs.py       # GenerateBackgroundDialog, RemoveBackgroundDialog
├── gallery.py       # Gallery state management (GalleryItem + Gallery)
├── compositor.py    # Pillow compositing engine (stub)
├── exporter.py      # Batch export (stub)
├── bg_remover.py    # Numpy BG removal by colour
├── bg_generator.py  # Numpy radial-gradient generator
├── config.py        # Pydantic models: ImageTransform, AppConfig
└── utils.py         # Path and image helpers (stub)
```
