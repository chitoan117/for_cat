"""Deterministic temporal spacing, exact deduplication and optional dHash warnings."""
import hashlib
import math


def fingerprint(image) -> int:
    gray = image.convert("L").resize((9, 8))
    pixels = gray.tobytes()
    return sum((pixels[y*9+x] > pixels[y*9+x+1]) << (y*8+x)
               for y in range(8) for x in range(8))


class SamplingPolicy:
    def __init__(self, interval=1.0, minimum_spacing=0.5, near_distance=3):
        if any(not math.isfinite(x) for x in (interval, minimum_spacing)) or interval <= 0 or minimum_spacing < 0 or not 0 <= near_distance <= 16:
            raise ValueError("invalid sampling policy")
        self.spacing = max(interval, minimum_spacing)
        self.next_at = 0.0
        self.last_at = -1.0
        self.hashes = set()
        self.fingerprints = []
        self.near_distance = near_distance
        self.duplicates = self.near_warnings = 0

    def due(self, seconds):
        if not math.isfinite(seconds) or seconds < 0 or seconds < self.last_at:
            raise ValueError("sample clock must be finite and nondecreasing")
        self.last_at = seconds
        return seconds + 1e-9 >= self.next_at

    def select(self, seconds, data: bytes, perceptual=None):
        if not self.due(seconds):
            return None
        self.next_at = seconds + self.spacing
        sha = hashlib.sha256(data).hexdigest()
        if sha in self.hashes:
            self.duplicates += 1
            return None
        if len(self.hashes) >= 1000:
            raise ValueError("sampling frame budget exhausted")
        self.hashes.add(sha)
        if perceptual is not None:
            self.near_warnings += int(any((old ^ perceptual).bit_count() <= self.near_distance for old in self.fingerprints))
            self.fingerprints.append(perceptual)
        return sha
