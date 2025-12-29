from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .image import ImageRecord
    from .person import PersonRecord


class FaceRecord(BaseModel, table=True):
    __tablename__ = "faces"

    id: str = Field(primary_key=True)
    image_id: str = Field(foreign_key="images.id", index=True, nullable=False)
    person_id: Optional[str] = Field(default=None, foreign_key="persons.id", index=True)

    bbox_top: float = Field(default=0)
    bbox_left: float = Field(default=0)
    bbox_width: float = Field(default=0)
    bbox_height: float = Field(default=0)
    embedding: bytes = Field(nullable=False)
    embedding_norm: float = Field(nullable=False)
    confidence: float = Field(default=1.0)

    image: "ImageRecord" = Relationship(back_populates="faces")
    person: "PersonRecord" = Relationship(
        back_populates="faces",
        sa_relationship_kwargs={
            "primaryjoin": "FaceRecord.person_id == PersonRecord.id",
            "foreign_keys": "FaceRecord.person_id",
        },
    )
