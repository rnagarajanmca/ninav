from datetime import datetime
from pathlib import Path
from typing import List, Self

from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    id: str
    name: str
    relative_path: str
    url: str
    size_bytes: int
    modified_at: datetime

    @classmethod
    def from_path(cls, *, root: Path, path: Path, url_prefix: str, identifier: str) -> Self:
        stat = path.stat()
        relative_path = path.relative_to(root).as_posix()
        return cls(
            id=identifier,
            name=path.name,
            relative_path=relative_path,
            url=f"{url_prefix}/{relative_path}",
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        )


class ImageListResponse(BaseModel):
    items: List[ImageMetadata]
    page: int
    page_size: int
    total: int


class ImageRenameRequest(BaseModel):
    relative_path: str = Field(..., description="Original relative path of the image within the library")
    new_name: str = Field(..., description="Desired file name (optionally including extension)")


class ImageDeleteRequest(BaseModel):
    relative_path: str = Field(..., description="Relative path of the image to move to trash")


class ImageDeleteResponse(BaseModel):
    original_path: str
    trashed_path: str
