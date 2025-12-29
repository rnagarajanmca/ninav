from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .core.config import get_settings
from .db import init_db
from .services.thumbnail_service import ThumbnailService, ThumbnailSize


def validate_media_path(relative_path: str, root: Path) -> Path:
    """Validate media path to prevent directory traversal attacks."""
    try:
        # Resolve the full path
        full_path = (root / relative_path).resolve()

        # Check if the resolved path is within the media root
        if not full_path.is_relative_to(root):
            raise HTTPException(status_code=403, detail="Access denied: Invalid path")

        # Check if file exists
        if not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        return full_path
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid path: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: cleanup if needed


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.project_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)

    media_root = settings.image_root.resolve()
    thumbnail_service = ThumbnailService(media_root)

    @app.get("/media/{path:path}")
    async def serve_media(path: str) -> FileResponse:
        """Serve media files with path validation."""
        validated_path = validate_media_path(path, media_root)
        return FileResponse(
            validated_path,
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
            },
        )

    @app.get("/thumbnails/{size}/{path:path}")
    async def serve_thumbnail(path: str, size: ThumbnailSize = "medium") -> FileResponse:
        """Serve thumbnail, generating on-demand if needed."""
        # Validate the original image path first
        original_path = validate_media_path(path, media_root)

        # Check if thumbnail exists and is up to date
        thumbnail_path = thumbnail_service.get_thumbnail_path(path, size)

        try:
            # Generate thumbnail if needed
            if not thumbnail_path.exists() or thumbnail_path.stat().st_mtime < original_path.stat().st_mtime:
                thumbnail_path = thumbnail_service.generate_thumbnail(original_path, path, size)

            return FileResponse(
                thumbnail_path,
                headers={
                    "Cache-Control": "public, max-age=31536000, immutable",
                },
            )
        except Exception as e:
            # Fallback to original image if thumbnail generation fails
            return FileResponse(
                original_path,
                headers={
                    "Cache-Control": "public, max-age=31536000, immutable",
                },
            )

    return app


app = create_app()
