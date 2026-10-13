"""File-backed *simulation* of safety counter restoration, NOT ESP32 NVS testing."""

import json
import math
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from app.simulator.controller import DailyState


class SimulationSafetyStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> DailyState | None:
        if not self.path.exists():
            return DailyState()
        try:
            if self.path.stat().st_size > 1024:
                return None
            row = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(row, dict) or set(row) != set(DailyState.__dataclass_fields__):
                return None
            value = DailyState(**row)
            if (type(value.revision) is not int or value.revision != 1 or
                    type(value.portions) is not int or value.portions < 0 or
                    type(value.date_key) is not int or value.date_key < 0 or
                    type(value.last_feed_epoch) is not int or value.last_feed_epoch < 0 or
                    type(value.grams) not in (float, int) or
                    not math.isfinite(value.grams) or value.grams < 0 or
                    type(value.needs_inspection) is not bool or
                    value.date_key == 0 and (value.portions or value.grams)):
                return None
            return value
        except (ValueError, TypeError, OSError, UnicodeError):
            return None  # caller stays in SAFE_BOOT on invalid persistence

    def save(self, value: DailyState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix="safety-", suffix=".tmp", delete=False) as stream:
                temp = Path(stream.name)
                json.dump(asdict(value), stream, allow_nan=False)
            os.replace(temp, self.path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
