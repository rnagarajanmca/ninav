"""
GPU-accelerated Face Pipeline
Uses remote GPU worker for faster face detection
Falls back to local CPU detection if GPU worker unavailable
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence
import asyncio

from sqlmodel import Session

from ..core.config import Settings, get_settings
from ..models import FaceRecord, ImageRecord
from ..repositories import FaceRepository, ImageRepository
from .face_detection import FaceDetectionService
from .gpu_worker_client import GPUWorkerClient


@dataclass
class FaceProcessingReport:
    scanned: int = 0
    updated: int = 0
    faces_created: int = 0
    gpu_accelerated: bool = False

    def as_dict(self) -> dict:
        return {
            "scanned": self.scanned,
            "updated": self.updated,
            "faces_created": self.faces_created,
            "gpu_accelerated": self.gpu_accelerated,
        }


class GPUFacePipeline:
    """
    Face processing pipeline with GPU acceleration support

    Automatically uses GPU worker if available, falls back to CPU
    """

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        gpu_worker_url: str | None = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.gpu_worker_url = gpu_worker_url
        self.image_repo = ImageRepository(session)
        self.face_repo = FaceRepository(session)

        # Local CPU detector as fallback
        self.cpu_detector = FaceDetectionService()

    @property
    def root(self) -> Path:
        return self.settings.image_root

    async def run_async(self, limit: int | None = None, progress_callback=None) -> FaceProcessingReport:
        """
        Run face detection pipeline asynchronously

        Args:
            limit: Maximum number of images to process
            progress_callback: Optional callback function(current, total, image_name)

        Returns:
            Processing report with statistics
        """
        report = FaceProcessingReport()

        # Check if GPU worker is available
        gpu_client = GPUWorkerClient(self.gpu_worker_url)
        gpu_available = await gpu_client.is_available()

        if gpu_available:
            print("✓ GPU worker available - using GPU acceleration")
            report.gpu_accelerated = True
        else:
            print("⚠ GPU worker not available - using CPU fallback")
            report.gpu_accelerated = False

        images = self._images_to_process(limit)
        total = len(images)

        for idx, image in enumerate(images):
            report.scanned += 1

            # Progress callback
            if progress_callback:
                progress_callback(idx + 1, total, image.relative_path)

            # Process image
            if gpu_available:
                created = await self._process_image_gpu(image, gpu_client)
            else:
                created = self._process_image_cpu(image)

            if created >= 0:
                report.updated += 1
                report.faces_created += created

        self.session.commit()
        return report

    def run(self, limit: int | None = None, progress_callback=None) -> FaceProcessingReport:
        """
        Synchronous wrapper for run_async

        Args:
            limit: Maximum number of images to process
            progress_callback: Optional callback function(current, total, image_name)

        Returns:
            Processing report with statistics
        """
        return asyncio.run(self.run_async(limit, progress_callback))

    def _images_to_process(self, limit: int | None) -> Sequence[ImageRecord]:
        """Get list of images that need processing"""
        records = self.image_repo.list_all()
        candidates: list[ImageRecord] = []

        for record in records:
            if record.last_scanned is None or record.modified_at > record.last_scanned:
                candidates.append(record)

        if limit is not None:
            return candidates[:limit]
        return candidates

    async def _process_image_gpu(self, record: ImageRecord, gpu_client: GPUWorkerClient) -> int:
        """
        Process image using GPU worker

        Args:
            record: Image record to process
            gpu_client: GPU worker client

        Returns:
            Number of faces detected
        """
        path = self.root / record.relative_path

        if not path.exists():
            return 0

        try:
            # Send to GPU worker
            detections = await gpu_client.detect_faces(path)

            # Delete existing faces for this image
            self.face_repo.delete_for_image(record.id)

            # Convert GPU worker results to FaceRecord objects
            faces = []
            for detection in detections:
                face = FaceRecord(
                    id=str(uuid4()),
                    image_id=record.id,
                    bbox_x=detection['bbox_x'],
                    bbox_y=detection['bbox_y'],
                    bbox_width=detection['bbox_width'],
                    bbox_height=detection['bbox_height'],
                    embedding=self._serialize_embedding(detection['embedding']),
                    confidence=detection.get('confidence', 1.0),
                )
                faces.append(face)

            # Save faces
            self.face_repo.bulk_insert(faces)

            # Update last_scanned timestamp
            record.last_scanned = datetime.now(UTC)

            return len(faces)

        except Exception as e:
            print(f"Error processing {record.relative_path} with GPU worker: {e}")
            # Fall back to CPU
            return self._process_image_cpu(record)

    def _process_image_cpu(self, record: ImageRecord) -> int:
        """
        Process image using local CPU detector

        Args:
            record: Image record to process

        Returns:
            Number of faces detected
        """
        path = self.root / record.relative_path

        if not path.exists():
            return 0

        try:
            # Use local CPU detector
            detections = self.cpu_detector.detect(path)

            # Delete existing faces
            self.face_repo.delete_for_image(record.id)

            # Convert to FaceRecord objects
            faces = []
            for detected in detections:
                face = FaceRecord(
                    id=str(uuid4()),
                    image_id=record.id,
                    bbox_x=detected.bbox[0],
                    bbox_y=detected.bbox[1],
                    bbox_width=detected.bbox[2] - detected.bbox[0],
                    bbox_height=detected.bbox[3] - detected.bbox[1],
                    embedding=self._serialize_embedding(detected.embedding),
                    confidence=1.0,
                )
                faces.append(face)

            # Save faces
            self.face_repo.bulk_insert(faces)

            # Update timestamp
            record.last_scanned = datetime.now(UTC)

            return len(faces)

        except Exception as e:
            print(f"Error processing {record.relative_path}: {e}")
            return -1

    def _serialize_embedding(self, embedding: list | np.ndarray) -> bytes:
        """
        Serialize face embedding to bytes

        Args:
            embedding: Face embedding vector

        Returns:
            Serialized bytes
        """
        import numpy as np

        if isinstance(embedding, list):
            embedding = np.array(embedding, dtype=np.float32)
        elif not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding, dtype=np.float32)

        return embedding.tobytes()


from uuid import uuid4
import numpy as np
