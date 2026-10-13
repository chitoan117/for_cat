from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class NormalizedBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self):
        if not all(isfinite(x) and 0 <= x <= 1 for x in (self.x1, self.y1, self.x2, self.y2)) or \
                self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("box/ROI coordinates must be normalized with positive area")

    def contains_center(self, box: "NormalizedBox") -> bool:
        return self.x1 <= (box.x1 + box.x2) / 2 <= self.x2 and \
               self.y1 <= (box.y1 + box.y2) / 2 <= self.y2

    def overlaps(self, box: "NormalizedBox") -> bool:
        return min(self.x2, box.x2) > max(self.x1, box.x1) and min(self.y2, box.y2) > max(self.y1, box.y1)

    @classmethod
    def parse(cls, text: str | None) -> "NormalizedBox | None":
        if not text:
            return None
        values = tuple(float(x) for x in text.split(","))
        if len(values) != 4:
            raise ValueError("ROI requires x1,y1,x2,y2")
        return cls(*values)
