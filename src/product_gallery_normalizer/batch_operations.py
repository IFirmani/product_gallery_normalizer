"""Batch operations for WooCommerce products (core module — no PySide6)."""

from __future__ import annotations

from typing import Callable, Literal

from .woocommerce_client import WooCommerceClient


def bulk_update_prices(
    client: WooCommerceClient,
    product_ids: list[int],
    price_multiplier: float,
    apply_to_sale_price: bool = False,
    round_to: int = 0,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[int, bool]:
    """Multiply regular_price (and optionally sale_price) for each product."""
    if not (0 < price_multiplier <= 10):
        raise ValueError(
            f"price_multiplier must be between 0 (exclusive) and 10, got {price_multiplier}"
        )
    total = len(product_ids)
    results: dict[int, bool] = {}
    for i, product_id in enumerate(product_ids, start=1):
        product = client.get_product(product_id)
        if product is None:
            results[product_id] = False
            if progress_callback is not None:
                progress_callback(i, total)
            continue
        new_price = round(product.regular_price_float * price_multiplier, round_to)
        patch: dict = {"regular_price": str(int(new_price) if round_to == 0 else new_price)}
        if apply_to_sale_price and product.sale_price:
            try:
                new_sale = round(float(product.sale_price) * price_multiplier, round_to)
                patch["sale_price"] = str(int(new_sale) if round_to == 0 else new_sale)
            except ValueError:
                pass
        updated = client.update_product(product_id, patch)
        results[product_id] = updated is not None
        if progress_callback is not None:
            progress_callback(i, total)
    return results


def bulk_set_status(
    client: WooCommerceClient,
    product_ids: list[int],
    status: Literal["publish", "draft"],
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[int, bool]:
    """Set the status for each product."""
    total = len(product_ids)
    results: dict[int, bool] = {}
    for i, product_id in enumerate(product_ids, start=1):
        updated = client.update_product(product_id, {"status": status})
        results[product_id] = updated is not None
        if progress_callback is not None:
            progress_callback(i, total)
    return results


def bulk_set_sale(
    client: WooCommerceClient,
    product_ids: list[int],
    sale_price_multiplier: float = 0.8,
    clear_sale: bool = False,
    round_to: int = 0,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[int, bool]:
    """Apply or clear a sale price for each product."""
    if not clear_sale and not (0 < sale_price_multiplier <= 1):
        raise ValueError(
            f"sale_price_multiplier must be between 0 (exclusive) and 1, got {sale_price_multiplier}"
        )
    total = len(product_ids)
    results: dict[int, bool] = {}
    for i, product_id in enumerate(product_ids, start=1):
        if clear_sale:
            patch: dict = {"sale_price": ""}
            updated = client.update_product(product_id, patch)
        else:
            product = client.get_product(product_id)
            if product is None:
                results[product_id] = False
                if progress_callback is not None:
                    progress_callback(i, total)
                continue
            new_sale = round(product.regular_price_float * sale_price_multiplier, round_to)
            patch = {"sale_price": str(int(new_sale) if round_to == 0 else new_sale)}
            updated = client.update_product(product_id, patch)
        results[product_id] = updated is not None
        if progress_callback is not None:
            progress_callback(i, total)
    return results
