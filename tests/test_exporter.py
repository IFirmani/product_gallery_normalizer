"""Tests for exporter.batch_export."""

from pathlib import Path

import pytest

from product_gallery_normalizer.exporter import ExportError, batch_export
from product_gallery_normalizer.gallery import Gallery


def _make_gallery(product_folder: Path) -> Gallery:
    g = Gallery()
    g.load(product_folder)
    return g


def test_batch_export_creates_files(
    background_png: Path, product_folder: Path, tmp_path: Path
) -> None:
    gallery = _make_gallery(product_folder)
    output_dir = tmp_path / "out"
    written = batch_export(gallery, background_png, output_dir, "PNG")

    assert len(written) == gallery.count
    for path in written:
        assert path.exists()
        assert path.suffix == ".png"


def test_batch_export_webp_extension(
    background_png: Path, product_folder: Path, tmp_path: Path
) -> None:
    gallery = _make_gallery(product_folder)
    output_dir = tmp_path / "out"
    written = batch_export(gallery, background_png, output_dir, "WEBP")

    for path in written:
        assert path.suffix == ".webp"


def test_batch_export_creates_output_dir(
    background_png: Path, product_folder: Path, tmp_path: Path
) -> None:
    gallery = _make_gallery(product_folder)
    output_dir = tmp_path / "deep" / "nested" / "out"
    assert not output_dir.exists()
    batch_export(gallery, background_png, output_dir, "PNG")
    assert output_dir.is_dir()


def test_batch_export_preserves_stems(
    background_png: Path, product_folder: Path, tmp_path: Path
) -> None:
    gallery = _make_gallery(product_folder)
    output_dir = tmp_path / "out"
    written = batch_export(gallery, background_png, output_dir, "PNG")

    product_stems = {p.stem for p, _ in gallery.items()}
    output_stems = {p.stem for p in written}
    assert product_stems == output_stems


def test_batch_export_raises_export_error_on_bad_background(
    product_folder: Path, tmp_path: Path
) -> None:
    gallery = _make_gallery(product_folder)
    bad_bg = tmp_path / "nonexistent.png"
    output_dir = tmp_path / "out"
    with pytest.raises(ExportError) as exc_info:
        batch_export(gallery, bad_bg, output_dir, "PNG")
    assert len(exc_info.value.failed) == gallery.count
