"""
GPU Worker Service for Face Detection
Runs on Windows machine with NVIDIA GPU
Provides face detection API using InsightFace
"""

import io
import base64
from typing import List, Optional
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import insightface
from insightface.app import FaceAnalysis
from PIL import Image


# Initialize FastAPI
app = FastAPI(
    title="GPU Face Detection Worker",
    description="High-performance face detection using InsightFace on GPU",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class FaceDetection(BaseModel):
    """Face detection result"""
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    embedding: List[float]
    confidence: float
    landmarks: Optional[List[List[float]]] = None


class DetectionResponse(BaseModel):
    """Response for face detection"""
    faces: List[FaceDetection]
    image_width: int
    image_height: int
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    gpu_available: bool
    model_loaded: bool
    device: str


# Global face analyzer
face_analyzer = None


def get_device_info() -> tuple[bool, str]:
    """Get GPU availability info"""
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()

        if 'CUDAExecutionProvider' in providers:
            return True, "CUDA (NVIDIA GPU)"
        elif 'DmlExecutionProvider' in providers:
            return True, "DirectML (Windows GPU)"
        else:
            return False, "CPU"
    except Exception:
        return False, "CPU"


@app.on_event("startup")
async def startup_event():
    """Initialize face detection model on startup"""
    global face_analyzer

    print("Initializing InsightFace model...")

    try:
        # Check GPU availability
        gpu_available, device = get_device_info()
        print(f"Device: {device}")

        # Initialize face analyzer
        face_analyzer = FaceAnalysis(
            name='buffalo_l',  # High accuracy model
            providers=['CUDAExecutionProvider', 'DmlExecutionProvider', 'CPUExecutionProvider']
        )

        # Prepare model with specific context (0 for GPU, -1 for CPU)
        ctx_id = 0 if gpu_available else -1
        face_analyzer.prepare(ctx_id=ctx_id, det_size=(640, 640))

        print(f"✓ InsightFace initialized successfully on {device}")
        print(f"✓ Detection size: 640x640")
        print(f"✓ Model: buffalo_l (high accuracy)")

    except Exception as e:
        print(f"✗ Error initializing face analyzer: {e}")
        import traceback
        traceback.print_exc()


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    gpu_available, device = get_device_info()

    return HealthResponse(
        status="healthy" if face_analyzer is not None else "initializing",
        gpu_available=gpu_available,
        model_loaded=face_analyzer is not None,
        device=device
    )


@app.post("/detect", response_model=DetectionResponse)
async def detect_faces(file: UploadFile = File(...)):
    """
    Detect faces in uploaded image

    Args:
        file: Image file (JPG, PNG, etc.)

    Returns:
        Face detection results with bounding boxes and embeddings
    """
    if face_analyzer is None:
        raise HTTPException(status_code=503, message="Model not initialized")

    import time
    start_time = time.time()

    try:
        # Read image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")

        # Get image dimensions
        height, width = img.shape[:2]

        # Detect faces
        faces = face_analyzer.get(img)

        # Convert results
        detections = []
        for face in faces:
            # Get bounding box
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox

            # Get landmarks (5 points: eyes, nose, mouth corners)
            landmarks = face.kps.tolist() if hasattr(face, 'kps') else None

            detection = FaceDetection(
                bbox_x=int(x1),
                bbox_y=int(y1),
                bbox_width=int(x2 - x1),
                bbox_height=int(y2 - y1),
                embedding=face.embedding.tolist(),  # 512-dim embedding
                confidence=float(face.det_score),
                landmarks=landmarks
            )
            detections.append(detection)

        processing_time = (time.time() - start_time) * 1000

        return DetectionResponse(
            faces=detections,
            image_width=width,
            image_height=height,
            processing_time_ms=processing_time
        )

    except Exception as e:
        print(f"Error processing image: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect-batch")
async def detect_faces_batch(files: List[UploadFile] = File(...)):
    """
    Detect faces in multiple images (batch processing)

    Args:
        files: List of image files

    Returns:
        List of detection results
    """
    if face_analyzer is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    results = []

    for file in files:
        try:
            result = await detect_faces(file)
            results.append({
                "filename": file.filename,
                "success": True,
                "data": result.dict()
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    return {"results": results, "total": len(files)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all interfaces
        port=8001,
        log_level="info"
    )
