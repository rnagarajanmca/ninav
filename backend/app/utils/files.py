from __future__ import annotations

import hashlib
from pathlib import Path


def compute_checksum(path: Path, chunk_size: int = 1 << 20) -> str:
    sha = hashlib.sha1()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            sha.update(chunk)
    return sha.hexdigest()
