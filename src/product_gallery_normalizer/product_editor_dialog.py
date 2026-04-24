"""Product editor dialog for WooCommerce products."""

from __future__ import annotations

import copy
from pathlib import Path

import requests as _requests
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .woocommerce_client import WooCommerceClient
from .woocommerce_models import WooCategory, WooImage, WooProduct

# ──────────────────────────────────────────────────── background workers ──


class _CategoriesLoader(QThread):
    finished = Signal(list)   # list[WooCategory]
    error = Signal(str)

    def __init__(self, client: WooCommerceClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client

    def run(self) -> None:
        try:
            cats = self._client.get_categories()
            self.finished.emit(cats)
        except Exception as exc:
            self.error.emit(str(exc))


class _ThumbnailLoader(QThread):
    thumbnail_ready = Signal(int, QPixmap)   # (list index, pixmap)

    def __init__(
        self,
        items: list[tuple[int, str]],
        session: _requests.Session,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._items = items
        self._session = session
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        for index, url in self._items:
            if self._cancelled or not url:
                continue
            try:
                resp = self._session.get(url, timeout=10)
                resp.raise_for_status()
                pixmap = QPixmap()
                pixmap.loadFromData(resp.content)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(
                        120, 120,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self.thumbnail_ready.emit(index, pixmap)
            except Exception:
                pass


class _SaveWorker(QThread):
    finished = Signal(object)   # WooProduct | None
    error = Signal(str)

    def __init__(
        self,
        client: WooCommerceClient,
        product_id: int,
        patch: dict,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._product_id = product_id
        self._patch = patch

    def run(self) -> None:
        try:
            result = self._client.update_product(self._product_id, self._patch)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class _UploadWorker(QThread):
    finished = Signal(object)   # WooImage | None
    error = Signal(str)

    def __init__(
        self,
        client: WooCommerceClient,
        path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._path = path

    def run(self) -> None:
        try:
            result = self._client.upload_image(self._path)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class _CategoryActionWorker(QThread):
    """Generic worker for create/update/delete category actions."""

    finished = Signal(object)  # result value (WooCategory | bool)
    error = Signal(str)

    def __init__(self, fn, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            self.finished.emit(self._fn())
        except Exception as exc:
            self.error.emit(str(exc))


# ──────────────────────────────────────────────────────────────── dialog ──

_STATUS_VALUES = ["publish", "draft", "pending", "private"]
_STOCK_VALUES = ["instock", "outofstock", "onbackorder"]


class ProductEditorDialog(QDialog):
    """Full-featured editor for a single WooCommerce product."""

    product_saved = Signal(WooProduct)
    request_canvas_export = Signal()

    def __init__(
        self,
        product: WooProduct,
        client: WooCommerceClient,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit — {product.name}")
        self.setMinimumSize(640, 560)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._product = product
        self._original = copy.deepcopy(product)
        self._client = client
        self._images: list[WooImage] = list(product.images)
        self._thumb_loader: _ThumbnailLoader | None = None
        self._workers: list[QThread] = []

        # shared requests session for thumbnail downloads
        import requests as req
        self._req_session = req.Session()   # no auth — thumbnails are public URLs

        self._build_ui()
        self._populate_fields(product)
        self._load_categories()
        self._load_thumbnails()

    # ─────────────────────────────────────────────────────── UI building ──

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_description_tab(), "Description")
        tabs.addTab(self._build_categories_tab(), "Categories")
        tabs.addTab(self._build_images_tab(), "Images")

        self._save_btn = QPushButton("Save changes")
        self._save_btn.setEnabled(False)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self._save_btn.clicked.connect(self._on_save)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._save_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs, stretch=1)
        layout.addLayout(btn_row)

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._name_edit = self._line_edit()
        self._sku_edit = self._line_edit()

        self._status_combo = QComboBox()
        self._status_combo.addItems(_STATUS_VALUES)

        self._regular_price_spin = self._price_spin()
        self._sale_price_spin = self._price_spin()

        self._manage_stock_cb = QCheckBox()
        self._stock_qty_spin = QSpinBox()
        self._stock_qty_spin.setRange(0, 99_999)
        self._stock_qty_spin.setEnabled(False)
        self._manage_stock_cb.toggled.connect(self._stock_qty_spin.setEnabled)

        self._stock_status_combo = QComboBox()
        self._stock_status_combo.addItems(_STOCK_VALUES)

        form.addRow("Name", self._name_edit)
        form.addRow("SKU", self._sku_edit)
        form.addRow("Status", self._status_combo)
        form.addRow("Regular Price", self._regular_price_spin)
        form.addRow("Sale Price", self._sale_price_spin)
        form.addRow("Manage Stock", self._manage_stock_cb)
        form.addRow("Stock Qty", self._stock_qty_spin)
        form.addRow("Stock Status", self._stock_status_combo)

        for widget in (
            self._name_edit,
            self._sku_edit,
            self._status_combo,
            self._regular_price_spin,
            self._sale_price_spin,
            self._manage_stock_cb,
            self._stock_qty_spin,
            self._stock_status_combo,
        ):
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self._mark_dirty)
            elif hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._mark_dirty)
            elif hasattr(widget, "currentIndexChanged"):
                widget.currentIndexChanged.connect(self._mark_dirty)
            elif hasattr(widget, "toggled"):
                widget.toggled.connect(self._mark_dirty)

        return w

    def _build_description_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Description"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setAcceptRichText(True)
        self._desc_edit.textChanged.connect(self._mark_dirty)
        layout.addWidget(self._desc_edit)
        layout.addWidget(QLabel("Short Description"))
        self._short_desc_edit = QTextEdit()
        self._short_desc_edit.setAcceptRichText(True)
        self._short_desc_edit.textChanged.connect(self._mark_dirty)
        layout.addWidget(self._short_desc_edit)
        return w

    def _build_categories_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self._cat_list = QListWidget()
        self._cat_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._cat_list.itemChanged.connect(self._mark_dirty)
        self._cat_list.itemSelectionChanged.connect(self._update_cat_buttons)
        layout.addWidget(self._cat_list)

        btn_row = QHBoxLayout()
        self._new_cat_btn = QPushButton("+ New category")
        self._rename_cat_btn = QPushButton("✎ Rename")
        self._delete_cat_btn = QPushButton("🗑 Delete")
        self._rename_cat_btn.setEnabled(False)
        self._delete_cat_btn.setEnabled(False)
        self._new_cat_btn.clicked.connect(self._on_new_category)
        self._rename_cat_btn.clicked.connect(self._on_rename_category)
        self._delete_cat_btn.clicked.connect(self._on_delete_categories)
        btn_row.addWidget(self._new_cat_btn)
        btn_row.addWidget(self._rename_cat_btn)
        btn_row.addWidget(self._delete_cat_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    def _build_images_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self._img_list = QListWidget()
        self._img_list.setViewMode(QListWidget.ViewMode.IconMode)
        self._img_list.setIconSize(QPixmap(120, 120).size())
        self._img_list.setFlow(QListWidget.Flow.LeftToRight)
        self._img_list.setWrapping(False)
        self._img_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._img_list.setMovement(QListWidget.Movement.Static)
        layout.addWidget(self._img_list, stretch=1)

        btn_row = QHBoxLayout()
        upload_btn = QPushButton("Upload from file…")
        canvas_btn = QPushButton("Use canvas export")
        remove_btn = QPushButton("Remove selected")
        upload_btn.clicked.connect(self._on_upload_image)
        canvas_btn.clicked.connect(self._on_use_canvas_export)
        remove_btn.clicked.connect(self._on_remove_images)
        btn_row.addWidget(upload_btn)
        btn_row.addWidget(canvas_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    # ─────────────────────────────────────────────────── field population ──

    def _populate_fields(self, product: WooProduct) -> None:
        self._name_edit.setText(product.name)
        self._sku_edit.setText(product.sku)
        idx = _STATUS_VALUES.index(product.status) if product.status in _STATUS_VALUES else 0
        self._status_combo.setCurrentIndex(idx)
        self._regular_price_spin.setValue(product.regular_price_float)
        sale_val = float(product.sale_price) if product.sale_price else 0.0
        self._sale_price_spin.setValue(sale_val)
        self._manage_stock_cb.setChecked(product.manage_stock)
        self._stock_qty_spin.setValue(product.stock_quantity or 0)
        si = _STOCK_VALUES.index(product.stock_status) if product.stock_status in _STOCK_VALUES else 0
        self._stock_status_combo.setCurrentIndex(si)
        self._desc_edit.setHtml(product.description)
        self._short_desc_edit.setHtml(product.short_description)

        self._img_list.clear()
        for image in self._images:
            item = QListWidgetItem(image.name or image.alt or str(image.id))
            item.setData(Qt.ItemDataRole.UserRole, image)
            self._img_list.addItem(item)

    def _load_thumbnails(self) -> None:
        if self._thumb_loader is not None:
            self._thumb_loader.cancel()
        pairs = [
            (i, img.src)
            for i, img in enumerate(self._images)
            if img.src
        ]
        if not pairs:
            return
        self._thumb_loader = _ThumbnailLoader(pairs, self._req_session, parent=self)
        self._thumb_loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._thumb_loader.start()

    def _on_thumbnail_ready(self, index: int, pixmap: QPixmap) -> None:
        item = self._img_list.item(index)
        if item is not None:
            from PySide6.QtGui import QIcon
            item.setIcon(QIcon(pixmap))

    # ──────────────────────────────────────────────── categories loading ──

    def _load_categories(self) -> None:
        self._cat_list.clear()
        loading = QListWidgetItem("Loading categories…")
        loading.setFlags(loading.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self._cat_list.addItem(loading)

        worker = _CategoriesLoader(self._client, parent=self)
        worker.finished.connect(self._on_categories_loaded)
        worker.error.connect(self._on_categories_error)
        self._workers.append(worker)
        worker.start()

    def _on_categories_loaded(self, categories: list) -> None:
        self._cat_list.clear()
        assigned_ids = {c.id for c in self._product.categories}
        self._cat_list.blockSignals(True)
        for cat in categories:
            item = QListWidgetItem(cat.name)
            item.setData(Qt.ItemDataRole.UserRole, cat)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            state = Qt.CheckState.Checked if cat.id in assigned_ids else Qt.CheckState.Unchecked
            item.setCheckState(state)
            self._cat_list.addItem(item)
        self._cat_list.blockSignals(False)

    def _on_categories_error(self, msg: str) -> None:
        self._cat_list.clear()
        err = QListWidgetItem("Could not load categories.")
        err.setFlags(err.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self._cat_list.addItem(err)
        logger.error("Categories load error: %s", msg)

    def _update_cat_buttons(self) -> None:
        n = len(self._cat_list.selectedItems())
        self._rename_cat_btn.setEnabled(n == 1)
        self._delete_cat_btn.setEnabled(n >= 1)

    # ──────────────────────────────────────────────── category actions ──

    def _on_new_category(self) -> None:
        name, ok = QInputDialog.getText(self, "New Category", "Category name:")
        if not ok or not name.strip():
            return
        worker = _CategoryActionWorker(
            lambda n=name.strip(): self._client.create_category(n), parent=self
        )
        worker.finished.connect(self._on_category_created)
        worker.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        self._workers.append(worker)
        worker.start()

    def _on_category_created(self, cat: object) -> None:
        if not isinstance(cat, WooCategory):
            return
        self._cat_list.blockSignals(True)
        item = QListWidgetItem(cat.name)
        item.setData(Qt.ItemDataRole.UserRole, cat)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        self._cat_list.addItem(item)
        self._cat_list.blockSignals(False)
        self._cat_list.scrollToItem(item)
        self._mark_dirty()

    def _on_rename_category(self) -> None:
        selected = self._cat_list.selectedItems()
        if len(selected) != 1:
            return
        item = selected[0]
        cat: WooCategory = item.data(Qt.ItemDataRole.UserRole)
        new_name, ok = QInputDialog.getText(
            self, "Rename Category", "New name:", text=cat.name
        )
        if not ok or not new_name.strip():
            return
        worker = _CategoryActionWorker(
            lambda cid=cat.id, n=new_name.strip(): self._client.update_category(cid, {"name": n}),
            parent=self,
        )
        worker.finished.connect(lambda result, it=item: self._on_category_renamed(result, it))
        worker.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        self._workers.append(worker)
        worker.start()

    def _on_category_renamed(self, cat: object, item: QListWidgetItem) -> None:
        if not isinstance(cat, WooCategory):
            return
        item.setText(cat.name)
        item.setData(Qt.ItemDataRole.UserRole, cat)

    def _on_delete_categories(self) -> None:
        selected = self._cat_list.selectedItems()
        if not selected:
            return
        n = len(selected)
        noun = "category" if n == 1 else "categories"
        reply = QMessageBox.warning(
            self,
            "Confirm Delete",
            f"Delete {n} {noun}? Products will not be deleted.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Ok:
            return

        original_ids = {c.id for c in self._original.categories}
        cats_to_delete: list[WooCategory] = [
            it.data(Qt.ItemDataRole.UserRole) for it in selected
        ]

        def _do_deletes(cats=cats_to_delete):
            return [self._client.delete_category(c.id, force=True) for c in cats]

        worker = _CategoryActionWorker(_do_deletes, parent=self)
        worker.finished.connect(
            lambda _result, items=selected, oids=original_ids, cats=cats_to_delete:
                self._on_categories_deleted(items, oids, cats)
        )
        worker.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        self._workers.append(worker)
        worker.start()

    def _on_categories_deleted(
        self,
        items: list[QListWidgetItem],
        original_ids: set[int],
        cats: list[WooCategory],
    ) -> None:
        dirty = False
        for item, cat in zip(items, cats):
            row = self._cat_list.row(item)
            self._cat_list.takeItem(row)
            if cat.id in original_ids:
                dirty = True
        if dirty:
            self._mark_dirty()

    # ─────────────────────────────────────────────────────── image actions ──

    def _on_upload_image(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Upload Image", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path_str:
            return
        self._start_upload(Path(path_str))

    def _on_use_canvas_export(self) -> None:
        self.request_canvas_export.emit()

    def receive_canvas_image(self, path: Path) -> None:
        """Called by the parent window after handling request_canvas_export."""
        self._start_upload(path)

    def _start_upload(self, path: Path) -> None:
        worker = _UploadWorker(self._client, path, parent=self)
        worker.finished.connect(self._on_image_uploaded)
        worker.error.connect(lambda msg: QMessageBox.critical(self, "Upload Error", msg))
        self._workers.append(worker)
        worker.start()

    def _on_image_uploaded(self, image: object) -> None:
        if not isinstance(image, WooImage):
            return
        self._images.insert(0, image)
        self._img_list.blockSignals(True)
        item = QListWidgetItem(image.name or image.alt or str(image.id))
        item.setData(Qt.ItemDataRole.UserRole, image)
        self._img_list.insertItem(0, item)
        self._img_list.blockSignals(False)
        self._mark_dirty()
        if image.src:
            loader = _ThumbnailLoader([(0, image.src)], self._req_session, parent=self)
            loader.thumbnail_ready.connect(self._on_thumbnail_ready)
            self._workers.append(loader)
            loader.start()

    def _on_remove_images(self) -> None:
        for item in self._img_list.selectedItems():
            image: WooImage | None = item.data(Qt.ItemDataRole.UserRole)
            if image in self._images:
                self._images.remove(image)
            self._img_list.takeItem(self._img_list.row(item))
        self._mark_dirty()

    # ──────────────────────────────────────────────────── dirty tracking ──

    def _mark_dirty(self, *_args) -> None:
        self._save_btn.setEnabled(True)

    # ────────────────────────────────────────────────────────── saving ──

    def _build_patch(self) -> dict:
        patch: dict = {}
        if self._name_edit.text() != self._original.name:
            patch["name"] = self._name_edit.text()
        if self._sku_edit.text() != self._original.sku:
            patch["sku"] = self._sku_edit.text()
        new_status = _STATUS_VALUES[self._status_combo.currentIndex()]
        if new_status != self._original.status:
            patch["status"] = new_status
        new_price = f"{self._regular_price_spin.value():.2f}".rstrip("0").rstrip(".")
        if new_price != self._original.regular_price:
            patch["regular_price"] = new_price
        new_sale = f"{self._sale_price_spin.value():.2f}".rstrip("0").rstrip(".")
        if new_sale == "0" or new_sale == "":
            new_sale = ""
        if new_sale != self._original.sale_price:
            patch["sale_price"] = new_sale
        if self._manage_stock_cb.isChecked() != self._original.manage_stock:
            patch["manage_stock"] = self._manage_stock_cb.isChecked()
        new_qty = self._stock_qty_spin.value() if self._manage_stock_cb.isChecked() else None
        if new_qty != self._original.stock_quantity:
            patch["stock_quantity"] = new_qty
        new_stock_status = _STOCK_VALUES[self._stock_status_combo.currentIndex()]
        if new_stock_status != self._original.stock_status:
            patch["stock_status"] = new_stock_status
        new_desc = self._desc_edit.toHtml()
        if new_desc != self._original.description:
            patch["description"] = new_desc
        new_short = self._short_desc_edit.toHtml()
        if new_short != self._original.short_description:
            patch["short_description"] = new_short

        # categories
        checked_ids: list[dict] = []
        for i in range(self._cat_list.count()):
            item = self._cat_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                cat: WooCategory | None = item.data(Qt.ItemDataRole.UserRole)
                if cat is not None:
                    checked_ids.append({"id": cat.id})
        orig_ids = sorted(c.id for c in self._original.categories)
        new_ids = sorted(d["id"] for d in checked_ids)
        if new_ids != orig_ids:
            patch["categories"] = checked_ids

        # images
        orig_image_ids = [img.id for img in self._original.images]
        new_image_ids = [img.id for img in self._images]
        if new_image_ids != orig_image_ids:
            patch["images"] = [{"id": img.id, "src": img.src} for img in self._images]

        return patch

    def _on_save(self) -> None:
        patch = self._build_patch()
        if not patch:
            self.accept()
            return
        self._save_btn.setEnabled(False)
        worker = _SaveWorker(self._client, self._product.id, patch, parent=self)
        worker.finished.connect(self._on_save_finished)
        worker.error.connect(self._on_save_error)
        self._workers.append(worker)
        worker.start()

    def _on_save_finished(self, product: object) -> None:
        if not isinstance(product, WooProduct):
            QMessageBox.critical(self, "Save Error", "Server returned an unexpected response.")
            self._save_btn.setEnabled(True)
            return
        self.product_saved.emit(product)
        self.accept()

    def _on_save_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Save Error", msg)
        self._save_btn.setEnabled(True)

    # ────────────────────────────────────────────────── cleanup on close ──

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._thumb_loader is not None:
            self._thumb_loader.cancel()
        super().closeEvent(event)

    # ──────────────────────────────────────────────────────── helpers ──

    @staticmethod
    def _line_edit():
        from PySide6.QtWidgets import QLineEdit
        return QLineEdit()

    @staticmethod
    def _price_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 9_999_999.0)
        spin.setDecimals(2)
        spin.setPrefix("$")
        return spin
