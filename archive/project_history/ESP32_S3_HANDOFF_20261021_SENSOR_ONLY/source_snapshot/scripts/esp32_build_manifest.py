"""Automatic provenance from real PlatformIO config, actual build output and artifacts."""
import hashlib
import json
import re
import shlex
import subprocess


def generate(root, logs, pio, profiles, build_output):
    raw = subprocess.check_output([str(pio), "project", "config", "--project-dir", str(root / "esp32"), "--json-output"])
    config = {name: dict(values) for name, values in json.loads(raw)}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root))
    entries = []
    fingerprint = hashlib.sha256()
    for file in sorted((root / "esp32").rglob("*")):
        if file.is_file() and ".pio" not in file.parts:
            fingerprint.update(str(file.relative_to(root)).replace("\\", "/").encode())
            fingerprint.update(file.read_bytes().replace(b"\r\n", b"\n"))
    for name in profiles:
        environment = config["env:" + name]
        flags = [flag for line in environment["build_flags"] for flag in shlex.split(line)]
        if "-DACTUATOR_OUTPUTS_ENABLED=0" not in flags:
            raise ValueError("build flags lack disabled actuator invariant: " + name)
        match = re.search(r"Processing " + re.escape(name) + r" \(.*?(?=\nProcessing |\Z)", build_output, re.S)
        if not match:
            raise ValueError("missing compiler output: " + name)
        ram = re.search(r"RAM:.*?used (\d+) bytes", match.group())
        flash = re.search(r"Flash:.*?used (\d+) bytes", match.group())
        if not ram or not flash:
            raise ValueError("missing actual size metrics: " + name)
        artifacts = []
        for file in (root / "esp32/.pio/build" / name).glob("*.bin"):
            artifacts.append({"file": file.name, "bytes": file.stat().st_size,
                              "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
        if not any(item["file"] == "firmware.bin" for item in artifacts):
            raise ValueError("missing firmware artifact")
        entries.append({"environment": name, "board_target": environment["board"], "platform": environment["platform"],
                        "build_flags": flags, "source_commit": commit, "source_worktree_dirty": dirty,
                        "ram_bytes": int(ram.group(1)), "flash_bytes": int(flash.group(1)),
                        "actuator_outputs_enabled": 0, "artifacts": artifacts})
    manifest = {"schema_version": 1, "software_status": "BUILT_AND_TESTED", "physical_validation": "NOT_TESTED",
                "source_commit": commit, "source_worktree_dirty": dirty, "environments": entries,
                "source_fingerprint_sha256": fingerprint.hexdigest(),
                "reproducibility": "Pinned existing toolchain/config and artifact hashes; absolute-path/time bit reproducibility not asserted"}
    path = logs / "firmware_build_manifest.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
    return path
