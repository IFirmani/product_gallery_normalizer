"""QApplication bootstrap for product_gallery_normalizer."""

import logging
import sys

from PySide6.QtWidgets import QApplication

from product_gallery_normalizer.window import MainWindow

logger = logging.getLogger(__name__)


def run() -> None:
    """Create the QApplication and show the main window."""
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    app.setApplicationName("product_gallery_normalizer")

    window = MainWindow()
    window.show()

    logger.info("Application started")
    sys.exit(app.exec())
