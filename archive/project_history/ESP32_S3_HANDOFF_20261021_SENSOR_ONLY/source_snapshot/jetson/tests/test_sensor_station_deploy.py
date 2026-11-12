import hashlib

import pytest

from bringup.flash import REAL_ENVS, plan


def test_sensor_station_factory_plan_keeps_explicit_no_stub_and_verify(tmp_path):
    image = tmp_path / "firmware.factory.bin"
    image.write_bytes(b"\xe9FAKE_HOST_PLAN_ONLY")
    checksum = hashlib.sha256(image.read_bytes()).hexdigest()
    data = plan(image, checksum, "diag_all_sensors", "/dev/ttyACM0")
    assert "diag_all_sensors" in REAL_ENVS
    assert data["erase_all"] is False and data["commands"][1][-2] == "0x0"
    assert all("--no-stub" in command for command in data["commands"])
    assert data["commands"][2][-3] == "verify_flash"
    # No port must exist or be opened to construct this dry-run plan.


def test_sensor_station_application_plan_preserves_offset_and_rejects_bad_hash(tmp_path):
    image = tmp_path / "firmware.bin"
    image.write_bytes(b"\xe9FAKE_HOST_PLAN_ONLY")
    checksum = hashlib.sha256(image.read_bytes()).hexdigest()
    data = plan(image, checksum, "diag_all_sensors", "/dev/ttyUSB0", application_only=True)
    assert data["application_only"] is True and data["commands"][1][-2] == "0x10000"
    with pytest.raises(ValueError):
        plan(image, "0" * 64, "diag_all_sensors", "/dev/ttyUSB0", application_only=True)


def test_simulated_and_surrogate_deploys_remain_prohibited(tmp_path):
    image = tmp_path / "firmware.factory.bin"
    image.write_bytes(b"\xe9FAKE_HOST_PLAN_ONLY")
    checksum = hashlib.sha256(image.read_bytes()).hexdigest()
    for profile in ("esp32s3_n16r8_sim", "diag_rtc_surrogate", "unknown"):
        with pytest.raises(ValueError):
            plan(image, checksum, profile, "/dev/ttyACM0")
