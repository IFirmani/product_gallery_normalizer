---
mode: agent
description: Implement the WooCommerce REST API v3 HTTP client
---

# Implement woocommerce_client.py

Create `src/product_gallery_normalizer/woocommerce_client.py`.
This is a **core module** — no PySide6 imports allowed.

## Class: WooCommerceClient

Constructor: `__init__(self, credentials: WooCredentials)`
- Build a `requests.Session` with HTTP Basic Auth (consumer_key, consumer_secret)
- Set default timeout to 15 seconds
- Base URL: `{credentials.store_url}/wp-json/wc/v3`

## Methods

### get_products
```python
def get_products(
    self,
    page: int = 1,
    per_page: int = 50,
    search: str = "",
    status: str = "any",
    category: int | None = None,
) -> list[WooProduct]
```
- GET `/products` with query params
- Parse response JSON into `list[WooProduct]` using `WooProduct.model_validate`
- Return empty list on HTTP error, log the error with `logging.error`

### get_product
```python
def get_product(self, product_id: int) -> WooProduct | None
```
- GET `/products/{product_id}`
- Return None on 404 or any error

### update_product
```python
def update_product(self, product_id: int, payload: dict) -> WooProduct | None
```
- PUT `/products/{product_id}` with JSON body
- Return updated WooProduct or None on error

### create_product
```python
def create_product(self, product: WooProduct) -> WooProduct | None
```
- POST `/products` with `product.model_dump(exclude={"id", "date_modified"}, exclude_none=True)`
- Return created WooProduct (with server-assigned id) or None on error

### delete_product
```python
def delete_product(self, product_id: int, force: bool = False) -> bool
```
- DELETE `/products/{product_id}?force={force}`
- Returns True on 200/success, False otherwise

### upload_image
```python
def upload_image(self, image_path: Path) -> WooImage | None
```
- POST to `{store_url}/wp-json/wp/v2/media` (WordPress Media API, not WC)
- Send file as multipart with correct `Content-Disposition` and `Content-Type` headers
- Infer MIME type from file extension using `mimetypes.guess_type`
- Return WooImage with the new `id` and `src`, or None on error

### get_categories
```python
def get_categories(self) -> list[WooCategory]
```
- GET `/products/categories?per_page=100`
- Return list of WooCategory or empty list on error

## Rules
- Add `requests` to `[project.dependencies]` in `pyproject.toml` if not already present
- Log all HTTP errors with `logging.error`, never raise to caller
- No threading in this module — threading is the GUI's responsibility
- No imports from PySide6 or any GUI module
