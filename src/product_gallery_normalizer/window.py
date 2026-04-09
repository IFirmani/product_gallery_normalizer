"""QMainWindow: left tools panel, canvas, right properties panel, bottom gallery."""

import io
import logging
import tempfile
from pathlib import Path
from typing import Literal

from PIL import Image as PilImage
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from product_gallery_normalizer.canvas import CanvasScene, CanvasView
from product_gallery_normalizer.config import AppConfig, ImageTransform
from product_gallery_normalizer.gallery import Gallery

logger = logging.getLogger(__name__)

_THUMB = 80
_LEFT_W = 165
_RIGHT_W = 200

_BTN_STYLE = (
    "QPushButton{background:#3c3f41;color:#ddd;border:1px solid #555;"
    "border-radius:4px;font-size:12px;}"
    "QPushButton:hover{background:#4c5052;}"
    "QPushButton:pressed{background:#214283;}"
)
_SPIN_STYLE = (
    "QDoubleSpinBox{background:#1e1e1e;color:#ddd;border:1px solid #555;"
    "border-radius:3px;padding:2px 4px;}"
    "QDoubleSpinBox::up-button,QDoubleSpinBox::down-button{width:16px;}"
)


class MainWindow(QMainWindow):
    """Main application window: left tools | canvas | right properties, bottom gallery."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("product_gallery_normalizer")
        self.resize(1500, 1000)

        self._config = AppConfig()
        self._gallery = Gallery()
        self._scene = CanvasScene()
        self._view = CanvasView(self._scene)
        self._temp_dir = Path(tempfile.mkdtemp(prefix="pgn_"))
        self._updating_props = False

        self._build_ui()
        self._build_status_bar()
        self._scene.product_transform_changed.connect(self._on_canvas_transform_changed)

    # ================================================================ layout

    def _build_ui(self) -> None:
        left = self._make_left_panel()
        right = self._make_right_panel()

        centre_row = QHBoxLayout()
        centre_row.setContentsMargins(0, 0, 0, 0)
        centre_row.setSpacing(0)
        centre_row.addWidget(left)
        centre_row.addWidget(self._view, stretch=1)
        centre_row.addWidget(right)

        gallery_bar = self._make_gallery_bar()

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        centre_widget = QWidget()
        centre_widget.setLayout(centre_row)
        root.addWidget(centre_widget, stretch=1)
        root.addWidget(gallery_bar)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

    # ------------------------------------------------------------------ left panel

    def _make_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(_LEFT_W)
        panel.setStyleSheet("background:#2b2b2b;")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(6)

        def section(title: str) -> QLabel:
            lbl = QLabel(
                f"<span style='color:#aaa;font-size:11px'><b>{title}</b></span>"
            )
            return lbl

        def btn(label: str) -> QPushButton:
            b = QPushButton(label)
            b.setFixedHeight(34)
            b.setStyleSheet(_BTN_STYLE)
            return b

        layout.addWidget(section("Background"))
        b_open_bg = btn("Open PNG…")
        b_open_bg.clicked.connect(self._on_open_background)
        layout.addWidget(b_open_bg)
        b_gen_bg = btn("Generate…")
        b_gen_bg.clicked.connect(self._on_generate_background)
        layout.addWidget(b_gen_bg)

        layout.addWidget(self._sep())

        layout.addWidget(section("Product"))
        b_open_folder = btn("Open folder…")
        b_open_folder.clicked.connect(self._on_open_folder)
        layout.addWidget(b_open_folder)
        b_remove = btn("Remove BG…")
        b_remove.clicked.connect(self._on_remove_product_bg)
        layout.addWidget(b_remove)

        layout.addWidget(self._sep())

        layout.addWidget(section("Export"))
        b_export = btn("Export batch…")
        b_export.clicked.connect(self._on_export)
        layout.addWidget(b_export)

        layout.addStretch()
        return panel

    # ------------------------------------------------------------------ right panel

    def _make_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(_RIGHT_W)
        panel.setStyleSheet("background:#2b2b2b;")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(6)

        def section(title: str) -> QLabel:
            return QLabel(
                f"<span style='color:#aaa;font-size:11px'><b>{title}</b></span>"
            )

        def field_lbl(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet("color:#bbb;font-size:11px;")
            return lbl

        layout.addWidget(section("Properties"))
        layout.addWidget(self._sep())

        # --- Position ---
        layout.addWidget(section("Position"))
        self._prop_x = self._make_spinbox(-5000, 5000, 500, 1, " px")
        self._prop_y = self._make_spinbox(-5000, 5000, 500, 1, " px")
        layout.addWidget(field_lbl("X"))
        layout.addWidget(self._prop_x)
        layout.addWidget(field_lbl("Y"))
        layout.addWidget(self._prop_y)
        layout.addWidget(self._sep())

        # --- Rotation ---
        layout.addWidget(section("Rotation"))
        self._prop_rot = self._make_spinbox(-360, 360, 0, 1, "°")
        layout.addWidget(self._prop_rot)
        self._rot_sl = self._make_slider(-360, 360, 0)
        layout.addWidget(self._rot_sl)
        layout.addWidget(self._sep())

        # --- Scale ---
        layout.addWidget(section("Scale"))
        self._prop_scale = self._make_spinbox(0.01, 20.0, 1.0, 3, "×")
        layout.addWidget(self._prop_scale)
        self._scale_sl = self._make_slider(1, 2000, 100)  # ×100 of actual scale
        layout.addWidget(self._scale_sl)
        layout.addWidget(self._sep())

        # --- Reset ---
        reset_btn = QPushButton("Reset transform")
        reset_btn.setFixedHeight(30)
        reset_btn.setStyleSheet(_BTN_STYLE)
        reset_btn.clicked.connect(self._on_reset_transform)
        layout.addWidget(reset_btn)

        layout.addStretch()

        # Connect props → canvas
        self._prop_x.valueChanged.connect(self._on_props_changed)
        self._prop_y.valueChanged.connect(self._on_props_changed)
        self._prop_rot.valueChanged.connect(self._on_props_changed)
        self._prop_scale.valueChanged.connect(self._on_props_changed)
        self._rot_sl.valueChanged.connect(self._on_rot_slider)
        self._scale_sl.valueChanged.connect(self._on_scale_slider)

        return panel

    def _make_spinbox(
        self, lo: float, hi: float, val: float, decimals: int, suffix: str = ""
    ) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(lo, hi)
        sb.setValue(val)
        sb.setDecimals(decimals)
        sb.setSuffix(suffix)
        sb.setStyleSheet(_SPIN_STYLE)
        sb.setSingleStep(0.05 if decimals >= 2 else 1.0)
        return sb

    @staticmethod
    def _make_slider(lo: int, hi: int, val: int) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        s.setStyleSheet(
            "QSlider::groove:horizontal{height:4px;background:#444;border-radius:2px;}"
            "QSlider::handle:horizontal{width:14px;height:14px;margin:-5px 0;"
            "background:#5d9eff;border-radius:7px;}"
            "QSlider::sub-page:horizontal{background:#4a80d4;border-radius:2px;}"
        )
        return s

    # ------------------------------------------------------------------ gallery bar

    def _make_gallery_bar(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setFixedHeight(_THUMB + 24)
        wrapper.setStyleSheet("background:#1a1a1a;")

        outer = QHBoxLayout(wrapper)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        prev_btn = QPushButton("◄")
        prev_btn.setFixedSize(28, _THUMB + 4)
        prev_btn.setStyleSheet(
            "QPushButton{background:#333;color:#aaa;border:none;font-size:16px;}"
            "QPushButton:hover{color:#fff;}"
        )
        prev_btn.clicked.connect(self._on_prev)

        next_btn = QPushButton("►")
        next_btn.setFixedSize(28, _THUMB + 4)
        next_btn.setStyleSheet(
            "QPushButton{background:#333;color:#aaa;border:none;font-size:16px;}"
            "QPushButton:hover{color:#fff;}"
        )
        next_btn.clicked.connect(self._on_next)

        scroll = QScrollArea()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:#1a1a1a;")

        self._thumb_row = QWidget()
        self._thumb_row.setStyleSheet("background:#1a1a1a;")
        self._thumb_layout = QHBoxLayout(self._thumb_row)
        self._thumb_layout.setContentsMargins(2, 2, 2, 2)
        self._thumb_layout.setSpacing(4)
        scroll.setWidget(self._thumb_row)

        outer.addWidget(prev_btn)
        outer.addWidget(scroll, stretch=1)
        outer.addWidget(next_btn)
        return wrapper

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _sep() -> QWidget:
        s = QWidget()
        s.setFixedHeight(1)
        s.setStyleSheet("background:#555;")
        return s

    def _build_status_bar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    # ================================================================ tool actions

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

    def _on_generate_background(self) -> None:
        from product_gallery_normalizer.dialogs import GenerateBackgroundDialog

        dlg = GenerateBackgroundDialog(parent=self)
        if dlg.exec() != GenerateBackgroundDialog.DialogCode.Accepted:
            return

        img = dlg.get_image()                              # 1000x1000 PIL Image
        temp_path = self._temp_dir / "generated_background.png"
        img.save(str(temp_path))                           # save for compositor
        self._config.background_path = temp_path
        self._scene.set_background_pil(img)                # show without reload
        self._status.showMessage("Background generated (1000x1000)")
        logger.info("Generated background at %s", temp_path)

    def _on_open_folder(self) -> None:
        dir_str = QFileDialog.getExistingDirectory(self, "Open product folder")
        if not dir_str:
            return
        directory = Path(dir_str)
        self._gallery.load_folder(directory)
        self._config.gallery_path = directory
        self._rebuild_thumbnails()
        self._refresh_canvas()
        self._status.showMessage(
            f"Loaded {self._gallery.count} images from {directory.name}"
        )

    def _on_remove_product_bg(self) -> None:
        from product_gallery_normalizer.dialogs import RemoveBackgroundDialog

        item = self._gallery.current
        if item is None:
            self._status.showMessage("Open a product folder first")
            return

        src = PilImage.open(item.path)
        dlg = RemoveBackgroundDialog(src, parent=self)
        if dlg.exec() != RemoveBackgroundDialog.DialogCode.Accepted:
            return

        result = dlg.get_result()
        # Save to temp dir — no user dialog
        temp_path = self._temp_dir / (item.path.stem + "_nobg.png")
        result.save(str(temp_path))
        item.path = temp_path                              # update gallery item
        self._rebuild_thumbnails()
        self._refresh_canvas()
        self._status.showMessage(f"Background removed: {temp_path.name}")
        logger.info("BG-removed product saved to %s", temp_path)

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

    # ================================================================ properties panel

    def _on_props_changed(self) -> None:
        """User edited a spinbox → push transform to canvas and gallery."""
        if self._updating_props:
            return
        t = ImageTransform(
            x=self._prop_x.value(),
            y=self._prop_y.value(),
            rotation=self._prop_rot.value(),
            scale=self._prop_scale.value(),
        )
        self._scene.apply_transform(t)
        if self._gallery.current is not None:
            self._gallery.update_current_transform(t)
        # Keep sliders in sync when spinboxes are edited directly
        self._rot_sl.blockSignals(True)
        self._rot_sl.setValue(int(t.rotation))
        self._rot_sl.blockSignals(False)
        self._scale_sl.blockSignals(True)
        self._scale_sl.setValue(int(t.scale * 100))
        self._scale_sl.blockSignals(False)

    def _on_canvas_transform_changed(
        self, x: float, y: float, rot: float, scale: float
    ) -> None:
        """Canvas item moved → update spinboxes and save to gallery."""
        self._updating_props = True
        try:
            self._prop_x.setValue(x)
            self._prop_y.setValue(y)
            self._prop_rot.setValue(rot)
            self._prop_scale.setValue(scale)
            self._rot_sl.setValue(int(rot))
            self._scale_sl.setValue(int(scale * 100))
        finally:
            self._updating_props = False
        if self._gallery.current is not None:
            self._gallery.update_current_transform(
                ImageTransform(x=x, y=y, rotation=rot, scale=scale)
            )

    def _on_reset_transform(self) -> None:
        t = ImageTransform()
        self._scene.apply_transform(t)
        if self._gallery.current is not None:
            self._gallery.update_current_transform(t)
        self._updating_props = True
        try:
            self._prop_x.setValue(t.x)
            self._prop_y.setValue(t.y)
            self._prop_rot.setValue(t.rotation)
            self._prop_scale.setValue(t.scale)
            self._rot_sl.setValue(int(t.rotation))
            self._scale_sl.setValue(int(t.scale * 100))
        finally:
            self._updating_props = False

    def _update_props_from_transform(self, t: ImageTransform) -> None:
        self._updating_props = True
        try:
            self._prop_x.setValue(t.x)
            self._prop_y.setValue(t.y)
            self._prop_rot.setValue(t.rotation)
            self._prop_scale.setValue(t.scale)
            self._rot_sl.setValue(int(t.rotation))
            self._scale_sl.setValue(int(t.scale * 100))
        finally:
            self._updating_props = False

    def _on_rot_slider(self, v: int) -> None:
        """Rotation slider moved → update spinbox and push to canvas."""
        if self._updating_props:
            return
        self._prop_rot.blockSignals(True)
        self._prop_rot.setValue(float(v))
        self._prop_rot.blockSignals(False)
        self._on_props_changed()

    def _on_scale_slider(self, v: int) -> None:
        """Scale slider moved → update spinbox and push to canvas."""
        if self._updating_props:
            return
        self._prop_scale.blockSignals(True)
        self._prop_scale.setValue(v / 100.0)
        self._prop_scale.blockSignals(False)
        self._on_props_changed()

    # ================================================================ gallery bar

    def _rebuild_thumbnails(self) -> None:
        while self._thumb_layout.count():
            child = self._thumb_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for i, gallery_item in enumerate(self._gallery):
            self._thumb_layout.addWidget(self._make_thumb_btn(gallery_item.path, i))
        self._thumb_layout.addStretch()
        self._highlight_thumb(self._gallery.index)

    def _make_thumb_btn(self, path: Path, index: int) -> QPushButton:
        b = QPushButton()
        b.setFixedSize(_THUMB, _THUMB)
        b.setCheckable(True)
        b.setToolTip(path.name)
        b.setStyleSheet(
            "QPushButton{border:2px solid #555;background:#2a2a2a;padding:0;}"
            "QPushButton:checked{border:2px solid #4a9eff;}"
            "QPushButton:hover{border:2px solid #888;}"
        )
        try:
            img = PilImage.open(path).convert("RGBA")
            img.thumbnail((_THUMB - 4, _THUMB - 4), PilImage.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qimg = QImage.fromData(buf.getvalue())
            b.setIcon(QIcon(QPixmap.fromImage(qimg)))
            b.setIconSize(QSize(_THUMB - 4, _THUMB - 4))
        except Exception:
            b.setText(path.stem[:10])
        b.clicked.connect(lambda _=False, i=index: self._on_thumb_clicked(i))
        return b

    def _on_thumb_clicked(self, index: int) -> None:
        self._save_transform()
        self._gallery.go_to(index)
        self._refresh_canvas()
        self._highlight_thumb(index)

    def _highlight_thumb(self, index: int) -> None:
        n = 0
        for i in range(self._thumb_layout.count()):
            item = self._thumb_layout.itemAt(i)
            w = item.widget() if item else None
            if w is not None:
                w.setChecked(n == index)
                n += 1

    # ================================================================ navigation

    def _on_prev(self) -> None:
        self._save_transform()
        self._gallery.previous()
        self._refresh_canvas()
        self._highlight_thumb(self._gallery.index)

    def _on_next(self) -> None:
        self._save_transform()
        self._gallery.next()
        self._refresh_canvas()
        self._highlight_thumb(self._gallery.index)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Left:
            self._on_prev()
        elif event.key() == Qt.Key.Key_Right:
            self._on_next()
        else:
            super().keyPressEvent(event)

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
        self._update_props_from_transform(item.transform)
        self._status.showMessage(
            f"{self._gallery.index + 1} / {self._gallery.count}"
            f"  —  {item.path.name}"
        )
