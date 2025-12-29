from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_image_root() -> Path:
    """Resolve to the repository-level sample_images directory by default."""

    return _project_root() / "sample_images"


def _default_db_path() -> Path:
    return _project_root() / "data" / "faces.db"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    project_name: str = "Ninav"
    api_prefix: str = "/api"
    image_root: Path = Field(default_factory=_default_image_root)
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [
            "jpg",
            "jpeg",
            "png",
            "gif",
            "webp",
            "bmp",
            "heic",
            "heif",
        ]
    )
    database_url: str = Field(default_factory=lambda: f"sqlite:///{_default_db_path()}")
    face_embedding_dim: int = 128
    face_similarity_threshold: float = 0.6
    face_scan_batch_size: int = 8
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    vite_api_base: str | None = None
    gpu_worker_url: str | None = None  # e.g., "http://192.168.1.100:8001"

    @field_validator("image_root", mode="before")
    @classmethod
    def _coerce_path(cls, value: str | Path) -> Path:
        path = Path(value)
        return path.expanduser().resolve() if not path.is_absolute() else path.resolve()

    @field_validator("allowed_extensions")
    @classmethod
    def _normalize_extensions(cls, values: List[str]) -> List[str]:
        return [v.lower().lstrip(".") for v in values]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [v.strip() for v in value.split(",") if v.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
