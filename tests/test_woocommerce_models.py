"""Tests for WooCommerce Pydantic models."""

import pytest

from product_gallery_normalizer.woocommerce_models import (
    WooCategory,
    WooImage,
    WooProduct,
)

_API_RESPONSE = {
    "id": 123,
    "name": "Electric Guitar",
    "slug": "electric-guitar",
    "status": "publish",
    "description": "<p>A fine instrument.</p>",
    "short_description": "<p>Great guitar.</p>",
    "sku": "EG-001",
    "regular_price": "1299.99",
    "sale_price": "999.00",
    "manage_stock": True,
    "stock_quantity": 5,
    "stock_status": "instock",
    "date_modified": "2024-01-15T10:30:00",
    "categories": [
        {"id": 10, "name": "Guitars", "slug": "guitars"},
        {"id": 20, "name": "Electric", "slug": "electric"},
    ],
    "images": [
        {"id": 1, "src": "https://example.com/guitar.jpg", "name": "guitar", "alt": "Electric Guitar"},
        {"id": 2, "src": "https://example.com/guitar2.jpg", "name": "guitar-side", "alt": ""},
    ],
}


def test_model_validate_from_api_response() -> None:
    product = WooProduct.model_validate(_API_RESPONSE)
    assert product.id == 123
    assert product.name == "Electric Guitar"
    assert product.sku == "EG-001"
    assert product.status == "publish"
    assert product.regular_price == "1299.99"
    assert product.sale_price == "999.00"
    assert product.manage_stock is True
    assert product.stock_quantity == 5
    assert product.stock_status == "instock"
    assert len(product.categories) == 2
    assert isinstance(product.categories[0], WooCategory)
    assert product.categories[0].id == 10
    assert product.categories[0].name == "Guitars"
    assert len(product.images) == 2
    assert isinstance(product.images[0], WooImage)
    assert product.images[0].src == "https://example.com/guitar.jpg"
    assert product.date_modified is not None


def test_to_patch_payload_returns_only_requested_fields() -> None:
    product = WooProduct(name="Bass", regular_price="500.00", sku="B-001")
    payload = product.to_patch_payload(["name", "regular_price"])
    assert set(payload.keys()) == {"name", "regular_price"}
    assert payload["name"] == "Bass"
    assert payload["regular_price"] == "500.00"


def test_to_patch_payload_empty_list_returns_empty_dict() -> None:
    product = WooProduct(name="Bass", regular_price="500.00")
    assert product.to_patch_payload([]) == {}


def test_regular_price_float_valid() -> None:
    assert WooProduct(regular_price="1299.99").regular_price_float == 1299.99


def test_regular_price_float_empty() -> None:
    assert WooProduct().regular_price_float == 0.0


def test_regular_price_float_invalid_string() -> None:
    assert WooProduct(regular_price="N/A").regular_price_float == 0.0


def test_partial_response_does_not_raise() -> None:
    product = WooProduct.model_validate({"id": 42, "name": "Guitar"})
    assert product.id == 42
    assert product.name == "Guitar"
    assert product.regular_price == ""
    assert product.categories == []
    assert product.images == []
