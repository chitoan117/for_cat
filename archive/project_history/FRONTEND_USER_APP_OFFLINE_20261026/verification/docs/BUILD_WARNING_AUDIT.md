# Build/static warning audit — quality pass

Starting full regression:217 Python,1328 native assertions,7 vectors,18 guards,11 builds PASS. Tools installed only in the isolated developer environment: Ruff0.14.10 / mypy1.19.1, pinned in `requirements-quality.txt`. No production ML/static dependency added.

| Finding | Classification | Resolution / evidence |
| --- | --- | --- |
| Eight unused imports in source/tools/AI tests | Reviewed dead imports, not a functionality claim | Removed individually; Ruff correctness rules pass |
| PreferencePolicy() argument default flagged B008 | Immutable frozen default; not shared mutable state | Named immutable singleton preserves behavior; no rule suppressed |
| Ultrasonic uint32→float warning under conversion flags | Intentional unit conversion, bounded/exact by echo timeout≤100000us (<2^24) | Explicit cast with bound rationale; no algorithm/physical assumption changed |
| Two-octet OR→uint16 safety record warning | Integer promotion, value bounded≤65535 | Explicit bounded cast; CRC/layout unchanged |
| Windows PlatformIO firmware-metrics/codepage notice | KNOWN TOOLCHAIN NOISE / PLATFORM-SPECIFIC | Actual RAM/flash metrics still present; no warning filter added |
| pip newer-version notice | TOOL NOTICE, not dependency conflict | No blind upgrade; pip check verifies consistency, not vulnerabilities |
| mypy dynamic runtime protocols outside five selected files | DOCUMENTED SCOPE LIMITATION | Selected artifact/sampling/session/tracking/service files checked; not a whole-project typing claim |
| cppcheck/clang-tidy unavailable | TOOL AVAILABILITY | Stricter native compiler used, not a claimed cppcheck result |

Native quality command uses `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror` on both portable harnesses and executes them. No new diagnostic suppression; strict quality compilation does not use even the pre-existing libc++ nullability flag in the standard runner. Project warnings fail quality checks.

Initial defect regressions were deliberately RED before fixes; JSON-nesting/soak-fixture/README-link-tool failures were diagnosed and fixed, not suppressed. Ruff is correctness-focused F/B rules, not a wholesale formatting rewrite. mypy covers5 selected files with external imports silent/missing stubs permitted; dynamic services are tested, not asserted fully statically typed. Actual final logs: `.release/{ruff,mypy,strict-*,quality_summary}.log/json`; normal build warnings/footprints: `.checks/firmware-builds.log`.
