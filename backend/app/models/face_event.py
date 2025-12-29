from __future__ import annotations

from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field

from .base import BaseModel


class FaceEventRecord(BaseModel, table=True):
    __tablename__ = "face_events"

    id: str = Field(primary_key=True)
    face_id: str = Field(foreign_key="faces.id", index=True, nullable=False)
    event_type: str = Field(index=True, nullable=False)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
