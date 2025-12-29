from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import face_recognition
import numpy as np


@dataclass(slots=True)
class DetectedFace:
    top: int
    right: int
    bottom: int
    left: int
    embedding: np.ndarray
    confidence: float = 1.0

    def to_bbox(self) -> tuple[int, int, int, int]:
        return self.top, self.left, self.bottom - self.top, self.right - self.left


class FaceDetectionService:
    def detect(self, path: Path) -> Sequence[DetectedFace]:
        image = face_recognition.load_image_file(str(path))
        face_locations = face_recognition.face_locations(image, model="hog")
        if not face_locations:
            return []
        encodings = face_recognition.face_encodings(image, face_locations)
        results: List[DetectedFace] = []
        for (top, right, bottom, left), encoding in zip(face_locations, encodings):
            vector = np.asarray(encoding, dtype=np.float32)
            results.append(
                DetectedFace(
                    top=top,
                    right=right,
                    bottom=bottom,
                    left=left,
                    embedding=vector,
                    confidence=1.0,
                )
            )
        return results
