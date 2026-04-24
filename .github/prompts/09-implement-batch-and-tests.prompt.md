---
mode: agent
description: Implement batch catalog operations and tests for the WooCommerce modules
---

# Implement batch_operations.py and tests

## Part 1: batch_operations.py (core module)

Create `src/product_gallery_normalizer/batch_operations.py`.
This is a **core module** — no PySide6 imports allowed.

### Function: bulk_update_prices
```python
def bulk_update_prices(
    client: WooCommerceClient,
    product_ids: list[int],
    price_multiplier: float,            # e.g. 0.9 for −10%
    apply_to_sale_price: bool = False,
    round_to: int = 0,                  # decimal places for rounding
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[int, bool]                    # {product_id: success}
```
- For each id: fetch the product, multiply `regular_price_float` by `price_multiplier`,
  round to `round_to` decimals, build a patch with `regular_price` as string
- If `apply_to_sale_price` and the product has a non-empty `sale_price`, apply the
  multiplier to `sale_price` as well
- Call `progress_callback(current_index, total)` after processing each product
- Return a dict mapping each product_id to True (success) or False (error)

### Function: bulk_set_status
```python
def bulk_set_status(
    client: WooCommerceClient,
    product_ids: list[int],
    status: Literal["publish", "draft"],
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[int, bool]
```
- PATCH each product with `{"status": status}`

### Function: bulk_set_sale
```python
def bulk_set_sale(
    client: WooCommerceClient,
    product_ids: list[int],
    sale_price_multiplier: float = 0.8,  # applied to regular_price
    clear_sale: bool = False,            # if True, send sale_price=""
    round_to: int = 0,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[int, bool]
```
- If `clear_sale` is True: PATCH each product with `{"sale_price": ""}`
- Otherwise: fetch each product, compute `round(regular_price_float * sale_price_multiplier, round_to)`,
  PATCH with the result as string

## Part 2: tests/test_woocommerce_models.py

Create `tests/test_woocommerce_models.py`. Follow the existing test style in the project.

### Tests to implement
- `test_model_validate_from_api_response`: call `WooProduct.model_validate` with a
  hardcoded realistic WC API response dict (include nested images and categories);
  assert key fields parse correctly
- `test_to_patch_payload_returns_only_requested_fields`: create a WooProduct, call
  `to_patch_payload(["name", "regular_price"])`, assert the dict has exactly those two keys
- `test_to_patch_payload_empty_list_returns_empty_dict`
- `test_regular_price_float_valid`: `WooProduct(regular_price="1299.99").regular_price_float == 1299.99`
- `test_regular_price_float_empty`: `WooProduct().regular_price_float == 0.0`
- `test_regular_price_float_invalid_string`: `WooProduct(regular_price="N/A").regular_price_float == 0.0`
- `test_partial_response_does_not_raise`: validate a dict with only `{"id": 42, "name": "Guitar"}`

## Part 3: tests/test_batch_operations.py

Create `tests/test_batch_operations.py`. Use `unittest.mock.MagicMock` for the client.

### Tests to implement
- `test_bulk_update_prices_calls_update_for_each_id`: mock `client.get_product` to
  return products, mock `client.update_product`; assert it's called once per id with
  the correctly rounded price
- `test_bulk_update_prices_rounding`: multiplier=0.99, round_to=0, price="1000.00" → "990"
- `test_bulk_set_sale_clear`: `clear_sale=True` must send `{"sale_price": ""}` regardless
  of the current sale price
- `test_bulk_set_sale_applies_multiplier`: multiplier=0.8, regular_price="1000.00",
  round_to=0 → sale_price patch = "800"
- `test_progress_callback_called_with_correct_args`: verify `progress_callback` receives
  `(1, 3)`, `(2, 3)`, `(3, 3)` for a list of 3 products
- `test_bulk_update_prices_continues_after_failed_product`: if `get_product` returns None
  for one id, the result dict maps that id to False and processing continues for remaining ids
