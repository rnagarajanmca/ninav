from __future__ import annotations

from typing import Iterable, Sequence

from sqlmodel import Session, select

from ..models import FaceRecord


class FaceRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_unassigned(self, limit: int = 100, offset: int = 0) -> Sequence[FaceRecord]:
        statement = (
            select(FaceRecord)
            .where(FaceRecord.person_id.is_(None))
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    def bulk_insert(self, faces: Iterable[FaceRecord]) -> None:
        for face in faces:
            self.session.add(face)

    def delete_for_image(self, image_id: str) -> int:
        statement = select(FaceRecord).where(FaceRecord.image_id == image_id)
        records = self.session.exec(statement).all()
        for record in records:
            self.session.delete(record)
        return len(records)

    def assign_faces(self, face_ids: Iterable[str], person_id: str) -> None:
        statement = select(FaceRecord).where(FaceRecord.id.in_(list(face_ids)))
        for record in self.session.exec(statement).all():
            record.person_id = person_id
            record.touch()
