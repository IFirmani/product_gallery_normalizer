"""Tests for exporter.batch_export."""

from pathlib import Path

import pytest
from PIL import Image

from product_gallery_normalizer.exporter import ExportError, batch_export
from product_gallery_normalizer.gallery import Gallery


def _make_gallery(tmp_path: Path, count: int = 3) -> Gallery:
    """Create a Gallery loaded from a folder of real PNG files."""
    folder = tmp_path / "products"
    folder.mkdir(exist_ok=True)
    colors = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]
    for i in range(count):
        img = Image.new("RGBA", (10, 10), color=colors[i % len(colors)])
        img.save(folder / f"product_{i:02d}.png")
    gallery = Gallery()
    gallery.load_folder(folder)
    return gallery


def test_batch_export_creates_png_files(
    tmp_background: Path, tmp_path: Path
) -> None:
    gallery = _make_gallery(tmp_path)
    output_dir = tmp_path / "out"
    written = batch_export(gallery, tmp_background, output_dir, "PNG")
    assert len(written) == gallery.count
    for path in written:
        assert path.exists()
        assert path.suffix == ".png"


def test_batch_export_creates_webp_files(
    tmp_background: Path, tmp_path: Path
) -> None:
    gallery = _make_gallery(tmp_path)
    output_dir = tmp_path / "out"
    written = batch_export(gallery, tmp_background, output_dir, "WEBP")
    for path in written:
        assert path.suffix == ".webp"


def test_batch_export_creates_output_dir(
    tmp_background: Path, tmp_path: Path
) -> None:
    gallery = _make_gallery(tmp_path)
    output_dir = tmp_path / "deep" / "nested" / "out"
    assert not output_dir.exists()
    batch_export(gallery, tmp_background, output_dir, "PNG")
    assert output_dir.is_dir()


def test_batch_export_preserves_stems(
    tmp_background: Path, tmp_path: Path
) -> None:
    gallery = _make_gallery(tmp_path)
    output_dir = tmp_path / "out"
    written = batch_export(gallery, tmp_background, output_dir, "PNG")
    product_stems = {item.path.stem for item in gallery}
    output_stems = {p.stem for p in written}
    assert product_stems == output_stems


def test_batch_export_raises_on_bad_background(
    tmp_path: Path
) -> None:
    gallery = _make_gallery(tmp_path)
    bad_bg = tmp_path / "nonexistent.png"
    with pytest.raises(ExportError):
        batch_export(gallery, bad_bg, tmp_path / "out", "PNG")
