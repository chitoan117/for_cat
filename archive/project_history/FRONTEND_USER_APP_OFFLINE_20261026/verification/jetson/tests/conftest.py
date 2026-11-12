"""Non-Linux identity fixture only; production boot identity stays untouched."""
import sys
import pytest

@pytest.fixture(autouse=True)
def isolated_windows_boot_identity(monkeypatch):
    if sys.platform != 'win32':return
    from app import device_state,ai_state
    if device_state.read_host_boot_id() is None:
        monkeypatch.setattr(device_state,'read_host_boot_id',lambda:'synthetic-offline-boot')
        monkeypatch.setattr(ai_state,'read_host_boot_id',lambda:'synthetic-offline-boot')
