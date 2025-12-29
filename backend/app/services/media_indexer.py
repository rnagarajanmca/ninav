from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from sqlmodel import Session, select

from ..core.config import Settings, get_settings
from ..models import ImageRecord
from ..utils import compute_checksum
from ..utils.ids import image_identifier


@dataclass
class SyncReport:
    scanned: int = 0
    inserted: int = 0
    updated: int = 0
    removed: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "scanned": self.scanned,
            "inserted": self.inserted,
            "updated": self.updated,
            "removed": self.removed,
        }


class MediaIndexer:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    @property
    def root(self) -> Path:
        return self._settings.image_root

    def sync(self, session: Session) -> SyncReport:
        report = SyncReport()
        existing = {
            record.relative_path: record
            for record in session.exec(select(ImageRecord)).all()
        }
        seen_paths: set[str] = set()

        for path in self._iter_image_files():
            report.scanned += 1
            relative_path = path.relative_to(self.root).as_posix()
            seen_paths.add(relative_path)

            checksum = compute_checksum(path)
            stat = path.stat()
            size_bytes = stat.st_size
            modified_at = datetime.fromtimestamp(stat.st_mtime)
            identifier = image_identifier(path)

            record = existing.get(relative_path)
            if record is None:
                record = ImageRecord(
                    id=identifier,
                    relative_path=relative_path,
                    checksum=checksum,
                    size_bytes=size_bytes,
                    modified_at=modified_at,
                    last_scanned=None,
                )
                session.add(record)
                report.inserted += 1
                continue

            if (
                record.checksum != checksum
                or record.size_bytes != size_bytes
                or record.modified_at != modified_at
            ):
                record.checksum = checksum
                record.size_bytes = size_bytes
                record.modified_at = modified_at
                record.touch()
                report.updated += 1

        for relative_path, record in existing.items():
            if relative_path not in seen_paths:
                session.delete(record)
                report.removed += 1

        session.commit()
        return report

    def _iter_image_files(self) -> Iterable[Path]:
        allowed = tuple(f".{ext}" for ext in self._settings.allowed_extensions)
        for path in sorted(self.root.rglob("*")):
            # Skip hidden/system directories
            if ".trash" in path.parts or ".thumbnails" in path.parts:
                continue
            if path.is_file() and path.suffix.lower() in allowed:
                yield path
