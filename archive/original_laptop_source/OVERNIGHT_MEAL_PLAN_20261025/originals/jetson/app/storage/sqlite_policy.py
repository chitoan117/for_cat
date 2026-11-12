"""Local embedded SQLite policy; not a promise of SD-card/power-loss durability."""

import sqlite3
from pathlib import Path


def connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=2, check_same_thread=False)
    connection.execute("PRAGMA busy_timeout=2000")
    connection.execute("PRAGMA foreign_keys=ON")
    if str(path) != ":memory:":
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA wal_autocheckpoint=100")
        connection.execute("PRAGMA journal_size_limit=4194304")
    return connection


def database_health(connection: sqlite3.Connection) -> str:
    try:
        connection.execute("SELECT 1").fetchone()
        return "READY"
    except sqlite3.Error:
        return "NOT_AVAILABLE"
