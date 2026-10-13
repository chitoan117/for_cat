# Software bill of materials — locally observed inventory

Generated from installed metadata; not legal compatibility, vulnerability or Jetson support certification. Core requirements remain separate from developer/test/quality tools.

| Python distribution | Installed version | Discoverable license metadata |
| --- | --- | --- |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.14.2 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| click | 8.5.0 | BSD-3-Clause |
| colorama | 0.4.6 | NOT_DISCOVERABLE_IN_LOCAL_METADATA |
| fastapi | 0.142.2 | MIT |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| idna | 3.20 | BSD-3-Clause |
| iniconfig | 2.3.0 | MIT |
| librt | 0.16.0 | MIT |
| mypy | 1.19.1 | MIT |
| mypy_extensions | 1.1.0 | MIT |
| numpy | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| opencv-python | 4.13.0.92 | Apache 2.0 |
| opentelemetry-api | 1.45.0 | Apache-2.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pathspec | 1.1.1 | NOT_DISCOVERABLE_IN_LOCAL_METADATA |
| pillow | 12.1.1 | MIT-CMU |
| pip | 25.3 | MIT |
| pluggy | 1.6.0 | MIT |
| pydantic | 2.13.5 | MIT |
| pydantic_core | 2.46.5 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| pyserial | 3.5 | BSD |
| pytest | 9.1.1 | MIT |
| ruff | 0.14.10 | NOT_DISCOVERABLE_IN_LOCAL_METADATA |
| starlette | 0.52.1 | BSD-3-Clause |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| uvicorn | 0.40.0 | BSD-3-Clause |

## Build packages (local PlatformIO manifests)

| Package | Version metadata | License metadata |
| --- | --- | --- |
| espressif32 | 55.03.311 | Apache-2.0 |
| framework-arduinoespressif32 | 3.3.11 | LGPL-2.1-or-later |
| framework-arduinoespressif32-libs | 5.5.5+sha.b774170ff46 | LGPL-2.1-or-later |
| toolchain-xtensa-esp-elf | 14.2.0+20260121 | GPL-2.0-or-later |
| tool-esptoolpy | 5.3.0 | GPL-2.0-or-later |

Important tools: observed Python3.14.3, PlatformIO Core6.2.0, Zig0.16.0; pinned espressif32 platform55.3.311 and Arduino3.3.11 compile environment.
Quality tooling is pinned separately in requirements-quality.txt (Ruff/mypy), never a production dependency. Missing/ambiguous license fields require review of actual distribution license files; no license was guessed.
No model/dataset is bundled. See THIRD_PARTY_ATTRIBUTION.md and REPRODUCIBLE_ENVIRONMENT.md.
