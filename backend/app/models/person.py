from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field, Relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .face import FaceRecord


class PersonRecord(BaseModel, table=True):
    __tablename__ = "persons"

    id: str = Field(primary_key=True)
    label: str = Field(default="Unnamed person", nullable=False)
    cover_face_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            "cover_face_id",
            String,
            ForeignKey("faces.id", use_alter=True),
            nullable=True,
        ),
    )

    faces: List["FaceRecord"] = Relationship(
        back_populates="person",
        sa_relationship_kwargs={
            "primaryjoin": "FaceRecord.person_id == PersonRecord.id",
            "foreign_keys": "FaceRecord.person_id",
        },
    )
