"""Versioned future weight evidence; never grants physical validation or grams consumed."""
import math
import re


def validate_weight(report):
    weight = report.get("weight")
    if not isinstance(weight, dict):
        raise ValueError("missing versioned weight")
    if type(weight.get("installed")) is not bool or type(weight.get("valid")) is not bool:
        raise ValueError("invalid weight availability flags")
    quality = weight.get("quality")
    if quality not in ("NOT_INSTALLED", "VALID", "NOT_CALIBRATED", "UNAVAILABLE", "STALE", "INVALID"):
        raise ValueError("invalid weight quality")
    value, stamp = weight.get("value_grams"), weight.get("sampled_at_ms")
    if not weight["installed"] and (weight["valid"] or quality != "NOT_INSTALLED"):
        raise ValueError("uninstalled sensor asserted validity")
    if weight["valid"]:
        if quality != "VALID" or type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100000:
            raise ValueError("invalid weight value")
        if type(stamp) is not int or not 0 <= stamp <= 0xffffffff:
            raise ValueError("invalid weight timestamp")
        age = (report["monotonic_ms"] - stamp) & 0xffffffff
        if age > 2000:
            raise ValueError("stale weight marked valid")
        if not isinstance(weight.get("calibration_id"), str) or not re.fullmatch(r"hx-v1-[0-9a-f]{4}", weight["calibration_id"]):
            raise ValueError("missing calibration fingerprint")
    elif value is not None or stamp is not None:
        raise ValueError("invalid/unavailable weight must be null")
    if type(weight.get("calibration_version")) is not int or weight["calibration_version"] != 1 or report.get("consumed_grams") is not None:
        raise ValueError("unsupported calibration or invented consumption")
    return weight


def consumption_evidence_available(before, after):
    """Precondition only. Existing stable/validated sensor fusion remains authoritative."""
    first, last = validate_weight(before), validate_weight(after)
    return bool(before.get("observation_epoch") and before.get("observation_epoch") == after.get("observation_epoch") and
                first["installed"] and last["installed"] and first["valid"] and last["valid"] and
                first["calibration_id"] == last["calibration_id"] and
                0 < ((last["sampled_at_ms"] - first["sampled_at_ms"]) & 0xffffffff) <= 3600000)
