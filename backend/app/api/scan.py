from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..core.config import get_settings
from ..db import get_session_dependency
from ..models import ImageRecord
from ..services.media_indexer import MediaIndexer

router = APIRouter(tags=["scan"])


class ScanStatus(BaseModel):
    """Face scanning status response"""
    is_running: bool
    total_images: int
    processed_images: int
    current_image: Optional[str] = None
    started_at: Optional[datetime] = None
    progress_percent: float = 0.0
    is_syncing: bool = False


class ScanControl(BaseModel):
    """Face scanning control request"""
    action: str  # "start" or "stop"


class SyncReport(BaseModel):
    """Media sync report response"""
    scanned: int
    inserted: int
    updated: int
    removed: int


# Global scan state (in production, use Redis or database)
_scan_state = {
    "is_running": False,
    "total_images": 0,
    "processed_images": 0,
    "current_image": None,
    "started_at": None,
    "should_stop": False,
    "progress_percent": 0.0,
    "is_syncing": False,
}

# Global sync state
_sync_state = {
    "is_running": False,
    "last_report": None,
}


def run_media_sync() -> None:
    """Background task to sync media directory"""
    from ..db import get_session

    session = None
    try:
        session = get_session()
        settings = get_settings()

        print("Starting media sync...")
        indexer = MediaIndexer(settings)
        report = indexer.sync(session)
        print(f"Media sync complete: {report.as_dict()}")

        _sync_state["last_report"] = report.as_dict()
    except Exception as e:
        print(f"Error in media sync: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if session:
            session.close()
        _sync_state["is_running"] = False


def run_face_scan() -> None:
    """Background task to scan faces in images"""
    from pathlib import Path
    from sqlmodel import func

    # Create a new session for this background task
    from ..db import get_session
    from ..services.face_pipeline import FacePipeline

    session = None
    try:
        session = get_session()
        settings = get_settings()

        # Check if database has images
        count_query = select(func.count()).select_from(ImageRecord)
        image_count = session.exec(count_query).one()

        # Only sync if database is empty or has very few images
        if image_count < 10:
            print("Syncing media directory (database has few images)...")
            _scan_state["is_syncing"] = True
            _scan_state["current_image"] = "Syncing media directory..."
            indexer = MediaIndexer(settings)
            sync_report = indexer.sync(session)
            print(f"Media sync complete: {sync_report.as_dict()}")
            _scan_state["is_syncing"] = False
            _scan_state["current_image"] = None
        else:
            print(f"Skipping sync - database already has {image_count} images")

        # Get all images that need face detection
        query = select(ImageRecord)
        images = list(session.exec(query).all())

        _scan_state["total_images"] = len(images)
        _scan_state["processed_images"] = 0
        _scan_state["started_at"] = datetime.utcnow()

        print(f"Starting face scan for {len(images)} images")

        # Create face pipeline for real face detection
        pipeline = FacePipeline(session, settings)

        for image in images:
            if _scan_state["should_stop"]:
                print("Scan stopped by user")
                break

            _scan_state["current_image"] = image.relative_path

            try:
                # Skip if already scanned
                if image.last_scanned is not None:
                    print(f"Skipping {image.relative_path}: already scanned")
                else:
                    # Process image with real face detection
                    path = settings.image_root / image.relative_path
                    if path.exists():
                        faces_created = pipeline._process_image(image)
                        session.commit()
                        print(f"Processed {image.relative_path}: {faces_created} faces detected")
                    else:
                        print(f"Skipping {image.relative_path}: file not found")
                        # Mark as scanned even if file not found to avoid retrying
                        image.last_scanned = datetime.utcnow()
                        session.commit()

            except Exception as e:
                # Continue on error
                print(f"Error processing {image.relative_path}: {e}")
                import traceback
                traceback.print_exc()

            _scan_state["processed_images"] += 1
            _scan_state["progress_percent"] = (
                (_scan_state["processed_images"] / _scan_state["total_images"]) * 100
                if _scan_state["total_images"] > 0
                else 0
            )

        print(f"Face scan completed. Processed {_scan_state['processed_images']} images")

    except Exception as e:
        print(f"Error in face scan: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if session:
            session.close()
        # Reset state when done
        _scan_state["is_running"] = False
        _scan_state["should_stop"] = False
        _scan_state["current_image"] = None


@router.get("/scan/status", response_model=ScanStatus)
def get_scan_status() -> ScanStatus:
    """Get current face scanning status"""
    return ScanStatus(
        is_running=_scan_state["is_running"],
        total_images=_scan_state["total_images"],
        processed_images=_scan_state["processed_images"],
        current_image=_scan_state["current_image"],
        started_at=_scan_state["started_at"],
        progress_percent=_scan_state["progress_percent"],
        is_syncing=_scan_state["is_syncing"],
    )


@router.get("/scan/sync-status")
def get_sync_status() -> dict:
    """Get current media sync status"""
    return {
        "is_running": _sync_state["is_running"],
        "last_report": _sync_state["last_report"],
    }


@router.post("/scan/sync-media")
async def sync_media(background_tasks: BackgroundTasks) -> dict:
    """Sync media directory with database in background"""
    if _sync_state["is_running"]:
        raise HTTPException(status_code=400, detail="Sync is already running")

    _sync_state["is_running"] = True
    _sync_state["last_report"] = None
    background_tasks.add_task(run_media_sync)

    return {
        "status": "started",
        "message": "Media sync started in background",
    }


@router.post("/scan/control")
async def control_scan(
    control: ScanControl,
    background_tasks: BackgroundTasks,
) -> dict:
    """Start or stop face scanning"""

    if control.action == "start":
        if _scan_state["is_running"]:
            raise HTTPException(status_code=400, detail="Scan is already running")

        _scan_state["is_running"] = True
        _scan_state["should_stop"] = False
        _scan_state["processed_images"] = 0
        _scan_state["progress_percent"] = 0.0
        background_tasks.add_task(run_face_scan)

        return {"status": "started", "message": "Face scanning started"}

    elif control.action == "stop":
        if not _scan_state["is_running"]:
            raise HTTPException(status_code=400, detail="No scan is running")

        _scan_state["should_stop"] = True
        return {"status": "stopping", "message": "Face scanning will stop after current image"}

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'start' or 'stop'")
