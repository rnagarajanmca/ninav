from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.db import get_session_dependency  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import FaceRecord, ImageRecord, PersonRecord  # noqa: E402


@pytest.fixture()
def test_engine():
    from app import models  # noqa: F401  # ensure mappers registered

    engine = create_engine("sqlite:///test.db", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    try:
        yield engine
    finally:
        SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def session(test_engine) -> Iterator[Session]:
    with Session(test_engine) as session:
        yield session


@pytest.fixture()
def client(test_engine):
    application = create_app()

    def override_session():
        with Session(test_engine) as session:
            yield session

    application.dependency_overrides[get_session_dependency] = override_session

    with TestClient(application) as test_client:
        yield test_client

    application.dependency_overrides.clear()


def create_sample_image(session: Session, *, relative_path: str = "sample.png") -> ImageRecord:
    image = ImageRecord(
        id=str(uuid4()),
        relative_path=relative_path,
        checksum="checksum",
        size_bytes=123,
        modified_at=datetime.now(UTC),
        last_scanned=datetime.now(UTC),
    )
    session.add(image)
    session.commit()
    return image


def create_sample_face(session: Session, *, image: ImageRecord) -> FaceRecord:
    face = FaceRecord(
        id=str(uuid4()),
        image_id=image.id,
        bbox_top=10,
        bbox_left=5,
        bbox_width=40,
        bbox_height=50,
        embedding=b"\x00" * 512,
        embedding_norm=1.0,
        confidence=0.9,
    )
    session.add(face)
    session.commit()
    return face


def test_list_faces_returns_items(client: TestClient, session: Session):
    image = create_sample_image(session)
    face = create_sample_face(session, image=image)

    response = client.get("/api/faces")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == face.id
    assert data["items"][0]["relative_path"] == image.relative_path


def test_create_person_and_assign_faces(client: TestClient, session: Session):
    image = create_sample_image(session)
    face = create_sample_face(session, image=image)

    resp = client.post("/api/persons", json={"label": "Family"})
    assert resp.status_code == 201
    person_payload = resp.json()
    person_id = person_payload["id"]
    assert person_payload["cover_face_id"] is None

    assign_resp = client.post(
        f"/api/persons/{person_id}/assign",
        json={"face_ids": [face.id]},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["count"] == 1

    session.refresh(face)
    assert face.person_id == person_id

    person = session.get(PersonRecord, person_id)
    assert person is not None
    assert person.cover_face_id == face.id

    persons_resp = client.get("/api/persons")
    assert persons_resp.status_code == 200
    people = persons_resp.json()
    assert people["total"] == 1
    assert people["items"][0]["cover_face_id"] == face.id
