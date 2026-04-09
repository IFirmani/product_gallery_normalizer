---
mode: agent
description: Implement the batch export loop (exporter.py)
---

# Implement exporter.py

No PySide6 imports allowed.

```python
class ExportError(Exception): ...

def batch_export(
    gallery: Gallery,
    background: Path,
    output_dir: Path,
    format: Literal["PNG", "WEBP"],
) -> list[Path]:
```

## Steps per GalleryItem

1. Call `compositor.composite_image(background, item.path, item.transform)`
2. Determine output path: `output_dir / (item.path.stem + ext)`
   where ext is `.png` or `.webp`
3. Save with correct format. For WEBP use `quality=90, method=6`
4. Log progress: `logging.info("Exported %s", output_path)`
5. On any exception: log error, raise `ExportError` wrapping the original,
   continue with remaining images
6. Return list of successfully written paths
