from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select, func

from ..core.config import get_settings
from ..db import get_session_dependency
from ..models import ImageRecord
from ..schemas import (
    ImageDeleteRequest,
    ImageDeleteResponse,
    ImageListResponse,
    ImageMetadata,
    ImageRenameRequest,
)
from ..services.image_service import ImageQuery, ImageService
from .faces import router as faces_router
from .scan import router as scan_router

api_router = APIRouter()
api_router.include_router(faces_router)
api_router.include_router(scan_router)


def get_image_service() -> ImageService:
    settings = get_settings()
    root = settings.image_root
    if not root.exists():
        raise HTTPException(status_code=500, detail=f"Image root '{root}' does not exist")
    return ImageService(settings=settings)


@api_router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def get_directory_size(path: Path) -> int:
    """Calculate total size of all files in a directory recursively."""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_directory_size(Path(entry.path))
    except (PermissionError, OSError):
        pass
    return total


@api_router.get("/storage", tags=["system"])
def get_storage_stats(service: ImageService = Depends(get_image_service)) -> dict:
    """Get storage statistics for the image library."""
    settings = get_settings()
    image_root = settings.image_root

    # Calculate total size of media directory
    total_bytes = get_directory_size(image_root) if image_root.exists() else 0

    # Get image count from service
    _, image_count = service.list_images(ImageQuery(page=1, page_size=1))

    return {
        "total_bytes": total_bytes,
        "total_gb": round(total_bytes / (1024**3), 2),
        "image_count": image_count,
        "media_path": str(image_root),
    }


@api_router.get("/images", response_model=ImageListResponse, tags=["images"])
def list_images(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=60, ge=1, le=240),
    session: Session = Depends(get_session_dependency),
) -> ImageListResponse:
    settings = get_settings()

    # Get total count
    total_stmt = select(func.count()).select_from(ImageRecord)
    total = session.exec(total_stmt).one()

    # Get paginated results
    offset = (page - 1) * page_size
    stmt = select(ImageRecord).offset(offset).limit(page_size).order_by(ImageRecord.relative_path)
    records = session.exec(stmt).all()

    # Convert to ImageMetadata
    items = [
        ImageMetadata(
            id=record.id,
            name=Path(record.relative_path).name,
            relative_path=record.relative_path,
            url=f"/media/{record.relative_path}",
            size_bytes=record.size_bytes,
            modified_at=record.modified_at,
        )
        for record in records
    ]

    return ImageListResponse(items=items, page=page, page_size=page_size, total=total)


def _map_file_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, FileExistsError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied when touching file")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@api_router.post("/images/rename", response_model=ImageMetadata, tags=["images"])
def rename_image(request: ImageRenameRequest, service: ImageService = Depends(get_image_service)) -> ImageMetadata:
    try:
        return service.rename_image(request.relative_path, request.new_name)
    except Exception as exc:  # pragma: no cover - FastAPI handles HTTPException
        raise _map_file_errors(exc)


@api_router.post("/images/delete", response_model=ImageDeleteResponse, tags=["images"])
def delete_image(
    request: ImageDeleteRequest,
    service: ImageService = Depends(get_image_service),
    session: Session = Depends(get_session_dependency),
) -> ImageDeleteResponse:
    try:
        # Delete the file (move to trash)
        response = service.delete_image(request.relative_path)

        # Also remove from database
        image_record = session.exec(
            select(ImageRecord).where(ImageRecord.relative_path == request.relative_path)
        ).first()
        if image_record:
            session.delete(image_record)
            session.commit()

        return response
    except Exception as exc:  # pragma: no cover
        raise _map_file_errors(exc)
