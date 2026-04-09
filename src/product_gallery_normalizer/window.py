"""QMainWindow: toolbar, panels, status bar, and navigation controls."""

import logging
from pathlib import Path
from typing import Literal

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from product_gallery_normalizer.canvas import CanvasScene, CanvasView
from product_gallery_normalizer.config import AppConfig
from product_gallery_normalizer.gallery import Gallery

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with toolbar, canvas, navigation and status bar."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("product_gallery_normalizer")
        self.resize(1200, 900)

        self._config = AppConfig()
        self._gallery = Gallery()
        self._scene = CanvasScene()
        self._view = CanvasView(self._scene)

        self._build_toolbar()
        self._build_central()
        self._build_status_bar()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main", self)
        self.addToolBar(toolbar)
        open_bg = toolbar.addAction("Open background\u2026")
        open_bg.triggered.connect(self._on_open_background)
        open_folder = toolbar.addAction("Open folder\u2026")
        open_folder.triggered.connect(self._on_open_folder)
        toolbar.addSeparator()
        export_action = toolbar.addAction("Export batch\u2026")
        export_action.triggered.connect(self._on_export)

    def _build_central(self) -> None:
        prev_btn = QPushButton("\u2190 Previous")
        prev_btn.clicked.connect(self._on_prev)
        self._nav_label = QLabel("No images loaded")
        next_btn = QPushButton("Next \u2192")
        next_btn.clicked.connect(self._on_next)

        nav = QHBoxLayout()
        nav.addWidget(prev_btn)
        nav.addStretch()
        nav.addWidget(self._nav_label)
        nav.addStretch()
        nav.addWidget(next_btn)

        root = QVBoxLayout()
        root.addWidget(self._view)
        root.addLayout(nav)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

    def _build_status_bar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    def _on_open_background(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open background", "", "PNG Images (*.png)"
        )
        if not path_str:
            return
        path = Path(path_str)
        self._config.background_path = path
        self._scene.set_background(path)
        self._status.showMessage(f"Background: {path.name}")
        logger.info("Background set to %s", path)

    def _on_open_folder(self) -> None:
        dir_str = QFileDialog.getExistingDirectory(self, "Open product folder")
        if not dir_str:
            return
        directory = Path(dir_str)
        self._gallery.load_folder(directory)
        self._config.gallery_path = directory
        self._refresh_canvas()
        self._status.showMessage(
            f"Loaded {self._gallery.count} images from {directory.name}"
        )

    def _on_export(self) -> None:
        from product_gallery_normalizer import exporter

        if self._config.background_path is None:
            self._status.showMessage("Select a background image first")
            return
        if self._gallery.count == 0:
            self._status.showMessage("Open a product folder first")
            return
        dir_str = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not dir_str:
            return
        output_dir = Path(dir_str)
        fmt: Literal["PNG", "WEBP"] = self._config.export_format  # type: ignore[assignment]
        try:
            written = exporter.batch_export(
                self._gallery, self._config.background_path, output_dir, fmt
            )
            self._status.showMessage(f"Exported {len(written)} images to {output_dir}")
        except exporter.ExportError as exc:
            self._status.showMessage(f"Export finished with errors: {exc}")
            logger.error("Export errors: %s", exc)

    def _on_prev(self) -> None:
        self._save_transform()
        self._gallery.previous()
        self._refresh_canvas()

    def _on_next(self) -> None:
        self._save_transform()
        self._gallery.next()
        self._refresh_canvas()

    def _save_transform(self) -> None:
        if self._gallery.current is not None:
            self._gallery.update_current_transform(self._scene.get_current_transform())

    def _refresh_canvas(self) -> None:
        item = self._gallery.current
        if item is None:
            return
        if self._config.background_path is not None:
            self._scene.set_background(self._config.background_path)
        self._scene.set_product(item.path, item.transform)
        self._nav_label.setText(
            f"{self._gallery.index + 1} / {self._gallery.count}  \u2014  {item.path.name}"
        )
