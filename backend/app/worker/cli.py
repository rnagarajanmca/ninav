from __future__ import annotations

import typer

from ..db import get_session, init_db
from ..services.face_pipeline import FacePipeline
from ..services.media_indexer import MediaIndexer

app = typer.Typer(help="Face detection pipeline utilities")


@app.command("init-db")
def init_db_command() -> None:
    """Create database tables."""
    init_db()
    typer.secho("Database initialized", fg=typer.colors.GREEN)


@app.command("sync-media")
def sync_media() -> None:
    """Scan filesystem for new/removed images."""
    indexer = MediaIndexer()
    with get_session() as session:
        report = indexer.sync(session)
    typer.echo(report.as_dict())


@app.command("scan-faces")
def scan_faces(limit: int = typer.Option(None, help="Max images to scan")) -> None:
    """Run face detection pipeline across new/changed images."""
    with get_session() as session:
        pipeline = FacePipeline(session=session)
        report = pipeline.run(limit=limit)
    typer.echo(report.as_dict())
