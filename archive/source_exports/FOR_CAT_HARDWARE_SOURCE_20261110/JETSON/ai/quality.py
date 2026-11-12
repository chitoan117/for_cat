"""Offline quality flags, never automatic deletion or semantic labels."""
import math

from ai.sampling import fingerprint


def validate_quality(value):
    if not isinstance(value, dict):
        return ["quality must be an object"]
    allowed = {"blur_variance", "blur_threshold", "blur_warning", "brightness_mean", "dhash", "near_duplicate_warning"}
    errors = ["unknown quality field" for key in value if key not in allowed]
    for name in ("blur_variance", "blur_threshold", "brightness_mean"):
        if name in value and (type(value[name]) not in (int, float) or not math.isfinite(value[name]) or value[name] < 0):
            errors.append("invalid quality metric")
    for name in ("blur_warning", "near_duplicate_warning"):
        if name in value and type(value[name]) is not bool:
            errors.append("invalid quality flag")
    if "dhash" in value and (not isinstance(value["dhash"], str) or len(value["dhash"]) != 16 or any(char not in "0123456789abcdef" for char in value["dhash"])):
        errors.append("invalid dhash")
    return errors


def image_quality(image, blur_threshold=50):
    if not math.isfinite(blur_threshold) or blur_threshold < 0:
        raise ValueError("invalid blur threshold")
    import cv2
    import numpy as np

    gray = np.asarray(image.convert("L"))
    # Compare at a bounded common scale; the threshold is a heuristic, not calibrated truth.
    if max(gray.shape) > 640:
        scale = 640 / max(gray.shape)
        gray = cv2.resize(gray, (max(1, round(gray.shape[1]*scale)), max(1, round(gray.shape[0]*scale))))
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return {"blur_variance": variance, "blur_threshold": blur_threshold,
            "blur_warning": variance < blur_threshold, "brightness_mean": float(gray.mean()),
            "dhash": f"{fingerprint(image):016x}"}


def near_pairs(items, distance=3, comparison_limit=2_000_000, example_limit=100):
    """All-item exact dHash-radius candidate index; bounded work, explicit truncation.

    For <=3 changed bits at least one of four 16-bit bands is unchanged.
    A close pair is a REVIEW warning, not proof of leakage or duplicate identity.
    """
    if distance != 3 or not 1 <= comparison_limit <= 20_000_000:
        raise ValueError("invalid near-check policy")
    from collections import Counter, defaultdict
    grouped = defaultdict(list)
    for item in items:
        grouped[int(item["dhash"], 16)].append(item)
    buckets, previous = [{} for _ in range(4)], []
    comparisons = pairs = cross_split = 0
    examples, source_pairs = [], set()

    def accumulate(first, second, same=False):
        nonlocal pairs, cross_split
        pairs += len(first)*(len(first)-1)//2 if same else len(first)*len(second)
        left = Counter((item.get("split"), item.get("source_hash")) for item in first if item.get("split"))
        right = left if same else Counter((item.get("split"), item.get("source_hash")) for item in second if item.get("split"))
        cross = 0
        for (split_a, source_a), count_a in left.items():
            for (split_b, source_b), count_b in right.items():
                if split_a != split_b:
                    cross += count_a * count_b
                    source_pairs.add(tuple(sorted((source_a, source_b))))
        cross_split += cross//2 if same else cross
        if len(examples) < example_limit:
            representatives = {}
            for item in first + ([] if same else second):
                representatives.setdefault((item.get("split"), item.get("source_hash")), item)
            values = list(representatives.values())
            if len(values) >= 2:
                examples.append({"samples": [values[0]["sample_id"], values[1]["sample_id"]], "cross_split": bool(cross)})

    for value, members in grouped.items():
        if len(members) > 1:
            accumulate(members, members, True)
        candidates = set()
        for band, bucket in enumerate(buckets):
            candidates.update(bucket.get((value >> (band*16)) & 65535, ()))
        for index in sorted(candidates):
            if comparisons >= comparison_limit:
                return {"pairs": pairs, "cross_split_pairs": cross_split, "examples": examples,
                        "cross_source_pairs": sorted(source_pairs), "comparisons": comparisons,
                        "complete": False, "checked": sum(len(group) for _, group in previous)}
            comparisons += 1
            old_value, old_members = previous[index]
            if (value ^ old_value).bit_count() <= distance:
                accumulate(old_members, members)
        for band, bucket in enumerate(buckets):
            bucket.setdefault((value >> (band*16)) & 65535, []).append(len(previous))
        previous.append((value, members))
    return {"pairs": pairs, "cross_split_pairs": cross_split, "examples": examples,
            "cross_source_pairs": sorted(source_pairs), "comparisons": comparisons,
            "complete": True, "checked": len(items)}
