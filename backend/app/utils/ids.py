from __future__ import annotations

from hashlib import sha1
from pathlib import Path


def image_identifier(path: Path) -> str:
    return sha1(path.as_posix().encode("utf-8")).hexdigest()
