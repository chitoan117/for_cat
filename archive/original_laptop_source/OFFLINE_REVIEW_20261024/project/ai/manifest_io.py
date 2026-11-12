"""Cooperative single-writer lock and atomic metadata replacement, offline only."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid


@contextmanager
def dataset_lock(root: Path, apply=True):
    root = Path(root)
    if not apply:
        yield
        return
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".dataset-write.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("dataset writer lock exists; inspect its PID, do not remove a live writer lock") from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "created_at": datetime.now(timezone.utc).isoformat()}))
        yield
    finally:
        lock.unlink()


def atomic_text(path, text):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=".metadata-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name == "posix":
            try:
                descriptor = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            except OSError:
                pass # rename already committed; never trigger caller rollback of owned images
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def rows_text(rows, limit=200_000_000):
    text = "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows)
    if len(text.encode("utf-8")) > limit:
        raise ValueError("metadata byte budget exceeded; existing manifest retained")
    return text


def replace_manifest(root, rows, *, action, details):
    """Caller owns dataset_lock. Save an immutable preimage before atomic commit."""
    root = Path(root)
    path = root / "manifest.jsonl"
    before = path.read_bytes() if path.exists() else b""
    after = rows_text(rows)
    if before == after.encode("utf-8"):
        return None
    revision = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid.uuid4().hex[:8]
    folder = root / "annotations" / "history" / revision
    folder.mkdir(parents=True, exist_ok=False)
    with (folder / "manifest_before.jsonl").open("xb") as stream:
        stream.write(before)
        stream.flush(); os.fsync(stream.fileno())
    receipt = {"revision": revision, "action": action, "recorded_at": datetime.now(timezone.utc).isoformat(),
               "before_sha256": hashlib.sha256(before).hexdigest(),
               "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(), "details": details}
    with (folder / "revision.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.flush(); os.fsync(stream.fileno())
    atomic_text(path, after)
    return revision
