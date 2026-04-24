---
mode: agent
description: Implement the product editor dialog for WooCommerce products
---

# Implement product_editor_dialog.py

Create `src/product_gallery_normalizer/product_editor_dialog.py`.
This is a **GUI module** — may import PySide6 and core modules.

## Class: ProductEditorDialog(QDialog)

Constructor: `__init__(self, product: WooProduct, client: WooCommerceClient, parent=None)`
- Store a deep copy of `product` as `self._original` for dirty-tracking
- Store `client` for API calls

### Signals
```python
product_saved          = Signal(WooProduct)   # emitted after successful PATCH
request_canvas_export  = Signal()             # parent must call receive_canvas_image()
```

### Layout — QTabWidget with 4 tabs

#### Tab 1: General
```
QFormLayout:
  "Name"           QLineEdit
  "SKU"            QLineEdit
  "Status"         QComboBox  ← publish / draft / pending / private
  "Regular Price"  QDoubleSpinBox  (range 0–9_999_999, decimals 2, prefix "$")
  "Sale Price"     QDoubleSpinBox  (range 0–9_999_999, decimals 2, prefix "$",
                                    0.00 = no active sale)
  "Manage Stock"   QCheckBox
  "Stock Qty"      QSpinBox  (range 0–99_999, enabled only when Manage Stock checked)
  "Stock Status"   QComboBox  ← instock / outofstock / onbackorder
```
Pre-fill all fields from `product` on open.

#### Tab 2: Description
```
"Description"        QLabel + QTextEdit  (accepts HTML)
"Short Description"  QLabel + QTextEdit  (accepts HTML)
```

#### Tab 3: Categories

```
QListWidget  ← one item per available category, checkable (Qt.ItemIsUserCheckable)
[+ New category]   [✎ Rename]   [🗑 Delete]
```

**Loading categories**
- On dialog open, call `client.get_categories()` in a `_CategoriesLoader(QThread)`:
  ```python
  class _CategoriesLoader(QThread):
      finished = Signal(list)   # list[WooCategory]
      error    = Signal(str)
  ```
- While loading: show a single disabled item "Loading categories…"
- On finish: populate the list; check the items whose `id` is in `product.categories`

**Assigning categories**
- Each `QListWidgetItem` stores the `WooCategory` in `item.setData(Qt.UserRole, category)`
- Checking/unchecking an item marks the dialog as dirty (enables "Save changes")
- On save, collect all checked items and build `{"categories": [{"id": cat.id}, ...]}`
  as part of the patch payload

**Creating a category**
- "+ New category" opens a small `QInputDialog.getText` asking for the category name
- Call `client.create_category(name)` (see note below) in a `QThread`
- On success: add the new `WooCategory` to the list, pre-checked, scroll to it

**Renaming a category**
- "✎ Rename" is enabled only when exactly one item is selected
- Opens `QInputDialog.getText` pre-filled with the current name
- Call `client.update_category(id, {"name": new_name})` in a `QThread`
- On success: update the item text in place

**Deleting a category**
- "🗑 Delete" is enabled when one or more items are selected
- Show a `QMessageBox.warning` confirmation: "Delete {n} category/categories?
  Products will not be deleted."
- Call `client.delete_category(id, force=True)` for each selected item in a `QThread`
- On success: remove items from the list; if any deleted category was in the product's
  original categories, mark the dialog as dirty

**Add to woocommerce_client.py** (extend prompt 05):
```python
def create_category(self, name: str, parent_id: int = 0) -> WooCategory | None:
    # POST /products/categories

def update_category(self, category_id: int, payload: dict) -> WooCategory | None:
    # PUT /products/categories/{id}

def delete_category(self, category_id: int, force: bool = True) -> bool:
    # DELETE /products/categories/{id}?force={force}
```

#### Tab 4: Images
```
QListWidget in IconMode, icon size 120×120, horizontal scroll, wrapping off
[Upload from file…]  [Use canvas export]  [Remove selected]
```

- On open, load existing `product.images`; create one `QListWidgetItem` per image,
  display a placeholder icon immediately, then load thumbnails asynchronously via
  `_ThumbnailLoader` (see below)
- "Upload from file…": open `QFileDialog` (PNG/JPG/WEBP filter), call
  `client.upload_image(path)` in a `QThread`, prepend the returned `WooImage` to the
  local images list and add its item to the widget
- "Use canvas export": emit `request_canvas_export`; the parent window intercepts it,
  exports the canvas to a temp PNG, then calls `dialog.receive_canvas_image(path)`
- "Remove selected": remove the selected items from the local list only (the deletion
  is applied on Save)

### Dirty tracking
- Keep `self._original: WooProduct` (deep copy from constructor)
- Before saving, compare each editable field with `_original`; build a minimal patch
  dict containing only changed fields
- If the patch dict is empty, the "Save changes" button is disabled

### Bottom buttons
```
[Cancel]                        [Save changes]
```
- "Save changes" is disabled when nothing is dirty
- On click: call `client.update_product(product.id, patch)` inside `_SaveWorker(QThread)`,
  on success emit `product_saved(updated_product)` and close the dialog,
  on error show `QMessageBox.critical` and leave the dialog open

### Method: receive_canvas_image(path: Path) -> None
- Called by the parent window after `request_canvas_export` was handled
- Calls `client.upload_image(path)` in a `QThread`, prepends result to images list

### _ThumbnailLoader(QThread)
```python
class _ThumbnailLoader(QThread):
    thumbnail_ready = Signal(int, QPixmap)   # (list index, pixmap)
```
- Takes a list of `(index, url)` pairs
- Downloads each image URL with `requests.get`, converts bytes to `QPixmap`
- Has a `cancel()` method that sets a flag; the loop checks the flag between items
- Is cancelled (via `cancel()`) when the dialog is closed or a new product is loaded
