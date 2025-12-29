from __future__ import annotations

from typing import Dict, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlmodel import Session

from ..db import get_session_dependency
from ..models import FaceRecord, ImageRecord, PersonRecord
from ..repositories import FaceRepository, PersonRepository
from ..schemas import (
    AssignFacesRequest,
    BoundingBox,
    CreatePersonRequest,
    FaceClusterItem,
    FaceClusterResponse,
    FaceItem,
    FaceListResponse,
    FaceStatus,
    PersonItem,
    PersonListResponse,
    UpdatePersonRequest,
)
from ..services.face_clustering import FaceClusteringService

router = APIRouter(tags=["faces"])


@router.get("/faces/clusters", response_model=FaceClusterResponse)
def cluster_faces(
    threshold: float = Query(0.6, ge=0.0, le=1.0, description="Similarity threshold (0-1)"),
    min_cluster_size: int = Query(1, ge=1, description="Minimum faces per cluster"),
    unassigned_only: bool = Query(True, description="Only cluster unassigned faces"),
    session: Session = Depends(get_session_dependency),
) -> FaceClusterResponse:
    """
    Cluster similar faces using facial embeddings.

    Args:
        threshold: Cosine similarity threshold (higher = stricter matching)
        min_cluster_size: Minimum number of faces to form a cluster
        unassigned_only: Only cluster faces that haven't been assigned to a person
    """
    # Fetch faces to cluster
    face_query = select(FaceRecord)

    if unassigned_only:
        face_query = face_query.where(FaceRecord.person_id.is_(None))

    # Use scalars() to get FaceRecord objects instead of Row objects
    face_records = list(session.exec(face_query).scalars().all())

    if not face_records:
        return FaceClusterResponse(total_clusters=0, clusters=[])

    # Perform clustering
    clustering_service = FaceClusteringService(similarity_threshold=threshold)
    raw_clusters = clustering_service.cluster_faces(face_records)

    # Filter by minimum cluster size
    filtered_clusters = [c for c in raw_clusters if len(c.face_ids) >= min_cluster_size]

    # Build face lookup map
    face_map = {face.id: face for face in face_records}
    image_query = select(ImageRecord).where(
        ImageRecord.id.in_([face.image_id for face in face_records])
    )
    image_records = session.exec(image_query).scalars().all()
    image_map = {img.id: img for img in image_records}

    # Convert to response format
    cluster_items = []
    for cluster in filtered_clusters:
        face_items = []
        for face_id in cluster.face_ids:
            face = face_map[face_id]
            image = image_map[face.image_id]
            bbox = BoundingBox(
                top=face.bbox_top,
                left=face.bbox_left,
                width=face.bbox_width,
                height=face.bbox_height,
            )
            face_items.append(
                FaceItem(
                    id=face.id,
                    image_id=face.image_id,
                    relative_path=image.relative_path,
                    image_url=f"/media/{image.relative_path}",
                    bbox=bbox,
                    confidence=face.confidence,
                    person_id=face.person_id,
                )
            )

        cluster_items.append(
            FaceClusterItem(
                cluster_id=cluster.cluster_id,
                face_ids=cluster.face_ids,
                representative_face_id=cluster.representative_face_id,
                faces=face_items,
            )
        )

    return FaceClusterResponse(total_clusters=len(cluster_items), clusters=cluster_items)


@router.get("/faces", response_model=FaceListResponse)
def list_faces(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: FaceStatus = FaceStatus.ANY,
    person_id: str | None = Query(default=None),
    session: Session = Depends(get_session_dependency),
) -> FaceListResponse:
    face_query = (
        select(FaceRecord, ImageRecord)
        .join(ImageRecord, FaceRecord.image_id == ImageRecord.id)
        .order_by(FaceRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    count_query = select(func.count()).select_from(FaceRecord)

    if status == FaceStatus.UNASSIGNED:
        face_query = face_query.where(FaceRecord.person_id.is_(None))
        count_query = count_query.where(FaceRecord.person_id.is_(None))
    elif status == FaceStatus.ASSIGNED:
        face_query = face_query.where(FaceRecord.person_id.is_not(None))
        count_query = count_query.where(FaceRecord.person_id.is_not(None))

    if person_id:
        face_query = face_query.where(FaceRecord.person_id == person_id)
        count_query = count_query.where(FaceRecord.person_id == person_id)

    rows = session.exec(face_query).all()
    total_result = session.exec(count_query).first()
    total_value = int(total_result or 0) if isinstance(total_result, (int, float)) else int(total_result[0] if total_result else 0)

    items: List[FaceItem] = []
    for face, image in rows:
        bbox = BoundingBox(
            top=face.bbox_top,
            left=face.bbox_left,
            width=face.bbox_width,
            height=face.bbox_height,
        )
        items.append(
            FaceItem(
                id=face.id,
                image_id=face.image_id,
                relative_path=image.relative_path,
                image_url=f"/media/{image.relative_path}",
                bbox=bbox,
                confidence=face.confidence,
                person_id=face.person_id,
            )
        )

    return FaceListResponse(total=total_value, limit=limit, offset=offset, items=items)


@router.get("/persons", response_model=PersonListResponse)
def list_persons(
    session: Session = Depends(get_session_dependency),
) -> PersonListResponse:
    statement = (
        select(
            PersonRecord,
            func.count(FaceRecord.id).label("face_count"),
        )
        .outerjoin(FaceRecord, FaceRecord.person_id == PersonRecord.id)
        .group_by(PersonRecord.id)
        .order_by(PersonRecord.created_at.desc())
    )
    rows = session.exec(statement).all()
    people: List[tuple[PersonRecord, int]] = []
    cover_face_ids = set()
    for row in rows:
        # Row may be a tuple or SQLAlchemy Row object
        if hasattr(row, "_fields"):
            person = row[0]
            face_count = row[1] if len(row) > 1 else 0
        else:
            person, face_count = row
        people.append((person, int(face_count or 0)))
        if person.cover_face_id:
            cover_face_ids.add(person.cover_face_id)

    cover_map: Dict[str, str] = {}
    if cover_face_ids:
        cover_rows = session.exec(
            select(FaceRecord.id, ImageRecord.relative_path)
            .join(ImageRecord, FaceRecord.image_id == ImageRecord.id)
            .where(FaceRecord.id.in_(cover_face_ids))
        ).all()
        for face_id, relative_path in cover_rows:
            cover_map[face_id] = f"/media/{relative_path}"

    items = []
    for person, face_count in people:
        items.append(
            PersonItem(
                id=person.id,
                label=person.label,
                face_count=face_count,
                cover_face_id=person.cover_face_id,
                cover_image_url=cover_map.get(person.cover_face_id or ""),
            )
        )
    return PersonListResponse(total=len(items), items=items)


@router.post(
    "/persons",
    response_model=PersonItem,
    status_code=status.HTTP_201_CREATED,
)
def create_person(
    payload: CreatePersonRequest,
    session: Session = Depends(get_session_dependency),
) -> PersonItem:
    person_repo = PersonRepository(session)
    person = PersonRecord(id=str(uuid4()), label=payload.label)
    person_repo.create(person)
    session.commit()
    
    return PersonItem(
        id=person.id,
        label=person.label,
        face_count=0,
        cover_face_id=person.cover_face_id,
    )


@router.patch("/persons/{person_id}", response_model=PersonItem)
def rename_person(
    person_id: str,
    payload: UpdatePersonRequest,
    session: Session = Depends(get_session_dependency),
) -> PersonItem:
    person_repo = PersonRepository(session)
    person = person_repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    person_repo.rename(person, payload.label)

    cover_image_url = None
    if person.cover_face_id:
        cover_face = session.get(FaceRecord, person.cover_face_id)
        if cover_face:
            cover_image = session.get(ImageRecord, cover_face.image_id)
            if cover_image:
                cover_image_url = f"/media/{cover_image.relative_path}"

    session.commit()

    return PersonItem(
        id=person.id,
        label=person.label,
        face_count=len(person.faces),
        cover_face_id=person.cover_face_id,
        cover_image_url=cover_image_url,
    )


@router.post("/persons/{person_id}/assign", status_code=status.HTTP_200_OK)
def assign_faces(
    person_id: str,
    payload: AssignFacesRequest,
    session: Session = Depends(get_session_dependency),
) -> dict:
    person_repo = PersonRepository(session)
    face_repo = FaceRepository(session)

    person = person_repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    if not payload.face_ids:
        raise HTTPException(status_code=400, detail="No face_ids provided")

    face_repo.assign_faces(payload.face_ids, person_id)

    if person.cover_face_id is None and payload.face_ids:
        person_repo.update_cover_face(person, payload.face_ids[0])

    session.commit()

    return {"count": len(payload.face_ids)}


@router.post("/persons/{person_id}/unassign", status_code=status.HTTP_200_OK)
def unassign_faces(
    person_id: str,
    payload: AssignFacesRequest,
    session: Session = Depends(get_session_dependency),
) -> dict:
    """Unassign faces from a person (detach them)."""
    person_repo = PersonRepository(session)
    person = person_repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    if not payload.face_ids:
        raise HTTPException(status_code=400, detail="No face_ids provided")

    person_repo.detach_faces(person_id, payload.face_ids)
    session.commit()

    return {"count": len(payload.face_ids)}


@router.delete("/persons/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: str,
    session: Session = Depends(get_session_dependency),
) -> Response:
    """Delete a person and unassign all their faces."""
    person_repo = PersonRepository(session)
    person = person_repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    # Detach all faces first
    face_ids = [face.id for face in person.faces]
    if face_ids:
        person_repo.detach_faces(person_id, face_ids)

    # Delete the person
    person_repo.delete(person)
    session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/persons/{person_id}/merge", response_model=PersonItem)
def merge_persons(
    person_id: str,
    payload: Dict[str, List[str]],
    session: Session = Depends(get_session_dependency),
) -> PersonItem:
    """Merge other persons into this person."""
    person_repo = PersonRepository(session)
    face_repo = FaceRepository(session)

    target_person = person_repo.get(person_id)
    if target_person is None:
        raise HTTPException(status_code=404, detail="Target person not found")

    source_person_ids = payload.get("source_person_ids", [])
    if not source_person_ids:
        raise HTTPException(status_code=400, detail="No source_person_ids provided")

    # Move all faces from source persons to target person
    total_faces_moved = 0
    for source_id in source_person_ids:
        source_person = person_repo.get(source_id)
        if source_person is None:
            continue

        # Get all face IDs from source person
        face_ids = [face.id for face in source_person.faces]
        if face_ids:
            face_repo.assign_faces(face_ids, person_id)
            total_faces_moved += len(face_ids)

        # Delete the source person
        person_repo.delete(source_person)

    session.commit()

    # Refresh to get updated face count
    session.refresh(target_person)

    return PersonItem(
        id=target_person.id,
        label=target_person.label,
        face_count=len(target_person.faces),
        cover_face_id=target_person.cover_face_id,
    )
