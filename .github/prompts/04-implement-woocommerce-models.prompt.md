---
mode: agent
description: Implement Pydantic models for WooCommerce REST API v3
---

# Implement woocommerce_models.py

Create `src/product_gallery_normalizer/woocommerce_models.py`.
This is a **core module** — no PySide6 imports allowed.

## Models to implement

### WooImage
```python
class WooImage(BaseModel):
    id: int = 0
    src: str = ""
    name: str = ""
    alt: str = ""
```

### WooCategory
```python
class WooCategory(BaseModel):
    id: int
    name: str
    slug: str
```

### WooProduct
```python
class WooProduct(BaseModel):
    id: int = 0
    name: str = ""
    slug: str = ""
    status: Literal["publish", "draft", "pending", "private"] = "draft"
    description: str = ""
    short_description: str = ""
    sku: str = ""
    regular_price: str = ""       # WC sends prices as strings
    sale_price: str = ""
    manage_stock: bool = False
    stock_quantity: int | None = None
    stock_status: Literal["instock", "outofstock", "onbackorder"] = "instock"
    categories: list[WooCategory] = []
    images: list[WooImage] = []
    date_modified: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)
```

### WooCredentials
```python
class WooCredentials(BaseModel):
    store_url: str = ""          # e.g. "https://mystore.com"
    consumer_key: str = ""       # ck_...
    consumer_secret: str = ""    # cs_...
```

## Rules
- Use `pydantic.BaseModel` with `model_config = ConfigDict(populate_by_name=True)`
- All fields must have defaults so partial API responses don't raise
- `WooProduct.regular_price` and `sale_price` are `str` (not float) — WC API returns
  them as strings and expects strings on write
- Add a convenience property `WooProduct.regular_price_float -> float` that returns
  `float(regular_price) if regular_price else 0.0`
- Add a method `WooProduct.to_patch_payload(fields: list[str]) -> dict` that returns
  only the requested field names as a dict suitable for a PATCH request body
- No imports from PySide6 or any GUI module
