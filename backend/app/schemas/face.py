from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class FaceStatus(str, Enum):
    ANY = "any"
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"


class BoundingBox(BaseModel):
    top: float
    left: float
    width: float
    height: float


class FaceItem(BaseModel):
    id: str
    image_id: str
    relative_path: str
    image_url: str
    bbox: BoundingBox
    confidence: float
    person_id: Optional[str] = None


class FaceListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[FaceItem]


class PersonItem(BaseModel):
    id: str
    label: str
    face_count: int
    cover_face_id: Optional[str] = None
    cover_image_url: Optional[str] = None


class PersonListResponse(BaseModel):
    total: int
    items: List[PersonItem]


class CreatePersonRequest(BaseModel):
    label: str


class UpdatePersonRequest(BaseModel):
    label: str


class AssignFacesRequest(BaseModel):
    face_ids: List[str]


class FaceClusterItem(BaseModel):
    cluster_id: int
    face_ids: List[str]
    representative_face_id: str
    faces: List[FaceItem]


class FaceClusterResponse(BaseModel):
    total_clusters: int
    clusters: List[FaceClusterItem]
