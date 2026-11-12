"""Trusted-local runtime boundary. No ONNX/CUDA/TensorRT import or fake output."""

from pathlib import Path
from typing import Callable, Protocol

from app.camera.base import CameraFrame


def trusted_model_path(root: Path, name: str | None) -> Path | None:
    if not name:
        return None
    relative = Path(name)
    if len(name) > 240 or relative.is_absolute() or relative.drive or \
            ".." in relative.parts or "\\" in name or ":" in name:
        raise ValueError("model path must be a trusted local relative filename")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("model path escapes trusted MODEL_ROOT")
    if target.suffix.lower() not in (".onnx", ".engine", ".pt", ".pth"):
        raise ValueError("unsupported model file extension")
    return target


class ModelRuntime(Protocol):
    def load(self) -> bool: ...
    def predict(self, frame: CameraFrame): ...
    def health(self) -> str: ...
    def close(self) -> None: ...


class ExternalRuntimeAdapter:
    """Future ONNX/TensorRT/research executor supplied locally after validation."""
    def __init__(self, kind: str, path: Path | None, threshold: float | None,
                 executor_factory: Callable | None = None):
        if kind not in ("ONNX", "TENSORRT", "RESEARCH"):
            raise ValueError("unsupported external runtime")
        self.kind, self.path, self.threshold = kind, path, threshold
        self.factory = executor_factory
        self.executor = None
        self.state = "NOT_CONFIGURED"

    def load(self) -> bool:
        if self.path is None or self.threshold is None or self.factory is None:
            self.state = "NOT_CONFIGURED"
            return False
        if not self.path.is_file():
            self.state = "NOT_AVAILABLE"
            return False
        self.executor = self.factory(self.path)
        self.state = "NOT_VALIDATED"
        return True

    def predict(self, frame: CameraFrame):
        if self.executor is None:
            raise RuntimeError("real model executor not loaded")
        return self.executor.predict(frame)

    def health(self) -> str:
        return self.state

    def close(self) -> None:
        if self.executor is not None:
            try:
                self.executor.close()
            finally:
                self.executor = None
        self.state = "NOT_CONFIGURED"
