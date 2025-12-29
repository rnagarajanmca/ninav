from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from ..core.config import get_settings


def _build_engine():
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {}
    engine = create_engine(db_url, echo=False, connect_args=connect_args)

    # Enable WAL mode for SQLite for better concurrency
    if db_url.startswith("sqlite:///"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()

    return engine


engine = _build_engine()


def init_db() -> None:
    from ..models import BaseModel, ImageRecord, FaceRecord, PersonRecord, FaceEventRecord  # noqa: F401

    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def get_session() -> Session:
    # Import all models to ensure relationships are configured
    from ..models import ImageRecord, FaceRecord, PersonRecord, FaceEventRecord  # noqa: F401
    return Session(engine)


def get_session_dependency() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
