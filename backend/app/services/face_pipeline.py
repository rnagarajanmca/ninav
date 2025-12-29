from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Sequence
from uuid import uuid4

import numpy as np
from sqlmodel import Session

from ..core.config import Settings, get_settings
from ..models import FaceRecord, ImageRecord
from ..repositories import FaceRepository, ImageRepository
from .face_detection import DetectedFace, FaceDetectionService


@dataclass
class FaceProcessingReport:
    scanned: int = 0
    updated: int = 0
    faces_created: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "scanned": self.scanned,
            "updated": self.updated,
            "faces_created": self.faces_created,
        }


class FacePipeline:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        detector: FaceDetectionService | None = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.detector = detector or FaceDetectionService()
        self.image_repo = ImageRepository(session)
        self.face_repo = FaceRepository(session)

    @property
    def root(self) -> Path:
        return self.settings.image_root

    def run(self, limit: int | None = None) -> FaceProcessingReport:
        report = FaceProcessingReport()
        images = self._images_to_process(limit)
        for image in images:
            report.scanned += 1
            created = self._process_image(image)
            if created >= 0:
                report.updated += 1
                report.faces_created += created
        self.session.commit()
        return report

    def _images_to_process(self, limit: int | None) -> Sequence[ImageRecord]:
        records = self.image_repo.list_all()
        candidates: list[ImageRecord] = []
        for record in records:
            if record.last_scanned is None or record.modified_at > record.last_scanned:
                candidates.append(record)
        if limit is not None:
            return candidates[:limit]
        return candidates

    def _process_image(self, record: ImageRecord) -> int:
        path = self.root / record.relative_path
        if not path.exists():
            return 0
        detections = self.detector.detect(path)
        self.face_repo.delete_for_image(record.id)
        faces = [self._to_face(record, detected) for detected in detections]
        self.face_repo.bulk_insert(faces)
        record.last_scanned = datetime.now(UTC)
        return len(faces)

    @staticmethod
    def _to_face(image: ImageRecord, detected: DetectedFace) -> FaceRecord:
        top, left, height, width = detected.to_bbox()
        embedding = FacePipeline._serialize_embedding(detected.embedding)
        norm = float(np.linalg.norm(detected.embedding))
        return FaceRecord(
            id=str(uuid4()),
            image_id=image.id,
            bbox_top=float(top),
            bbox_left=float(left),
            bbox_width=float(width),
            bbox_height=float(height),
            embedding=embedding,
            embedding_norm=norm,
            confidence=detected.confidence,
        )

    @staticmethod
    def _serialize_embedding(vector: np.ndarray) -> bytes:
        return np.asarray(vector, dtype=np.float32).tobytes()
