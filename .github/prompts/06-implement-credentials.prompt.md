---
mode: agent
description: Persist WooCommerce credentials in config and add a credentials dialog
---

# Extend config.py and implement credentials_dialog.py

## Part 1: Extend config.py

The existing `config.py` has an `AppConfig` Pydantic model and load/save functions.

- Import `WooCredentials` from `woocommerce_models`
- Add a `woocommerce: WooCredentials = WooCredentials()` field to `AppConfig`
- Verify that the existing `save_config` / `load_config` functions round-trip the new
  field correctly through JSON — no other changes needed if Pydantic handles it

## Part 2: Create credentials_dialog.py

Create `src/product_gallery_normalizer/credentials_dialog.py`.
This is a **GUI module** — may import PySide6 and core modules.

### Class: CredentialsDialog(QDialog)

Constructor: `__init__(self, credentials: WooCredentials, parent=None)`

### Signal
```python
credentials_saved = Signal(WooCredentials)
```

### Layout (vertical)
```
QFormLayout:
  "Store URL"         QLineEdit  (placeholder: "https://mystore.com")
  "Consumer Key"      QLineEdit  (placeholder: "ck_...")
  "Consumer Secret"   QLineEdit  (placeholder: "cs_...", echoMode=Password)

[Test Connection]        [Cancel]   [Save]
```

### Behaviour
- Pre-fill all three fields from the `WooCredentials` passed to the constructor
- "Test Connection" button: read current field values, instantiate
  `WooCommerceClient(credentials)`, call `get_categories()` in a `_TestConnectionWorker`
  (see below), then show a `QMessageBox`:
  - Success: "✓ Connected — {n} categories found"
  - Failure: "✗ Connection failed — check your credentials and store URL"
- "Save" button: emit `credentials_saved` with a `WooCredentials` built from current
  field values, then `self.accept()`
- "Cancel" button: `self.reject()`

### Worker: _TestConnectionWorker(QThread)
```python
class _TestConnectionWorker(QThread):
    result = Signal(bool, str)   # (success, message)
```
- Accepts a `WooCommerceClient` instance
- In `run()`: call `client.get_categories()`, emit `result(True, f"{n} categories found")`
  on success or `result(False, str(exception))` on failure
- The dialog disables "Test Connection" while the worker is running and re-enables it
  in the `result` slot
