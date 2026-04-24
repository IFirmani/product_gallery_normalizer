"""Pydantic models for WooCommerce REST API v3."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class WooImage(BaseModel):
    id: int = 0
    src: str = ""
    name: str = ""
    alt: str = ""


class WooCategory(BaseModel):
    id: int
    name: str
    slug: str


class WooProduct(BaseModel):
    id: int = 0
    name: str = ""
    slug: str = ""
    status: Literal["publish", "draft", "pending", "private"] = "draft"
    description: str = ""
    short_description: str = ""
    sku: str = ""
    regular_price: str = ""
    sale_price: str = ""
    manage_stock: bool = False
    stock_quantity: int | None = None
    stock_status: Literal["instock", "outofstock", "onbackorder"] = "instock"
    categories: list[WooCategory] = []
    images: list[WooImage] = []
    date_modified: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)

    @property
    def regular_price_float(self) -> float:
        """Return regular_price as float, or 0.0 if empty or non-numeric."""
        try:
            return float(self.regular_price) if self.regular_price else 0.0
        except ValueError:
            return 0.0

    def to_patch_payload(self, fields: list[str]) -> dict:
        """Return a dict with only the requested fields for a PATCH request body."""
        data = self.model_dump(mode="json")
        return {field: data[field] for field in fields if field in data}


class WooCredentials(BaseModel):
    store_url: str = ""
    consumer_key: str = ""
    consumer_secret: str = ""

    def __repr__(self) -> str:
        masked = self.consumer_secret[:4] + "****" if self.consumer_secret else ""
        return (
            f"WooCredentials(store_url={self.store_url!r}, "
            f"consumer_key={self.consumer_key!r}, "
            f"consumer_secret={masked!r})"
        )

    __str__ = __repr__
