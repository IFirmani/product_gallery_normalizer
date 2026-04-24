"""Pydantic models: AppConfig and ImageTransform, plus load/save helpers."""

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .credential_store import load_credentials, save_credentials
from .woocommerce_models import WooCredentials

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path.home() / ".product_gallery_normalizer" / "config.json"


class ImageTransform(BaseModel):
    """Per-image transform state — the single source of truth for position, rotation and scale."""

    x: float = Field(default=500.0, description="Scene X coordinate of the image centre (px)")
    y: float = Field(default=500.0, description="Scene Y coordinate of the image centre (px)")
    rotation: float = Field(default=0.0, description="Rotation in degrees")
    scale: float = Field(default=1.0, gt=0.0, description="Scale factor")
    edge_feather: int = Field(default=0, ge=0, description="Edge feather radius in pixels (0 = off)")


class AppConfig(BaseModel):
    """Application-level configuration."""

    canvas_size: int = Field(default=1000, gt=0)
    export_format: Literal["PNG", "WEBP"] = "PNG"
    background_path: Path | None = None
    gallery_path: Path | None = None
    output_path: Path | None = None
    woocommerce: WooCredentials = WooCredentials()


def save_config(config: AppConfig) -> None:
    """Persist AppConfig to disk as JSON (credentials stored in OS keyring)."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = config.model_dump(mode="json")
        save_credentials(
            data["woocommerce"].pop("consumer_key", ""),
            data["woocommerce"].pop("consumer_secret", ""),
        )
        _CONFIG_PATH.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
    except OSError as exc:
        logger.error("save_config failed: %s", exc)


def load_config() -> AppConfig:
    """Load AppConfig from disk, injecting credentials from OS keyring."""
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        config = AppConfig.model_validate(data)
    except FileNotFoundError:
        config = AppConfig()
    except Exception as exc:
        logger.error("load_config failed, using defaults: %s", exc)
        config = AppConfig()
    ck, cs = load_credentials()
    config.woocommerce.consumer_key = ck
    config.woocommerce.consumer_secret = cs
    return config
