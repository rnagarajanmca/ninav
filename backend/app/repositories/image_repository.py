from __future__ import annotations

from typing import Iterable, Sequence

from sqlmodel import Session, select

from ..models import ImageRecord


class ImageRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> Sequence[ImageRecord]:
        statement = select(ImageRecord)
        return self.session.exec(statement).all()

    def get_by_relative_path(self, relative_path: str) -> ImageRecord | None:
        statement = select(ImageRecord).where(ImageRecord.relative_path == relative_path)
        return self.session.exec(statement).first()

    def add_or_update(self, record: ImageRecord) -> ImageRecord:
        self.session.add(record)
        return record

    def delete(self, record: ImageRecord) -> None:
        self.session.delete(record)

    def bulk_delete_by_relative_paths(self, paths: Iterable[str]) -> int:
        count = 0
        for path in paths:
            record = self.get_by_relative_path(path)
            if record:
                self.session.delete(record)
                count += 1
        return count
