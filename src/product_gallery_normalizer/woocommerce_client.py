"""WooCommerce REST API v3 HTTP client."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

from .woocommerce_models import WooCategory, WooCredentials, WooImage, WooProduct

logger = logging.getLogger(__name__)


class WooCommerceClient:
    """HTTP client for the WooCommerce REST API v3."""

    _TIMEOUT = 15

    def __init__(self, credentials: WooCredentials) -> None:
        self._base_url = f"{credentials.store_url.rstrip('/')}/wp-json/wc/v3"
        self._store_url = credentials.store_url.rstrip("/")
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(
            credentials.consumer_key, credentials.consumer_secret
        )

    def get_products(
        self,
        page: int = 1,
        per_page: int = 50,
        search: str = "",
        status: str = "any",
        category: int | None = None,
    ) -> list[WooProduct]:
        """Fetch a page of products from the WooCommerce API."""
        params: dict = {"page": page, "per_page": per_page, "status": status}
        if search:
            params["search"] = search
        if category is not None:
            params["category"] = category
        try:
            response = self._session.get(
                f"{self._base_url}/products", params=params, timeout=self._TIMEOUT
            )
            response.raise_for_status()
            return [WooProduct.model_validate(item) for item in response.json()]
        except requests.HTTPError as exc:
            logger.error("get_products HTTP error: %s", exc)
            return []
        except Exception as exc:
            logger.error("get_products error: %s", exc)
            return []

    def get_product(self, product_id: int) -> WooProduct | None:
        """Fetch a single product by ID."""
        try:
            response = self._session.get(
                f"{self._base_url}/products/{product_id}", timeout=self._TIMEOUT
            )
            response.raise_for_status()
            return WooProduct.model_validate(response.json())
        except Exception as exc:
            logger.error("get_product(%s) error: %s", product_id, exc)
            return None

    def update_product(self, product_id: int, payload: dict) -> WooProduct | None:
        """Update a product via PUT and return the updated model."""
        try:
            response = self._session.put(
                f"{self._base_url}/products/{product_id}",
                json=payload,
                timeout=self._TIMEOUT,
            )
            response.raise_for_status()
            return WooProduct.model_validate(response.json())
        except Exception as exc:
            logger.error("update_product(%s) error: %s", product_id, exc)
            return None

    def create_product(self, product: WooProduct) -> WooProduct | None:
        """Create a new product and return the server-assigned model."""
        payload = product.model_dump(
            mode="json", exclude={"id", "date_modified"}, exclude_none=True
        )
        try:
            response = self._session.post(
                f"{self._base_url}/products", json=payload, timeout=self._TIMEOUT
            )
            response.raise_for_status()
            return WooProduct.model_validate(response.json())
        except Exception as exc:
            logger.error("create_product error: %s", exc)
            return None

    def delete_product(self, product_id: int, force: bool = False) -> bool:
        """Delete a product. Returns True on success."""
        try:
            response = self._session.delete(
                f"{self._base_url}/products/{product_id}",
                params={"force": force},
                timeout=self._TIMEOUT,
            )
            response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("delete_product(%s) error: %s", product_id, exc)
            return False

    _ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    _ALLOWED_MIME_PREFIX = "image/"

    def upload_image(self, image_path: Path) -> WooImage | None:
        """Upload an image to the WordPress Media Library."""
        if image_path.suffix.lower() not in self._ALLOWED_EXTENSIONS:
            logger.error("upload_image: rejected file with extension %s", image_path.suffix)
            return None
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type or not mime_type.startswith(self._ALLOWED_MIME_PREFIX):
            logger.error("upload_image: rejected non-image MIME type %s", mime_type)
            return None
        safe_name = (
            image_path.name
            .replace('"', "")
            .replace("\r", "")
            .replace("\n", "")
        )
        try:
            with image_path.open("rb") as fh:
                response = self._session.post(
                    f"{self._store_url}/wp-json/wp/v2/media",
                    headers={
                        "Content-Disposition": f'attachment; filename="{safe_name}"',
                        "Content-Type": mime_type,
                    },
                    data=fh,
                    timeout=self._TIMEOUT,
                )
            response.raise_for_status()
            data = response.json()
            return WooImage(
                id=data.get("id", 0),
                src=data.get("source_url", ""),
                name=data.get("slug", image_path.stem),
                alt=data.get("alt_text", ""),
            )
        except Exception as exc:
            logger.error("upload_image(%s) error: %s", image_path, exc)
            return None

    def get_categories(self) -> list[WooCategory]:
        """Fetch all product categories."""
        try:
            response = self._session.get(
                f"{self._base_url}/products/categories",
                params={"per_page": 100},
                timeout=self._TIMEOUT,
            )
            response.raise_for_status()
            return [WooCategory.model_validate(item) for item in response.json()]
        except Exception as exc:
            logger.error("get_categories error: %s", exc)
            return []

    def create_category(self, name: str, parent_id: int = 0) -> WooCategory | None:
        """Create a new product category."""
        payload: dict = {"name": name}
        if parent_id:
            payload["parent"] = parent_id
        try:
            response = self._session.post(
                f"{self._base_url}/products/categories",
                json=payload,
                timeout=self._TIMEOUT,
            )
            response.raise_for_status()
            return WooCategory.model_validate(response.json())
        except Exception as exc:
            logger.error("create_category(%r) error: %s", name, exc)
            return None

    def update_category(self, category_id: int, payload: dict) -> WooCategory | None:
        """Update a product category."""
        try:
            response = self._session.put(
                f"{self._base_url}/products/categories/{category_id}",
                json=payload,
                timeout=self._TIMEOUT,
            )
            response.raise_for_status()
            return WooCategory.model_validate(response.json())
        except Exception as exc:
            logger.error("update_category(%s) error: %s", category_id, exc)
            return None

    def delete_category(self, category_id: int, force: bool = True) -> bool:
        """Delete a product category. Returns True on success."""
        try:
            response = self._session.delete(
                f"{self._base_url}/products/categories/{category_id}",
                params={"force": force},
                timeout=self._TIMEOUT,
            )
            response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("delete_category(%s) error: %s", category_id, exc)
            return False
