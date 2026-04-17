"""Pydantic models: AppConfig and ImageTransform."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


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
