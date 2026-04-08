"""Pydantic models: AppConfig and ImageTransform."""

from pathlib import Path

from pydantic import BaseModel, Field


class ImageTransform(BaseModel):
    """Per-image transform state — the single source of truth for position, rotation and scale."""

    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale: float = Field(default=1.0, gt=0)


class AppConfig(BaseModel):
    """Application-level configuration."""

    canvas_size: int = 1000
    background_path: Path | None = None
    gallery_dir: Path | None = None
    output_dir: Path = Path("output")
    export_format: str = "PNG"
