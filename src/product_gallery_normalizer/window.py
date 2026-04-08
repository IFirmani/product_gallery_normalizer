"""QMainWindow: toolbar, panels, status bar, and navigation controls."""

import logging
from pathlib import Path

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

        self._build_toolbar()
        self._build_central()
        self._build_status_bar()

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main", self)
        self.addToolBar(toolbar)

        open_bg_action = toolbar.addAction("Open background…")
        open_bg_action.triggered.connect(self._on_open_background)

        open_folder_action = toolbar.addAction("Open folder…")
        open_folder_action.triggered.connect(self._on_open_folder)

        toolbar.addSeparator()

        export_action = toolbar.addAction("Export batch…")
        export_action.triggered.connect(self._on_export)

    def _build_central(self) -> None:
        self._scene = CanvasScene(self._gallery)
        self._view = CanvasView(self._scene)

        prev_btn = QPushButton("← Previous")
        prev_btn.clicked.connect(self._on_prev)

        self._nav_label = QLabel("No images loaded")
        self._nav_label.setAlignment(self._nav_label.alignment())

        next_btn = QPushButton("Next →")
        next_btn.clicked.connect(self._on_next)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self._nav_label)
        nav_layout.addStretch()
        nav_layout.addWidget(next_btn)

        root_layout = QVBoxLayout()
        root_layout.addWidget(self._view)
        root_layout.addLayout(nav_layout)

        container = QWidget()
        container.setLayout(root_layout)
        self.setCentralWidget(container)

    def _build_status_bar(self) -> None:
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_open_background(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open background image", "", "PNG Images (*.png)"
        )
        if not path_str:
            return
        path = Path(path_str)
        self._config.background_path = path
        self._scene.load_background(path)
        self._status_bar.showMessage(f"Background: {path.name}")
        logger.info("Background set to %s", path)

    def _on_open_folder(self) -> None:
        dir_str = QFileDialog.getExistingDirectory(self, "Open product folder")
        if not dir_str:
            return
        directory = Path(dir_str)
        self._gallery.load(directory)
        self._config.gallery_dir = directory
        self._refresh_canvas()
        self._status_bar.showMessage(f"Loaded {self._gallery.count} images from {directory.name}")

    def _on_export(self) -> None:
        from product_gallery_normalizer import exporter
        from typing import Literal

        if self._config.background_path is None:
            self._status_bar.showMessage("Select a background image first")
            return
        if self._gallery.count == 0:
            self._status_bar.showMessage("Open a product folder first")
            return

        dir_str = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not dir_str:
            return
        output_dir = Path(dir_str)
        fmt: Literal["PNG", "WEBP"] = "PNG"

        try:
            written = exporter.batch_export(
                self._gallery,
                self._config.background_path,
                output_dir,
                fmt,
            )
            self._status_bar.showMessage(f"Exported {len(written)} images to {output_dir}")
        except exporter.ExportError as exc:
            self._status_bar.showMessage(f"Export finished with errors: {exc}")
            logger.error("Export errors: %s", exc.failed)

    def _on_prev(self) -> None:
        self._save_current_transform()
        if self._gallery.go_prev():
            self._refresh_canvas()

    def _on_next(self) -> None:
        self._save_current_transform()
        if self._gallery.go_next():
            self._refresh_canvas()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _save_current_transform(self) -> None:
        if self._gallery.count > 0:
            self._gallery.current_transform = self._scene.current_transform()

    def _refresh_canvas(self) -> None:
        path = self._gallery.current_path
        transform = self._gallery.current_transform
        if path is None or transform is None:
            return
        if self._config.background_path is not None:
            self._scene.load_background(self._config.background_path)
        self._scene.load_product(path, transform)
        self._nav_label.setText(
            f"{self._gallery.index + 1} / {self._gallery.count}  —  {path.name}"
        )
