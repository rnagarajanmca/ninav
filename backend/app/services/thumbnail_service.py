from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from PIL import Image

logger = logging.getLogger(__name__)

ThumbnailSize = Literal["small", "medium", "large"]

THUMBNAIL_SIZES = {
    "small": (300, 300),
    "medium": (800, 800),
    "large": (1600, 1600),
}


class ThumbnailService:
    """Service for generating and managing image thumbnails."""

    def __init__(self, image_root: Path, thumbnail_root: Path | None = None):
        self.image_root = image_root.resolve()
        self.thumbnail_root = thumbnail_root or (image_root / ".thumbnails")
        self.thumbnail_root.mkdir(parents=True, exist_ok=True)

    def get_thumbnail_path(self, relative_path: str, size: ThumbnailSize = "medium") -> Path:
        """Get the path where thumbnail should be stored."""
        size_dir = self.thumbnail_root / size
        size_dir.mkdir(parents=True, exist_ok=True)
        return size_dir / relative_path

    def generate_thumbnail(
        self,
        source_path: Path,
        relative_path: str,
        size: ThumbnailSize = "medium",
        force: bool = False,
    ) -> Path:
        """
        Generate a thumbnail for an image.

        Args:
            source_path: Absolute path to source image
            relative_path: Relative path from image root
            size: Thumbnail size preset
            force: Regenerate even if thumbnail exists

        Returns:
            Path to generated thumbnail
        """
        thumbnail_path = self.get_thumbnail_path(relative_path, size)

        # Skip if thumbnail exists and is newer than source (unless force=True)
        if not force and thumbnail_path.exists():
            if thumbnail_path.stat().st_mtime >= source_path.stat().st_mtime:
                return thumbnail_path

        try:
            # Create parent directory
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

            # Open and process image
            with Image.open(source_path) as img:
                # Convert RGBA to RGB if needed
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Calculate thumbnail size maintaining aspect ratio
                target_size = THUMBNAIL_SIZES[size]
                img.thumbnail(target_size, Image.Resampling.LANCZOS)

                # Save with optimization
                img.save(
                    thumbnail_path,
                    "JPEG",
                    quality=85,
                    optimize=True,
                    progressive=True,
                )

            logger.debug(f"Generated {size} thumbnail for {relative_path}")
            return thumbnail_path

        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {source_path}: {e}")
            raise

    def generate_all_sizes(self, source_path: Path, relative_path: str) -> dict[ThumbnailSize, Path]:
        """Generate thumbnails in all sizes."""
        thumbnails = {}
        for size in THUMBNAIL_SIZES.keys():
            try:
                thumbnails[size] = self.generate_thumbnail(source_path, relative_path, size)
            except Exception as e:
                logger.warning(f"Failed to generate {size} thumbnail for {relative_path}: {e}")
        return thumbnails

    def delete_thumbnails(self, relative_path: str) -> None:
        """Delete all thumbnails for an image."""
        for size in THUMBNAIL_SIZES.keys():
            thumbnail_path = self.get_thumbnail_path(relative_path, size)
            if thumbnail_path.exists():
                try:
                    thumbnail_path.unlink()
                    logger.debug(f"Deleted {size} thumbnail for {relative_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {size} thumbnail for {relative_path}: {e}")
