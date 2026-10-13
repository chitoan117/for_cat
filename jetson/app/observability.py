"""JSON log lines with bounded operational fields, no frame or payload bytes."""

import json
import logging
import sys
import time
from collections import OrderedDict
from threading import RLock
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "severity": record.levelname,
            "component": getattr(record, "component", "jetson"),
            "request_id": getattr(record, "request_id", None),
            "session_id": getattr(record, "session_id", None),
            "event_type": getattr(record, "event_type", None),
            "message": record.getMessage()[:256],
        }, separators=(",", ":"))


def get_logger() -> logging.Logger:
    logger = logging.getLogger("forr_cat")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


class WarningLimiter:
    def __init__(self, interval: float = 30, max_keys: int = 32, clock=time.monotonic):
        self.interval, self.max_keys, self.clock = interval, max_keys, clock
        self.entries = OrderedDict()
        self.lock = RLock()

    def warn(self, logger, key: str, message: str, extra: dict) -> bool:
        with self.lock:
            now = self.clock()
            last, suppressed = self.entries.get(key, (float("-inf"), 0))
            emit = now - last >= self.interval
            self.entries[key] = (now if emit else last, 0 if emit else suppressed + 1)
            self.entries.move_to_end(key)
            while len(self.entries) > self.max_keys:
                self.entries.popitem(last=False)
            if emit:
                logger.warning(message + (f" (suppressed {suppressed} repeats)" if suppressed else ""), extra=extra)
            return emit
