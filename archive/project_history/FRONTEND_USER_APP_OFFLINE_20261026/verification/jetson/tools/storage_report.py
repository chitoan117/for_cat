"""Bounded disk inventory only: never deletes/creates data or scans symlink trees."""

import argparse
import json
import os
import shutil
from pathlib import Path

from app.config import DATA_PATH


def tree_size(root: Path, max_entries=10000) -> dict:
    if not root.is_dir():
        return {"bytes": 0, "files": 0, "available": False, "truncated": False}
    size = files = entries = 0
    for parent, directories, names in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories if not (Path(parent) / name).is_symlink()]
        for name in names:
            entries += 1
            if entries > max_entries:
                return {"bytes": size, "files": files, "available": True, "truncated": True}
            path = Path(parent) / name
            if path.is_symlink():
                continue
            try:
                size += path.stat().st_size
                files += 1
            except OSError:
                pass
    return {"bytes": size, "files": files, "available": True, "truncated": False}


def report(database: Path = DATA_PATH, logs: Path | None = None, dataset: Path | None = None) -> dict:
    root = Path(__file__).resolve().parents[2]
    filesystem = database.parent
    while not filesystem.exists():
        filesystem = filesystem.parent
    usage = shutil.disk_usage(filesystem)
    db_files = {str(path.name): path.stat().st_size if path.is_file() else 0
                for path in (database, Path(str(database) + "-wal"), Path(str(database) + "-shm"))}
    return {"database_bytes": db_files, "logs": tree_size(logs) if logs else {"status": "NOT_CONFIGURED"},
            "dataset": tree_size(dataset or root / "ai" / "datasets"),
            "free_disk_bytes": usage.free, "total_disk_bytes": usage.total,
            "deleted": False, "note": "Dataset growth is explicit opt-in; journald/tmp retention is an OS policy."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DATA_PATH)
    parser.add_argument("--logs", type=Path)
    parser.add_argument("--dataset", type=Path)
    args = parser.parse_args()
    print(json.dumps(report(args.database, args.logs, args.dataset), indent=2))
