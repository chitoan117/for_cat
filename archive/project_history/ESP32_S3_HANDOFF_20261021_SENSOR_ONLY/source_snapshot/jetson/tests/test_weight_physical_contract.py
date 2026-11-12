import copy
import json
from pathlib import Path

import pytest

from bringup.hardware_report import record, template, validate
from bringup.weight_contract import consumption_evidence_available, validate_weight


def reading(value=None, installed=False, valid=False, stamp=None):
    return {"monotonic_ms": 1000, "observation_epoch": "SOFTWARE_FIXTURE_SESSION",
            "consumed_grams": None,
            "weight": {"installed": installed, "valid": valid, "quality": "VALID" if valid else "NOT_INSTALLED",
                       "value_grams": value, "sampled_at_ms": stamp, "calibration_version": 1,
                       "calibration_id": "hx-v1-abcd" if valid else None}}


def test_uninstalled_is_not_zero_and_never_consumption():
    data = reading()
    assert validate_weight(data)["value_grams"] is None
    assert not consumption_evidence_available(data, data)
    with pytest.raises(ValueError):
        validate_weight(reading(0))


def test_future_zero_validity_freshness_and_calibration_session_identity():
    first, last = reading(20, True, True, 900), reading(0, True, True, 1000)
    assert validate_weight(last)["value_grams"] == 0
    assert consumption_evidence_available(first, last)
    last["observation_epoch"] = "OTHER_BOOT"
    assert not consumption_evidence_available(first, last)
    last["observation_epoch"] = first["observation_epoch"]
    last["weight"]["calibration_id"] = "hx-v1-1234"
    assert not consumption_evidence_available(first, last)
    stale = reading(1, True, True, 0); stale["monotonic_ms"] = 3000
    with pytest.raises(ValueError):
        validate_weight(stale)


def test_physical_template_does_not_award_pass_and_installation_is_unconfirmed(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"files": [{"file": "firmware.bin", "sha256": "a" * 64}]}))
    root = Path(__file__).resolve().parents[2]
    data = template(root / "config/hardware_current.json", manifest)
    assert data["hx711_installed"] is None
    assert data["tests"]["hx711_load_cell"]["status"] == "NOT_TESTED"
    assert all(row["status"] in ("NOT_TESTED", "NOT_INSTALLED") for row in data["tests"].values())
    assert not data["physical_validation_automatically_awarded"]
    invalid = copy.deepcopy(data)
    invalid["tests"]["rtc"]["status"] = "PASS"
    with pytest.raises(ValueError):
        validate(invalid)
    with pytest.raises(ValueError):
        record(copy.deepcopy(data), "hx711_load_cell", "PASS", "operator", [])
    skipped = record(data, "rtc", "SKIPPED", "operator", [])
    assert skipped["tests"]["rtc"]["status"] == "SKIPPED"
