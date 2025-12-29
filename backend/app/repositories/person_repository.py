from __future__ import annotations

from typing import Iterable, Sequence

from sqlmodel import Session, select

from ..models import FaceRecord, PersonRecord


class PersonRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> Sequence[PersonRecord]:
        return self.session.exec(select(PersonRecord)).all()

    def get(self, person_id: str) -> PersonRecord | None:
        statement = select(PersonRecord).where(PersonRecord.id == person_id)
        return self.session.exec(statement).first()

    def create(self, person: PersonRecord) -> PersonRecord:
        self.session.add(person)
        return person

    def delete(self, person: PersonRecord) -> None:
        self.session.delete(person)

    def update_cover_face(self, person: PersonRecord, face_id: str | None) -> None:
        person.cover_face_id = face_id
        person.touch()

    def rename(self, person: PersonRecord, label: str) -> PersonRecord:
        person.label = label
        person.touch()
        return person

    def detach_faces(self, person_id: str, face_ids: Iterable[str]) -> None:
        statement = (
            select(FaceRecord)
            .where(FaceRecord.person_id == person_id)
            .where(FaceRecord.id.in_(list(face_ids)))
        )
        for record in self.session.exec(statement).all():
            record.person_id = None
            record.touch()
