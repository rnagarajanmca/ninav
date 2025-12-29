"""Seed a few placeholder images into sample_images for local testing."""

from __future__ import annotations

import base64
from pathlib import Path

DATA = {
    # 1x1 PNGs in different colors (valid base64, multiples of 4)
    "sample_images/lake.png": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAgMBgWxeJTsAAAAASUVORK5CYII=",
    "sample_images/mountains.png": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/xcAAoMBgkYlR5sAAAAASUVORK5CYII=",
    "sample_images/people/beach.png": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/xcAAwMCAOr9qFQAAAAASUVORK5CYII=",
}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative_path, encoded in DATA.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(encoded))
        print(f"Wrote {relative_path}")


if __name__ == "__main__":
    main()
