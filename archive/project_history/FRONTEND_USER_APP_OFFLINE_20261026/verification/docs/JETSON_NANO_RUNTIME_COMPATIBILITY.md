# Actual Nano runtime compatibility — preserve system Python/GPU stack

Observed **user-supplied** environment: Nano2GB,Ubuntu18.04.6,L4T32.7.6,system Python3.6.9,CUDA10.2,cuDNN8.2.1,TensorRT8.2.1.8,custom OpenCV4.8.0 with cuda device count1. Those bindings are working reported facts, not proof of modern API/model execution. Do not replace `/usr/bin/python3`, apt-upgrade OS/JetPack destructively, copy ABI-incompatible `.so` files or pip-reinstall OpenCV over custom bindings.

| Existing barrier | Actual source/package consequence |
| --- | --- |
| Evaluated `X | None` / `Path | str` annotations | Need Python3.10;3.6 cannot import production modules as written |
| Built-in `list[...]`, `dict[...]`, `tuple[...]` | Runtime generic evaluation requires3.9; pervasive models/storage signatures |
| dataclasses / asynccontextmanager | stdlib3.7+, not system3.6; backports would only address part of stack |
| pathlib.is_relative_to / missing_ok unlink, int.bit_count, walrus in release tooling |3.9 /3.8 /3.10 /3.8 dependencies; not solved by changing an annotation |
| FastAPI0.142.2,Starlette0.52.1,AnyIO4.14.2,Uvicorn0.40.0 | Pinned modern packages do not support3.6; installed host metadata requires modern Python |
| Pydantic2.13.5 / core2.46.5 | Modern validators/config, compiled aarch64/glibc/interpreter wheel compatibility must be audited; not a3.6 drop-in |
| StrEnum | Current project uses `class Name(str,Enum)`, no current StrEnum blocker; older baseline describing it is historical |
| GPU/OpenCV bindings | Working3.6 extensions cannot simply be imported by isolated3.10+; cuda count1 does not validate actual model/opset/performance |
| Ubuntu18.04 glibc / Nano wheels | Audit actual manylinux/aarch64/build requirements before installation; Windows lock is not an ARM deployment lock |

## Options and ONE recommended path

| Option | Assessment |
| --- | --- |
| A Backport entire production API to3.6 | NOT RECOMMENDED: old unsupported dependency stack, syntax/model/lifecycle/path/security rewrites, extensive regression; threatens preserved behavior |
| B Isolated newer Python alongside system | Viable control/API prerequisite only after ARM/glibc audit; cannot automatically use3.6 GPU/OpenCV ABI |
| **C Modern control/API environment + Python3.6 capture/GPU sidecar boundary** | **RECOMMENDED**: keep working vendor/custom environment, isolate modern API, exchange bounded versioned frame/prediction metadata; no unsafe action path |
| D Compatible container/remote research host | Conditional alternative for research/API; container must match L4T/runtime and storage/network constraints; not automatic Nano TensorRT support |

Recommend **C**, with B as its isolated API interpreter prerequisite. No OS/interpreter installation or production sidecar IPC service is performed in this pass. Current `bringup/` utilities are operator tools/session bridge, not a deployed full sidecar inference service or validated model. Future IPC needs explicit bounds/schema/time/provenance and shadow-only integration after actual runtime review. AI never drives physical feeding now.

## Hardware testing works now without modern backend

From `jetson/`, use existing system interpreter/bindings:

```sh
python3 -m bringup.devices
python3 -m bringup.serial_probe --device /dev/ttyACM0 --count 3
python3 -m bringup.camera --device /dev/video0 --frames 300 --seconds 15
# Above camera command is DRY_RUN; explicit --apply opens V4L2/MJPG720p30.
```

Low-level package uses3.6 syntax/stdlib and pyserial3.5, optional custom cv2 only inside explicit acquisition; imports no `app`, Pydantic/FastAPI/dataclasses/CUDA/TRT/model. Frozen vectors are cross-tested on host. Host AST3.6 grammar plus fake-I/O tests are NOT an actual3.6 interpreter/Nano execution claim; new utility hardware run remains opt-in/user-executed.

Modern backend/capture/data/train tools continue on supported host/isolation. Do not run existing modern `tools.test_serial` / `tools.benchmark_camera` under system3.6 and interpret an import error as hardware failure. Jetson PlatformIO linux_aarch64 cannot resolve pinned55.3.311 per supplied result; build Windows, transfer reviewed files, flash with system esptool3.3.3 **--no-stub**.
