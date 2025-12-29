from __future__ import annotations

import logging
import errno
import shutil
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Iterable, List

from ..core.config import Settings
from ..schemas import ImageDeleteResponse, ImageMetadata

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImageQuery:
    page: int = 1
    page_size: int = 60

    def slice_bounds(self) -> tuple[int, int]:
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return start, end


class ImageService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._root = settings.image_root.resolve()
        self._allowed_suffixes = tuple(f".{ext}" for ext in settings.allowed_extensions)

    @property
    def root(self) -> Path:
        return self._root

    def list_images(self, query: ImageQuery) -> tuple[List[ImageMetadata], int]:
        files = list(self._iter_image_files())
        total = len(files)
        start, end = query.slice_bounds()
        selected = files[start:end]
        images: List[ImageMetadata] = []
        for path in selected:
            try:
                images.append(
                    ImageMetadata.from_path(
                        root=self.root,
                        path=path,
                        url_prefix="/media",
                        identifier=self._build_identifier(path),
                    )
                )
            except (FileNotFoundError, PermissionError, OSError) as exc:
                logger.warning("Skipping unreadable image %s: %s", path, exc)
        return images, total

    def _iter_image_files(self) -> Iterable[Path]:
        for path in sorted(self.root.rglob("*")):
            suffix = path.suffix.lower()
            if suffix not in self._allowed_suffixes:
                continue
            # Skip hidden/system directories
            if ".trash" in path.parts or ".thumbnails" in path.parts:
                continue
            try:
                if path.is_file():
                    yield path
            except (FileNotFoundError, PermissionError, OSError) as exc:
                logger.warning("Skipping path %s due to access error: %s", path, exc)

    def rename_image(self, relative_path: str, new_name: str) -> ImageMetadata:
        source = self._resolve_relative_path(relative_path)
        self._ensure_file_exists(source)
        sanitized = self._validate_filename(new_name)
        target = source.with_name(sanitized)
        if target.suffix.lower() == "":
            target = target.with_suffix(source.suffix)
        if target.suffix.lower() not in self._allowed_suffixes:
            raise ValueError("File extension not allowed")
        if target == source:
            return ImageMetadata.from_path(
                root=self.root,
                path=source,
                url_prefix="/media",
                identifier=self._build_identifier(source),
            )
        if target.exists():
            raise FileExistsError(f"Target file '{target.name}' already exists")
        self._safe_move(source, target)
        return ImageMetadata.from_path(
            root=self.root,
            path=target,
            url_prefix="/media",
            identifier=self._build_identifier(target),
        )

    def delete_image(self, relative_path: str) -> ImageDeleteResponse:
        source = self._resolve_relative_path(relative_path)
        self._ensure_file_exists(source)
        trash_root = self._ensure_trash_directory()
        relative_target = Path(relative_path)
        target = trash_root / relative_target
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = target.with_name(f"{target.stem}-{timestamp}{target.suffix or source.suffix}")
        target.parent.mkdir(parents=True, exist_ok=True)
        self._safe_move(source, target)
        trashed_relative = target.relative_to(self.root).as_posix()
        return ImageDeleteResponse(original_path=relative_path, trashed_path=trashed_relative)

    def _ensure_file_exists(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Image '{path.name}' was not found")
        if not path.is_file():
            raise ValueError("Only files can be managed")

    def _resolve_relative_path(self, relative_path: str) -> Path:
        candidate = (self.root / Path(relative_path)).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("Path escapes the image root")
        return candidate

    def _ensure_trash_directory(self) -> Path:
        trash = self.root / ".trash"
        trash.mkdir(parents=True, exist_ok=True)
        return trash

    def _safe_move(self, source: Path, target: Path) -> None:
        try:
            source.rename(target)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                source.unlink()
            else:
                logger.exception("Safe move failed for %s -> %s", source, target)
                raise

    @staticmethod
    def _validate_filename(name: str) -> str:
        """Validate and sanitize filename to prevent security issues."""
        sanitized = Path(name).name.strip()

        if not sanitized:
            raise ValueError("Filename must not be empty")

        dangerous_chars = ["/", "\\", "\0", "\n", "\r", "\t"]
        if any(char in sanitized for char in dangerous_chars):
            raise ValueError(f"Filename contains invalid characters")

        if ".." in sanitized:
            raise ValueError("Filename cannot contain '..'")

        reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                         "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
                         "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]
        name_without_ext = Path(sanitized).stem.upper()
        if name_without_ext in reserved_names:
            raise ValueError(f"Filename is reserved and cannot be used")

        if len(sanitized) > 255:
            raise ValueError("Filename too long (max 255 characters)")

        if sanitized.startswith("."):
            raise ValueError("Filename cannot start with '.'")

        return sanitized

    @staticmethod
    def _build_identifier(path: Path) -> str:
        return sha1(path.as_posix().encode("utf-8")).hexdigest()
