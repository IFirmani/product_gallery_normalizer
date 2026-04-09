"""Dialogs with real-time preview for background generation and BG removal."""

import io

import numpy as np
from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor, QImage, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from product_gallery_normalizer.bg_generator import generate_radial_gradient
from product_gallery_normalizer.bg_remover import remove_background_by_color

_PREVIEW = 280


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pil_to_pixmap(img: Image.Image) -> QPixmap:
    """Convert PIL Image to QPixmap via PNG round-trip."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return QPixmap.fromImage(QImage.fromData(buf.getvalue()))


def _checker(size: int, cell: int = 12) -> Image.Image:
    """Grey checkered background to visualise transparency."""
    arr = np.full((size, size), 155, dtype=np.uint8)
    for y in range(0, size, cell):
        for x in range(0, size, cell):
            if (x // cell + y // cell) % 2 == 0:
                arr[y : y + cell, x : x + cell] = 205
    rgb = np.stack([arr, arr, arr], axis=2)
    return Image.fromarray(rgb, "RGB")


def _on_checker(fg: Image.Image, size: int) -> Image.Image:
    """Paste *fg* (RGBA) resized to *size* x *size* over a checkered background."""
    bg = _checker(size)
    resized = fg.resize((size, size), Image.LANCZOS).convert("RGBA")
    bg.paste(resized, mask=resized.split()[3])
    return bg


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


class _ColorButton(QPushButton):
    """QPushButton that shows and edits a QColor."""

    colorChanged = Signal()

    def __init__(self, color: QColor, parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(32)
        self._refresh()
        self.clicked.connect(self._pick)

    def _pick(self) -> None:
        c = QColorDialog.getColor(self._color, self, "Choose colour")
        if c.isValid():
            self.set_color(c)

    def set_color(self, c: QColor) -> None:
        """Set button colour and emit colorChanged."""
        self._color = c
        self._refresh()
        self.colorChanged.emit()

    def _refresh(self) -> None:
        self.setStyleSheet(
            f"background:{self._color.name()};"
            "border:1px solid #888;border-radius:3px;"
        )

    @property
    def color(self) -> QColor:
        return self._color


class _ClickableLabel(QLabel):
    """QLabel that emits a pixel-position signal on left-click (eyedropper)."""

    clicked = Signal(int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(int(event.position().x()), int(event.position().y()))
        super().mousePressEvent(event)


def _make_slider(lo: int, hi: int, value: int) -> QSlider:
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(lo, hi)
    s.setValue(value)
    return s


# ---------------------------------------------------------------------------
# Generate background dialog
# ---------------------------------------------------------------------------


class GenerateBackgroundDialog(QDialog):
    """Pick a colour and adjust radial-gradient params with live 280x280 preview."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generate background")
        self.setMinimumWidth(580)

        self._solid = 35
        self._trans = 25

        self._preview = QLabel()
        self._preview.setFixedSize(_PREVIEW, _PREVIEW)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._color_btn = _ColorButton(QColor(220, 220, 220))
        self._color_btn.colorChanged.connect(self._refresh)

        self._radius_sl = _make_slider(0, 100, self._solid)
        self._radius_lbl = QLabel(f"{self._solid}%")
        self._radius_sl.valueChanged.connect(self._on_radius)

        self._trans_sl = _make_slider(0, 100, self._trans)
        self._trans_lbl = QLabel(f"{self._trans}%")
        self._trans_sl.valueChanged.connect(self._on_trans)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        ctrl = QVBoxLayout()
        ctrl.setSpacing(6)
        ctrl.addWidget(QLabel("Colour:"))
        ctrl.addWidget(self._color_btn)
        ctrl.addWidget(QLabel("Solid radius (0-100 %):"))
        ctrl.addWidget(self._radius_sl)
        ctrl.addWidget(self._radius_lbl)
        ctrl.addWidget(QLabel("Transition width (0-100 %):"))
        ctrl.addWidget(self._trans_sl)
        ctrl.addWidget(self._trans_lbl)
        ctrl.addStretch()
        ctrl.addWidget(buttons)

        row = QHBoxLayout(self)
        row.addWidget(self._preview)
        row.addLayout(ctrl)

        self._refresh()

    def _on_radius(self, v: int) -> None:
        self._solid = v
        self._radius_lbl.setText(f"{v}%")
        self._refresh()

    def _on_trans(self, v: int) -> None:
        self._trans = v
        self._trans_lbl.setText(f"{v}%")
        self._refresh()

    def _refresh(self) -> None:
        c = self._color_btn.color
        img = generate_radial_gradient(
            (c.red(), c.green(), c.blue()),
            canvas_size=_PREVIEW,
            solid_radius=self._solid / 100.0,
            transition_width=self._trans / 100.0,
        )
        self._preview.setPixmap(_pil_to_pixmap(_on_checker(img, _PREVIEW)))

    def get_image(self) -> Image.Image:
        """Return the final 1000x1000 generated image."""
        c = self._color_btn.color
        return generate_radial_gradient(
            (c.red(), c.green(), c.blue()),
            canvas_size=1000,
            solid_radius=self._solid / 100.0,
            transition_width=self._trans / 100.0,
        )


# ---------------------------------------------------------------------------
# Remove background dialog
# ---------------------------------------------------------------------------


class RemoveBackgroundDialog(QDialog):
    """Adjust BG-removal params with side-by-side before/after live preview.

    Click on the Original preview to pick the background colour (eyedropper).
    """

    def __init__(self, source: Image.Image, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Remove background  —  click Original to pick colour")
        self.setMinimumWidth(780)

        self._source = source.convert("RGBA")
        self._tolerance = 30
        self._softness = 10

        # Before — clickable for eyedropper
        before_col = QVBoxLayout()
        hint = QLabel("Original  │  💧 click to pick colour")
        hint.setStyleSheet("color:#aaa;font-size:11px;")
        before_col.addWidget(hint)
        self._before_lbl = _ClickableLabel()
        self._before_lbl.setFixedSize(_PREVIEW, _PREVIEW)
        self._before_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._before_lbl.setPixmap(
            _pil_to_pixmap(_on_checker(self._source, _PREVIEW))
        )
        self._before_lbl.clicked.connect(self._on_eyedrop)
        before_col.addWidget(self._before_lbl)

        # After
        after_col = QVBoxLayout()
        after_col.addWidget(QLabel("Result"))
        self._after_lbl = QLabel()
        self._after_lbl.setFixedSize(_PREVIEW, _PREVIEW)
        self._after_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        after_col.addWidget(self._after_lbl)

        # Controls
        self._color_btn = _ColorButton(QColor(255, 255, 255))
        self._color_btn.colorChanged.connect(self._refresh)

        self._tol_sl = _make_slider(0, 150, self._tolerance)
        self._tol_lbl = QLabel(str(self._tolerance))
        self._tol_sl.valueChanged.connect(self._on_tol)

        self._soft_sl = _make_slider(0, 80, self._softness)
        self._soft_lbl = QLabel(str(self._softness))
        self._soft_sl.valueChanged.connect(self._on_soft)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        ctrl = QVBoxLayout()
        ctrl.setSpacing(6)
        ctrl.addWidget(QLabel("Colour to remove:"))
        ctrl.addWidget(self._color_btn)
        ctrl.addWidget(QLabel("Tolerance (0-150):"))
        ctrl.addWidget(self._tol_sl)
        ctrl.addWidget(self._tol_lbl)
        ctrl.addWidget(QLabel("Softness (0-80):"))
        ctrl.addWidget(self._soft_sl)
        ctrl.addWidget(self._soft_lbl)
        ctrl.addStretch()
        ctrl.addWidget(buttons)

        row = QHBoxLayout(self)
        row.addLayout(before_col)
        row.addLayout(after_col)
        row.addLayout(ctrl)

        self._refresh()

    # ------------------------------------------------------------------ slots

    def _on_eyedrop(self, px: int, py: int) -> None:
        """Sample the pixel at (px, py) within the preview and set as target colour."""
        w, h = self._source.size
        x = max(0, min(w - 1, int(px / _PREVIEW * w)))
        y = max(0, min(h - 1, int(py / _PREVIEW * h)))
        pixel = self._source.getpixel((x, y))
        r, g, b = pixel[0], pixel[1], pixel[2]
        self._color_btn.set_color(QColor(r, g, b))

    def _on_tol(self, v: int) -> None:
        self._tolerance = v
        self._tol_lbl.setText(str(v))
        self._refresh()

    def _on_soft(self, v: int) -> None:
        self._softness = v
        self._soft_lbl.setText(str(v))
        self._refresh()

    def _refresh(self) -> None:
        c = self._color_btn.color
        small = self._source.resize((_PREVIEW, _PREVIEW), Image.LANCZOS)
        result = remove_background_by_color(
            small,
            (c.red(), c.green(), c.blue()),
            self._tolerance,
            self._softness,
        )
        self._after_lbl.setPixmap(_pil_to_pixmap(_on_checker(result, _PREVIEW)))

    def get_result(self) -> Image.Image:
        """Return the processed full-resolution image."""
        c = self._color_btn.color
        return remove_background_by_color(
            self._source,
            (c.red(), c.green(), c.blue()),
            self._tolerance,
            self._softness,
        )
