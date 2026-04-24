---
mode: agent
description: Fix security vulnerabilities found in the WooCommerce integration modules
---

# Security fixes

Apply all of the following fixes. Do not refactor anything outside the scope of each
fix — minimal, targeted changes only.

---

## Fix 1 — Credentials stored in plaintext (HIGH)

**Problem:** `config.py` saves `consumer_key` and `consumer_secret` in
`~/.product_gallery_normalizer/config.json` as plaintext.

**Solution:** Use the `keyring` library to store and retrieve WooCommerce credentials
in the OS secure store (Keychain on macOS, Credential Manager on Windows,
Secret Service on Linux).

### Changes to pyproject.toml
Add `keyring` to `[project.dependencies]`.

### New file: `src/product_gallery_normalizer/credential_store.py` (core module)
```python
"""Secure credential storage using the OS keyring."""

SERVICE_NAME = "product_gallery_normalizer"

def save_credentials(consumer_key: str, consumer_secret: str) -> None:
    """Persist consumer_key and consumer_secret in the OS keyring."""

def load_credentials() -> tuple[str, str]:
    """Return (consumer_key, consumer_secret) from the OS keyring.
    Returns ("", "") if not found."""

def clear_credentials() -> None:
    """Remove stored credentials from the OS keyring."""
```
- Use `keyring.set_password(SERVICE_NAME, "consumer_key", value)` and
  `keyring.set_password(SERVICE_NAME, "consumer_secret", value)`
- Use `keyring.get_password(SERVICE_NAME, key)` to retrieve; return `""` if None

### Changes to `config.py`
- Remove `consumer_key` and `consumer_secret` from `WooCredentials` **when saving to disk**
- `save_config`: before writing JSON, call `save_credentials(...)` then zero out the
  secret fields in the serialised dict so they are never written to disk:
  ```python
  data = config.model_dump(mode="json")
  save_credentials(
      data["woocommerce"].pop("consumer_key", ""),
      data["woocommerce"].pop("consumer_secret", ""),
  )
  # write data (now without secrets) to disk
  ```
- `load_config`: after loading from disk, inject credentials back:
  ```python
  ck, cs = load_credentials()
  config.woocommerce.consumer_key = ck
  config.woocommerce.consumer_secret = cs
  ```

### Changes to `credentials_dialog.py`
- In `_on_save`, after emitting `credentials_saved`, also call
  `save_credentials(credentials.consumer_key, credentials.consumer_secret)`

---

## Fix 2 — Thumbnail loader sends WC credentials to external servers (HIGH)

**File:** `src/product_gallery_normalizer/product_editor_dialog.py`

**Problem:** `_req_session` copies `client._session.auth`, so thumbnail downloads
to external CDN URLs (Cloudflare, S3, etc.) include WooCommerce Basic Auth credentials.

**Solution:** Create a plain session with no auth for thumbnails.

In `ProductEditorDialog.__init__`, replace:
```python
# BEFORE
import requests as req
self._req_session = req.Session()
if hasattr(client, "_session") and hasattr(client._session, "auth"):
    self._req_session.auth = client._session.auth
```
with:
```python
# AFTER
import requests as req
self._req_session = req.Session()   # no auth — thumbnails are public URLs
```

---

## Fix 3 — HTTP header injection via filename (HIGH)

**File:** `src/product_gallery_normalizer/woocommerce_client.py`
**Method:** `upload_image`

**Problem:** `image_path.name` is inserted raw into a `Content-Disposition` header,
allowing header injection via crafted filenames.

**Solution:** Sanitize the filename before embedding it in the header.

Replace the `Content-Disposition` header line with:
```python
safe_name = (
    image_path.name
    .replace('"', "")
    .replace("\r", "")
    .replace("\n", "")
)
# then use safe_name in the header:
"Content-Disposition": f'attachment; filename="{safe_name}"',
```

---

## Fix 4 — HTTP URLs accepted for store_url (MEDIUM)

**File:** `src/product_gallery_normalizer/credentials_dialog.py`
**Method:** `_on_save`

**Problem:** No validation enforces HTTPS, so credentials can be sent in plaintext.

**Solution:** In `_on_save`, check the URL scheme before emitting `credentials_saved`:
```python
url = self._url_edit.text().strip()
if url and not url.startswith("https://"):
    result = QMessageBox.warning(
        self,
        "Insecure Connection",
        "The store URL does not use HTTPS. Your credentials will be sent "
        "unencrypted over the network.\n\nContinue anyway?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if result != QMessageBox.StandardButton.Yes:
        return
```
Add this check at the top of `_on_save`, before building `WooCredentials`.

---

## Fix 5 — Arbitrary file upload (MEDIUM)

**File:** `src/product_gallery_normalizer/woocommerce_client.py`
**Method:** `upload_image`

**Problem:** Any file path is accepted without verifying it is actually an image.

**Solution:** Validate extension and MIME type at the top of `upload_image`:
```python
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_MIME_PREFIX = "image/"

if image_path.suffix.lower() not in ALLOWED_EXTENSIONS:
    logger.error("upload_image: rejected file with extension %s", image_path.suffix)
    return None

mime_type, _ = mimetypes.guess_type(str(image_path))
if not mime_type or not mime_type.startswith(ALLOWED_MIME_PREFIX):
    logger.error("upload_image: rejected non-image MIME type %s", mime_type)
    return None
```
Remove the fallback to `"application/octet-stream"` — return `None` instead.

---

## Fix 6 — WooCredentials secret exposed in repr/logs (MEDIUM)

**File:** `src/product_gallery_normalizer/woocommerce_models.py`
**Class:** `WooCredentials`

**Problem:** Default Pydantic repr exposes `consumer_secret` in plaintext.

**Solution:** Override `__repr__` and `__str__` to mask the secret:
```python
def __repr__(self) -> str:
    masked = self.consumer_secret[:4] + "****" if self.consumer_secret else ""
    return (
        f"WooCredentials(store_url={self.store_url!r}, "
        f"consumer_key={self.consumer_key!r}, "
        f"consumer_secret={masked!r})"
    )

__str__ = __repr__
```

---

## Fix 7 — QThread.terminate() leaves operations in inconsistent state (LOW)

**File:** `src/product_gallery_normalizer/catalog_panel.py`
**Class:** `_BulkWorker`

**Problem:** `progress_dlg.canceled.connect(self._bulk_worker.terminate)` kills the
thread abruptly, leaving some products updated and others not, with no notification.

**Solution:**
1. Add a cancellation flag to `_BulkWorker`:
   ```python
   def cancel(self) -> None:
       self._cancelled = True
   ```
2. Check the flag inside `run()` at the top of each loop iteration:
   ```python
   for i, product in enumerate(self._products):
       if self._cancelled:
           break
       # ... rest of loop
   ```
3. Add a `cancelled = Signal()` to `_BulkWorker` and emit it when the loop breaks early.
4. In `_run_bulk`, replace:
   ```python
   progress_dlg.canceled.connect(self._bulk_worker.terminate)
   ```
   with:
   ```python
   progress_dlg.canceled.connect(self._bulk_worker.cancel)
   ```

---

## Fix 8 — Raw exception messages shown in UI (LOW)

**Files:** `catalog_panel.py` (`_on_fetch_error`) and
`product_editor_dialog.py` (`_on_categories_error`)

**Problem:** Internal exception strings (paths, IPs, server details) are displayed
directly to the user.

**Solution:** Show a generic user-facing message and log the detail separately.

In `CatalogPanel._on_fetch_error`:
```python
def _on_fetch_error(self, message: str) -> None:
    self._set_controls_enabled(True)
    self._list.clear()
    err_item = QListWidgetItem("Could not load products. Check your connection and credentials.")
    err_item.setFlags(err_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
    self._list.addItem(err_item)
    logger.error("CatalogPanel fetch error: %s", message)
```

In `ProductEditorDialog._on_categories_error`:
```python
def _on_categories_error(self, msg: str) -> None:
    self._cat_list.clear()
    err = QListWidgetItem("Could not load categories.")
    err.setFlags(err.flags() & ~Qt.ItemFlag.ItemIsEnabled)
    self._cat_list.addItem(err)
    logger.error("Categories load error: %s", msg)
```

---

## Fix 9 — No validation of price multiplier (LOW)

**File:** `src/product_gallery_normalizer/batch_operations.py`
**Functions:** `bulk_update_prices`, `bulk_set_sale`

**Problem:** A zero or negative `price_multiplier` / `sale_price_multiplier` would
send invalid prices to WooCommerce without any error.

**Solution:** Add a guard at the top of each function:
```python
# In bulk_update_prices:
if not (0 < price_multiplier <= 10):
    raise ValueError(f"price_multiplier must be between 0 (exclusive) and 10, got {price_multiplier}")

# In bulk_set_sale:
if not clear_sale and not (0 < sale_price_multiplier <= 1):
    raise ValueError(f"sale_price_multiplier must be between 0 (exclusive) and 1, got {sale_price_multiplier}")
```
