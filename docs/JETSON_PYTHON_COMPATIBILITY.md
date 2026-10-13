# Jetson Python compatibility — source/dependency audit, NOT JETSON VERIFIED

**Minimum current runtime: Python 3.10.** Host execution is Python 3.14.3; no Python 3.10 or Jetson interpreter was executed here. This is an evidence-based minimum, not a tested Nano compatibility claim.

| Feature/dependency | Evidence | Minimum constraint |
| --- | --- | --- |
| Evaluated `str | None`, `Path | str` annotations | `app/config.py`, `main.py`, model/service modules | Python 3.10 |
| Built-in generics (`list[...]`, `dict[...]`, `tuple[...]`) | storage, serial, temporal modules | Python 3.9, superseded by unions |
| `Path.is_relative_to`, `unlink(missing_ok=True)` | model-path safety, DB maintenance/simulator persistence | Python 3.9 / 3.8 |
| Dataclasses, string Enum, asynccontextmanager | camera/config/models/lifespan | no StrEnum, no 3.11-only dataclass features |
| match/case and new asyncio APIs | searched runtime: no match/case/task-group/3.14-only feature required | no higher version introduced |
| FastAPI 0.142.2, Starlette 0.52.1, AnyIO 4.14.2, Uvicorn 0.40.0 | installed package `Requires-Python` inspected | >=3.10 |
| Pydantic 2.13.5 / pydantic-core 2.46.5 | installed metadata | >=3.9; compiled aarch64/glibc wheel still must be available |
| pyserial 3.5 | no higher Python minimum in installed metadata | core minimum remains 3.10 |
| pytest 9.1.1 / httpx 0.28.1 | installed metadata | test minimum 3.10 / 3.8 |

`requirements-core.txt` runs API/database/serial/mock paths without OpenCV, CUDA, PyTorch, TensorRT or Roboflow. OpenCV file/live capture is optional and lazy; GPU adapter code imports no GPU runtime. Backend-dependent code is isolated in camera/runtime adapters. Avoid blind code downgrades: older Nano JetPack releases may ship Python 3.6, and an OpenCV extension compiled for that Python cannot simply be placed into a 3.10 venv.

When Nano arrives: record exact board/JetPack/L4T/OS/Python and run diagnostics. If Python <3.10, stop setup with a clear error. Choose a supported isolated interpreter/venv/container **compatible with the actual OS and ARM libraries**, or plan a documented compatibility change; do not replace system Python or JetPack packages. If GPU bindings require a different interpreter, review a separate runtime boundary rather than silently mixing ABI-incompatible modules. All library wheels, GStreamer/CUDA support, TensorRT model ops and performance must be proven on that exact device.
