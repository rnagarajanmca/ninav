from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from ..models import FaceRecord


@dataclass
class FaceCluster:
    cluster_id: int
    face_ids: list[str]
    representative_face_id: str  # Face with highest confidence in the cluster


class FaceClusteringService:
    """Service for clustering similar faces using hierarchical clustering."""

    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize the clustering service.

        Args:
            similarity_threshold: Cosine similarity threshold (0-1).
                                 Higher values = stricter matching (fewer clusters).
                                 Typical values: 0.5-0.7
        """
        self.similarity_threshold = similarity_threshold

    def cluster_faces(self, faces: Sequence[FaceRecord]) -> list[FaceCluster]:
        """
        Cluster faces based on embedding similarity.

        Args:
            faces: List of face records with embeddings

        Returns:
            List of face clusters, sorted by cluster size (largest first)
        """
        if len(faces) == 0:
            return []

        if len(faces) == 1:
            face = faces[0]
            return [
                FaceCluster(
                    cluster_id=1,
                    face_ids=[face.id],
                    representative_face_id=face.id,
                )
            ]

        # Convert embeddings to numpy array
        embeddings = np.array([self._deserialize_embedding(face.embedding) for face in faces])

        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings_normalized = embeddings / norms

        # Compute pairwise cosine similarities
        similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)

        # Convert to distance matrix (1 - similarity)
        distance_matrix = 1 - similarity_matrix

        # Convert to condensed distance matrix for scipy
        condensed_distances = squareform(distance_matrix, checks=False)

        # Perform hierarchical clustering
        linkage_matrix = linkage(condensed_distances, method="average")

        # Cut the dendrogram at the threshold to form clusters
        distance_threshold = 1 - self.similarity_threshold
        cluster_labels = fcluster(linkage_matrix, distance_threshold, criterion="distance")

        # Group faces by cluster
        clusters_dict: dict[int, list[int]] = {}
        for idx, label in enumerate(cluster_labels):
            if label not in clusters_dict:
                clusters_dict[label] = []
            clusters_dict[label].append(idx)

        # Create FaceCluster objects
        clusters = []
        for cluster_id, face_indices in clusters_dict.items():
            cluster_faces = [faces[idx] for idx in face_indices]
            face_ids = [face.id for face in cluster_faces]

            # Select representative face (highest confidence)
            representative = max(cluster_faces, key=lambda f: f.confidence)

            clusters.append(
                FaceCluster(
                    cluster_id=cluster_id,
                    face_ids=face_ids,
                    representative_face_id=representative.id,
                )
            )

        # Sort by cluster size (largest first)
        clusters.sort(key=lambda c: len(c.face_ids), reverse=True)

        return clusters

    @staticmethod
    def _deserialize_embedding(embedding_bytes: bytes) -> np.ndarray:
        """Convert bytes back to numpy array."""
        return np.frombuffer(embedding_bytes, dtype=np.float32)
