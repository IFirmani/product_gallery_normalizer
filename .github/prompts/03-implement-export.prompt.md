---
mode: agent
description: Implement the batch export loop (exporter.py)
---

# Implement exporter.py

## Context

The stub `src/product_gallery_normalizer/exporter.py` exists.
`compositor.composite_image` is fully implemented and tested.
`Gallery` exposes an iterable of `(path: Path, transform: ImageTransform)` pairs
via `gallery.items()`.

## Goal

Implement `batch_export` so users can write all composited images to disk.

## Function signature

```python
def batch_export(
    gallery: Gallery,
    background: Path,
    output_dir: Path,
    fmt: Literal["PNG", "WEBP"],
) -> list[Path]:
```

## Requirements

1. Create `output_dir` if it does not exist (`output_dir.mkdir(parents=True, exist_ok=True)`).
2. Iterate `gallery.items()` — each item yields `(product_path, transform)`.
3. For each item:
   a. Call `compositor.composite_image(background, product_path, transform)`.
   b. Determine the output filename: same stem as `product_path`, extension
      `.png` (for `"PNG"`) or `.webp` (for `"WEBP"`).
   c. Save the composited image to `output_dir / filename` with the chosen format.
   d. Log `logging.info("Exported %s", output_path)`.
   e. Append `output_path` to the result list.
4. If compositing or saving fails for a single image, catch the exception,
   log `logging.error(...)`, raise `ExportError` wrapping the original exception,
   **but continue** processing the remaining images.
5. Return the list of successfully written paths.

## ExportError

Define `ExportError(RuntimeError)` in `exporter.py` with a `failed: list[Path]`
attribute listing all product paths that failed.

## Constraints

- No PySide6 imports
- All logging via `logging.getLogger(__name__)`
- `output_dir` creation is the only side-effect before the loop starts;
  everything else happens inside the per-item try/except
