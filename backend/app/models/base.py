from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    """Declarative base with timestamp helpers."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False, index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)
