"""WooCommerce catalog browser panel."""

from __future__ import annotations

import logging
from typing import Literal

from PySide6.QtCore import Qt, QSize, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .config import AppConfig
from .woocommerce_client import WooCommerceClient
from .woocommerce_models import WooCredentials, WooProduct

logger = logging.getLogger(__name__)

_PAGE_SIZE = 20


# ────────────────────────────────────────────────────── background workers ──


class _FetchWorker(QThread):
    """Background worker that fetches a page of products."""

    finished = Signal(list)   # list[WooProduct]
    error = Signal(str)

    def __init__(
        self,
        client: WooCommerceClient,
        page: int,
        per_page: int,
        search: str,
        status: str,
        category: int | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._page = page
        self._per_page = per_page
        self._search = search
        self._status = status
        self._category = category

    def run(self) -> None:
        try:
            products = self._client.get_products(
                page=self._page,
                per_page=self._per_page,
                search=self._search,
                status=self._status,
                category=self._category,
            )
            self.finished.emit(products)
        except Exception as exc:
            self.error.emit(str(exc))


class _BulkWorker(QThread):
    """Background worker that applies an action to multiple products."""

    progress = Signal(int)    # index of item just processed
    finished = Signal(list)   # list[WooProduct] (updated)
    cancelled = Signal()
    error = Signal(str)

    def __init__(
        self,
        client: WooCommerceClient,
        products: list[WooProduct],
        action: Literal["publish", "draft", "sale_set", "sale_clear"],
        sale_multiplier: float = 1.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._products = products
        self._action = action
        self._sale_multiplier = sale_multiplier
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        results: list[WooProduct] = []
        try:
            for i, product in enumerate(self._products):
                if self._cancelled:
                    self.cancelled.emit()
                    return
                if self._action in ("publish", "draft"):
                    updated = self._client.update_product(
                        product.id, {"status": self._action}
                    )
                elif self._action == "sale_set":
                    sale = round(product.regular_price_float * self._sale_multiplier, 2)
                    updated = self._client.update_product(
                        product.id, {"sale_price": str(sale)}
                    )
                else:  # sale_clear
                    updated = self._client.update_product(product.id, {"sale_price": ""})
                if updated is not None:
                    results.append(updated)
                self.progress.emit(i + 1)
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))


# ──────────────────────────────────────────────────────────────── helpers ──


def _item_text(product: WooProduct) -> str:
    price = f"${product.regular_price}" if product.regular_price else "$0"
    sku = product.sku or "—"
    return f"{product.name}\n{sku} · {price}"


# ─────────────────────────────────────────────────────────────────── panel ──


class CatalogPanel(QWidget):
    """WooCommerce product catalog browser."""

    product_selected = Signal(WooProduct)
    product_updated = Signal(WooProduct)
    settings_requested = Signal()

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(300)
        self._config = config
        self._client: WooCommerceClient | None = None
        self._current_page = 1
        self._total_pages = 1
        self._fetch_worker: _FetchWorker | None = None
        self._bulk_worker: _BulkWorker | None = None

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(500)
        self._debounce.timeout.connect(lambda: self._load_products(page=1))

        self._build_ui()

        if config.woocommerce.store_url:
            self._client = WooCommerceClient(config.woocommerce)
            self._show_list_ui()
            self._load_products(page=1)
        else:
            self._show_empty_state()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search products…")
        self._search_edit.textChanged.connect(self._debounce.start)
        layout.addWidget(self._search_edit)

        self._status_combo = QComboBox()
        self._status_combo.addItems(["Any status", "Published", "Draft"])
        self._status_combo.currentIndexChanged.connect(
            lambda _: self._load_products(page=1)
        )
        layout.addWidget(self._status_combo)

        self._empty_label = QLabel(
            "Connect your WooCommerce store\n\u2699 Settings"
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color:#888;font-size:13px;")
        layout.addWidget(self._empty_label)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._list, stretch=1)

        self._pagination = QWidget()
        pag_layout = QHBoxLayout(self._pagination)
        pag_layout.setContentsMargins(0, 0, 0, 0)
        self._prev_btn = QPushButton("◄ Prev")
        self._prev_btn.clicked.connect(
            lambda: self._load_products(page=self._current_page - 1)
        )
        self._page_label = QLabel("Page 1 of 1")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._next_btn = QPushButton("► Next")
        self._next_btn.clicked.connect(
            lambda: self._load_products(page=self._current_page + 1)
        )
        pag_layout.addWidget(self._prev_btn)
        pag_layout.addWidget(self._page_label, stretch=1)
        pag_layout.addWidget(self._next_btn)
        layout.addWidget(self._pagination)

        self._settings_btn = QPushButton("\u2699 WooCommerce Settings")
        self._settings_btn.setFlat(True)
        self._settings_btn.clicked.connect(self.settings_requested)
        layout.addWidget(self._settings_btn)

    def _show_empty_state(self) -> None:
        self._empty_label.setVisible(True)
        self._search_edit.setVisible(False)
        self._status_combo.setVisible(False)
        self._list.setVisible(False)
        self._pagination.setVisible(False)

    def _show_list_ui(self) -> None:
        self._empty_label.setVisible(False)
        self._search_edit.setVisible(True)
        self._status_combo.setVisible(True)
        self._list.setVisible(True)
        self._pagination.setVisible(True)

    # ---------------------------------------------------------------- public

    def set_credentials(self, credentials: WooCredentials) -> None:
        """Update credentials and reload the product list."""
        self._config.woocommerce = credentials
        self._client = WooCommerceClient(credentials)
        self._show_list_ui()
        self._load_products(page=1)

    # ---------------------------------------------------------------- helpers

    def _status_filter(self) -> str:
        return {0: "any", 1: "publish", 2: "draft"}.get(
            self._status_combo.currentIndex(), "any"
        )

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._search_edit.setEnabled(enabled)
        self._status_combo.setEnabled(enabled)
        self._prev_btn.setEnabled(enabled)
        self._next_btn.setEnabled(enabled)

    def _load_products(self, page: int = 1) -> None:
        if self._client is None:
            return
        self._current_page = page
        self._set_controls_enabled(False)
        self._list.clear()
        loading = QListWidgetItem("Loading…")
        loading.setFlags(loading.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self._list.addItem(loading)

        self._fetch_worker = _FetchWorker(
            client=self._client,
            page=page,
            per_page=_PAGE_SIZE,
            search=self._search_edit.text(),
            status=self._status_filter(),
            category=None,
            parent=self,
        )
        self._fetch_worker.finished.connect(self._on_fetch_finished)
        self._fetch_worker.error.connect(self._on_fetch_error)
        self._fetch_worker.start()

    def _on_fetch_finished(self, products: list) -> None:
        self._set_controls_enabled(True)
        self._list.clear()
        for product in products:
            item = QListWidgetItem(_item_text(product))
            item.setSizeHint(QSize(0, 48))
            item.setData(Qt.ItemDataRole.UserRole, product)
            self._list.addItem(item)
        if not products:
            no_item = QListWidgetItem("No products found")
            no_item.setFlags(no_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self._list.addItem(no_item)
        # Infer total pages from result count
        if len(products) == _PAGE_SIZE:
            self._total_pages = max(self._current_page + 1, self._total_pages)
        else:
            self._total_pages = self._current_page
        self._update_pagination()

    def _on_fetch_error(self, message: str) -> None:
        self._set_controls_enabled(True)
        self._list.clear()
        err_item = QListWidgetItem("Could not load products. Check your connection and credentials.")
        err_item.setFlags(err_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self._list.addItem(err_item)
        logger.error("CatalogPanel fetch error: %s", message)

    def _update_pagination(self) -> None:
        self._page_label.setText(f"Page {self._current_page} of {self._total_pages}")
        self._prev_btn.setEnabled(self._current_page > 1)
        self._next_btn.setEnabled(self._current_page < self._total_pages)

    # ---------------------------------------------------------------- item signals

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        product: WooProduct | None = item.data(Qt.ItemDataRole.UserRole)
        if product is not None:
            self.product_selected.emit(product)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        product: WooProduct | None = item.data(Qt.ItemDataRole.UserRole)
        if product is not None and self._client is not None:
            self._open_editor(product)

    def _open_editor(self, product: WooProduct) -> None:
        try:
            from .product_editor_dialog import ProductEditorDialog  # type: ignore[import]
        except ImportError:
            logger.warning("ProductEditorDialog not yet implemented")
            return
        if self._client is None:
            return
        dlg = ProductEditorDialog(product, self._client, parent=self)
        dlg.product_saved.connect(self._on_product_saved)
        dlg.exec()

    def _on_product_saved(self, product: WooProduct) -> None:
        self._refresh_item(product)
        self.product_updated.emit(product)

    def _refresh_item(self, product: WooProduct) -> None:
        """Update the list item text for the given product in-place."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is None:
                continue
            existing: WooProduct | None = item.data(Qt.ItemDataRole.UserRole)
            if existing is not None and existing.id == product.id:
                item.setText(_item_text(product))
                item.setData(Qt.ItemDataRole.UserRole, product)
                break

    # ---------------------------------------------------------------- context menu

    def _on_context_menu(self, pos) -> None:  # type: ignore[override]
        item = self._list.itemAt(pos)
        if item is None or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        selected_products: list[WooProduct] = [
            it.data(Qt.ItemDataRole.UserRole)
            for it in self._list.selectedItems()
            if it.data(Qt.ItemDataRole.UserRole) is not None
        ]
        if not selected_products:
            selected_products = [item.data(Qt.ItemDataRole.UserRole)]

        menu = QMenu(self)
        edit_act = menu.addAction("Edit product…")
        menu.addSeparator()
        publish_act = menu.addAction("Publish")
        draft_act = menu.addAction("Set as draft")
        menu.addSeparator()
        sale_act = menu.addAction("Apply sale…")
        remove_sale_act = menu.addAction("Remove sale")

        action = menu.exec(self._list.viewport().mapToGlobal(pos))

        if action == edit_act:
            clicked_product: WooProduct | None = item.data(Qt.ItemDataRole.UserRole)
            if clicked_product is not None:
                self._open_editor(clicked_product)
        elif action == publish_act:
            self._run_bulk(selected_products, "publish")
        elif action == draft_act:
            self._run_bulk(selected_products, "draft")
        elif action == sale_act:
            self._ask_sale_discount(selected_products)
        elif action == remove_sale_act:
            self._run_bulk(selected_products, "sale_clear")

    def _ask_sale_discount(self, products: list[WooProduct]) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Apply Sale Discount")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Discount percentage:"))
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 99.0)
        spin.setSuffix(" %")
        spin.setValue(10.0)
        layout.addWidget(spin)
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        layout.addWidget(btn_box)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            multiplier = 1.0 - spin.value() / 100.0
            self._run_bulk(products, "sale_set", sale_multiplier=multiplier)

    def _run_bulk(
        self,
        products: list[WooProduct],
        action: Literal["publish", "draft", "sale_set", "sale_clear"],
        sale_multiplier: float = 1.0,
    ) -> None:
        if self._client is None or not products:
            return
        progress_dlg = QProgressDialog(
            f"Updating {len(products)} products…", "Cancel", 0, len(products), self
        )
        progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dlg.show()

        self._bulk_worker = _BulkWorker(
            client=self._client,
            products=products,
            action=action,
            sale_multiplier=sale_multiplier,
            parent=self,
        )
        self._bulk_worker.progress.connect(progress_dlg.setValue)
        self._bulk_worker.finished.connect(progress_dlg.close)
        self._bulk_worker.finished.connect(self._on_bulk_finished)
        self._bulk_worker.error.connect(progress_dlg.close)
        self._bulk_worker.error.connect(
            lambda msg: logger.error("Bulk action error: %s", msg)
        )
        progress_dlg.canceled.connect(self._bulk_worker.cancel)
        self._bulk_worker.start()

    def _on_bulk_finished(self, products: list) -> None:
        for product in products:
            self._refresh_item(product)
            self.product_updated.emit(product)
