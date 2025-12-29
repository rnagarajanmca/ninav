from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .face import FaceRecord


class ImageRecord(BaseModel, table=True):
    __tablename__ = "images"

    id: str = Field(primary_key=True)
    relative_path: str = Field(index=True, unique=True, nullable=False)
    checksum: str = Field(index=True, nullable=False)
    size_bytes: int = Field(default=0, nullable=False)
    modified_at: datetime = Field(nullable=False, index=True)
    first_seen: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_scanned: Optional[datetime] = Field(default=None, nullable=True)

    faces: list["FaceRecord"] = Relationship(
        back_populates="image",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
