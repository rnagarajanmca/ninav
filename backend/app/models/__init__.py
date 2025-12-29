from importlib import import_module
from typing import Any

from .base import BaseModel

__all__ = [
    "BaseModel",
    "ImageRecord",
    "FaceRecord",
    "PersonRecord",
    "FaceEventRecord",
]

_LAZY_MODULES = {
    "ImageRecord": ".image",
    "FaceRecord": ".face",
    "PersonRecord": ".person",
    "FaceEventRecord": ".face_event",
}


def __getattr__(name: str) -> Any:
    module_path = _LAZY_MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_path, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
