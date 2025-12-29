"""
GPU Worker Client
Communicates with remote GPU worker for face detection
"""

from typing import Optional, List
import httpx
from pathlib import Path
import asyncio

from ..core.config import get_settings


class GPUWorkerClient:
    """Client for GPU worker service"""

    def __init__(self, worker_url: Optional[str] = None):
        """
        Initialize GPU worker client

        Args:
            worker_url: URL of GPU worker (e.g., "http://192.168.1.100:8001")
                       If None, will use GPU_WORKER_URL from settings
        """
        self.settings = get_settings()
        self.worker_url = worker_url or getattr(self.settings, 'GPU_WORKER_URL', None)
        self.timeout = 30.0  # 30 second timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()

    async def is_available(self) -> bool:
        """
        Check if GPU worker is available

        Returns:
            True if worker is reachable and healthy
        """
        if not self.worker_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.worker_url}/")
                return response.status_code == 200 and response.json().get("status") == "healthy"
        except Exception as e:
            print(f"GPU worker not available: {e}")
            return False

    async def get_health(self) -> dict:
        """
        Get GPU worker health status

        Returns:
            Health status dict with GPU info
        """
        if not self.worker_url:
            raise RuntimeError("GPU worker URL not configured")

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.worker_url}/")
            response.raise_for_status()
            return response.json()

    async def detect_faces(self, image_path: Path) -> List[dict]:
        """
        Detect faces in image using GPU worker

        Args:
            image_path: Path to image file

        Returns:
            List of face detections with bboxes and embeddings
        """
        if not self.worker_url:
            raise RuntimeError("GPU worker URL not configured")

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Read image file
        with open(image_path, 'rb') as f:
            files = {'file': (image_path.name, f, 'image/jpeg')}

            # Send to GPU worker
            client = self._client or httpx.AsyncClient(timeout=self.timeout)
            try:
                response = await client.post(
                    f"{self.worker_url}/detect",
                    files=files
                )
                response.raise_for_status()

                result = response.json()
                return result.get('faces', [])

            finally:
                if not self._client:
                    await client.aclose()

    async def detect_faces_batch(self, image_paths: List[Path]) -> List[dict]:
        """
        Detect faces in multiple images (batch processing)

        Args:
            image_paths: List of image file paths

        Returns:
            List of results for each image
        """
        if not self.worker_url:
            raise RuntimeError("GPU worker URL not configured")

        files = []
        for path in image_paths:
            if path.exists():
                files.append(('files', (path.name, open(path, 'rb'), 'image/jpeg')))

        try:
            client = self._client or httpx.AsyncClient(timeout=self.timeout * len(image_paths))
            response = await client.post(
                f"{self.worker_url}/detect-batch",
                files=files
            )
            response.raise_for_status()

            return response.json().get('results', [])

        finally:
            # Close file handles
            for _, (_, fh, _) in files:
                fh.close()

            if not self._client:
                await client.aclose()


# Convenience function
async def get_gpu_worker() -> Optional[GPUWorkerClient]:
    """
    Get GPU worker client if available

    Returns:
        GPUWorkerClient if configured and available, None otherwise
    """
    try:
        client = GPUWorkerClient()
        if await client.is_available():
            return client
        return None
    except Exception:
        return None
