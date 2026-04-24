---
mode: agent
description: Implement the WooCommerce catalog browser panel
---

# Implement catalog_panel.py

Create `src/product_gallery_normalizer/catalog_panel.py`.
This is a **GUI module** — may import PySide6 and core modules.

## Class: CatalogPanel(QWidget)

Target width: ~300px. This panel lets the user browse, search, and select
WooCommerce products without opening WordPress.

### Signals
```python
product_selected = Signal(WooProduct)   # emitted on single click
product_updated  = Signal(WooProduct)   # emitted after a successful save
```

### Layout (top to bottom)
```
QLineEdit  ← search bar, placeholder "Search products…"
QComboBox  ← status filter: "Any status" / "Published" / "Draft"
QListWidget ← product list, flex height, multi-select (ExtendedSelection)
QWidget    ← pagination row: [◄ Prev]  [Page N of M]  [► Next]
QPushButton ← "⚙ WooCommerce Settings" (full width, flat style)
```

### Product list items
- Each `QListWidgetItem` shows two lines:
  - Line 1 (bold): product name
  - Line 2 (smaller, grey): SKU · $price
- Store the `WooProduct` object with `item.setData(Qt.UserRole, product)`
- Single click → emit `product_selected`
- Double click → open `ProductEditorDialog(product, client, parent=self)`
- Right-click → context menu (see "Context menu" section below)

### Initial state
- On `__init__`, check if `config.woocommerce.store_url` is non-empty
- If no credentials: hide the list and pagination, show a centred label:
  "Connect your WooCommerce store\n⚙ Settings"
- If credentials exist: call `_load_products()`

### Search & pagination
- Search bar: after each keystroke, wait 500 ms (debounce via `QTimer.singleShot`)
  before calling `_load_products(page=1)`
- Page size: 20 products per page
- "◄ Prev" / "► Next" buttons call `_load_products(page=current±1)`
- While loading: disable search, filter, and nav buttons; show "Loading…" as the
  single list item

### API calls
- All calls to `WooCommerceClient` run inside `_FetchWorker(QThread)`:
  ```python
  class _FetchWorker(QThread):
      finished = Signal(list)   # list[WooProduct]
      error    = Signal(str)
  ```
- On `error`: re-enable controls, show error text as single disabled list item

### Method: set_credentials(credentials: WooCredentials) -> None
- Store credentials, rebuild `WooCommerceClient`, call `_load_products(page=1)`

### On product_updated
- Receive an updated `WooProduct`; find its matching list item by `product.id` and
  refresh its display text in place (no full reload)

### Context menu (right-click on list)
- "Edit product…" → open `ProductEditorDialog`
- Separator
- "Publish" → call `bulk_set_status` for all selected items with `status="publish"`
- "Set as draft" → call `bulk_set_status` with `status="draft"`
- Separator
- "Apply sale…" → open a small inline `QDialog` with a QDoubleSpinBox (0–99%)
  asking for discount percentage, then call `bulk_set_sale(multiplier=1-pct/100)`
- "Remove sale" → call `bulk_set_sale(clear_sale=True)`
- Batch actions run in a `QThread` and show a `QProgressDialog`

### Integration in window.py
- Wrap `CatalogPanel` in a `QDockWidget` titled "WooCommerce Catalog"
- Dock it on the right side (`Qt.RightDockWidgetArea`), below the properties panel
- Add menu item **View → "WooCommerce Catalog"** (checkable, toggles dock visibility)
- Wire `CredentialsDialog.credentials_saved` → `CatalogPanel.set_credentials` and
  also save to config via `save_config`
- Open `CredentialsDialog` when "⚙ WooCommerce Settings" is clicked
