"""Tests for batch_operations module."""

from unittest.mock import MagicMock, call

import pytest

from product_gallery_normalizer.batch_operations import (
    bulk_set_sale,
    bulk_set_status,
    bulk_update_prices,
)
from product_gallery_normalizer.woocommerce_models import WooProduct


def _make_product(product_id: int, regular_price: str, sale_price: str = "") -> WooProduct:
    return WooProduct(id=product_id, regular_price=regular_price, sale_price=sale_price)


def test_bulk_update_prices_calls_update_for_each_id() -> None:
    client = MagicMock()
    products = [
        _make_product(1, "100.00"),
        _make_product(2, "200.00"),
        _make_product(3, "300.00"),
    ]
    client.get_product.side_effect = products
    client.update_product.return_value = products[0]

    result = bulk_update_prices(client, [1, 2, 3], price_multiplier=0.9, round_to=0)

    assert client.update_product.call_count == 3
    calls = client.update_product.call_args_list
    assert calls[0] == call(1, {"regular_price": "90"})
    assert calls[1] == call(2, {"regular_price": "180"})
    assert calls[2] == call(3, {"regular_price": "270"})
    assert result == {1: True, 2: True, 3: True}


def test_bulk_update_prices_rounding() -> None:
    client = MagicMock()
    client.get_product.return_value = _make_product(1, "1000.00")
    client.update_product.return_value = _make_product(1, "990")

    result = bulk_update_prices(client, [1], price_multiplier=0.99, round_to=0)

    client.update_product.assert_called_once_with(1, {"regular_price": "990"})
    assert result[1] is True


def test_bulk_set_sale_clear() -> None:
    client = MagicMock()
    client.update_product.return_value = _make_product(1, "100.00")

    result = bulk_set_sale(client, [1, 2], clear_sale=True)

    assert client.get_product.call_count == 0
    assert client.update_product.call_count == 2
    for c in client.update_product.call_args_list:
        assert c.args[1] == {"sale_price": ""}
    assert result == {1: True, 2: True}


def test_bulk_set_sale_applies_multiplier() -> None:
    client = MagicMock()
    client.get_product.return_value = _make_product(1, "1000.00")
    client.update_product.return_value = _make_product(1, "1000.00", "800")

    result = bulk_set_sale(client, [1], sale_price_multiplier=0.8, round_to=0)

    client.update_product.assert_called_once_with(1, {"sale_price": "800"})
    assert result[1] is True


def test_progress_callback_called_with_correct_args() -> None:
    client = MagicMock()
    client.update_product.return_value = _make_product(1, "100.00")

    received: list[tuple[int, int]] = []

    def callback(current: int, total: int) -> None:
        received.append((current, total))

    bulk_set_status(client, [1, 2, 3], status="publish", progress_callback=callback)

    assert received == [(1, 3), (2, 3), (3, 3)]


def test_bulk_update_prices_continues_after_failed_product() -> None:
    client = MagicMock()
    p1 = _make_product(1, "100.00")
    p3 = _make_product(3, "300.00")
    client.get_product.side_effect = [p1, None, p3]
    client.update_product.return_value = p1

    result = bulk_update_prices(client, [1, 2, 3], price_multiplier=1.0, round_to=0)

    assert result[1] is True
    assert result[2] is False
    assert result[3] is True
    assert client.update_product.call_count == 2
