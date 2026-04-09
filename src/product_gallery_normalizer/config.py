"""Pydantic models: AppConfig and ImageTransform."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ImageTransform(BaseModel):
    """Per-image transform state — the single source of truth for position, rotation and scale."""

    x: float = Field(default=0.0, description="Horizontal offset in pixels")
    y: float = Field(default=0.0, description="Vertical offset in pixels")
    rotation: float = Field(default=0.0, description="Rotation in degrees")
    scale: float = Field(default=1.0, gt=0.0, description="Scale factor")


class AppConfig(BaseModel):
    """Application-level configuration."""

    canvas_size: int = Field(default=1000, gt=0)
    export_format: Literal["PNG", "WEBP"] = "PNG"
    background_path: Path | None = None
    gallery_path: Path | None = None
    output_path: Path | None = None
