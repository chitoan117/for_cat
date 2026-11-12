"""New real-board/capture/deploy contracts tested with fake I/O only."""
import ast
import csv
import hashlib
import json
from pathlib import Path

import pytest

from app.camera.settings import CaptureSettings
from app.camera.usb_webcam import UsbWebcamCameraProvider
from app.config import HardwareConfig
from bringup import protocol
from bringup.flash import plan as flash_plan
from bringup.serial_probe import probe
from ai.session import SessionManifest

ROOT=Path(__file__).resolve().parents[2]


def test_measured_camera_preferences_fourcc_before_size_and_passive_import():
    calls=[]
    class Capture:
        def isOpened(self): return True
        def set(self,key,value): calls.append((key,value)); return False
        def get(self,key): return {3:1280,4:720,5:30,6:1196444237}.get(key,0)
        def release(self): pass
    camera=UsbWebcamCameraProvider("/dev/fake",lambda device,backend:Capture(),CaptureSettings(backend="V4L2"))
    assert camera.health()=="NOT_CONNECTED" and calls==[]
    assert camera.open()
    assert [key for key,value in calls[:4]]==[6,3,4,5]
    assert (camera.settings.width,camera.settings.height,camera.settings.fps,camera.settings.fourcc)==(1280,720,30,"MJPG")
    assert camera.actual["width"]==1280 and camera.actual["fourcc_code"]==1196444237
    assert not camera.timeout_supported
    camera.close()
    assert HardwareConfig.from_env({}).ai_shadow_mode is True


def test_camera_reopen_budget_and_backoff_require_explicit_reset(monkeypatch):
    now=[0.0]; calls=[]
    monkeypatch.setattr("app.camera.usb_webcam.time.monotonic",lambda:now[0])
    class Capture:
        def isOpened(self): return False
        def release(self): pass
    def factory(device): calls.append(device); return Capture()
    camera=UsbWebcamCameraProvider("fake",factory)
    assert camera.read() is None and len(calls)==1
    now[0]=0.5; assert camera.read() is None and len(calls)==1
    now[0]=1; camera.read(); now[0]=2; camera.read()
    assert len(calls)==3 and camera.health()=="FAULT"
    now[0]=100
    for _ in range(20): camera.read()
    assert len(calls)==3
    camera.reset_reconnect(); camera.read(); assert len(calls)==4


def test_python36_bringup_matches_all_frozen_golden_vectors():
    with (ROOT/"docs/UART_V1_GOLDEN_VECTORS.csv").open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream))
    for row in rows:
        raw=bytes.fromhex(row["frame_hex"])
        decoded=protocol.decode(raw)
        assert protocol.encode(decoded["request_id"],decoded["command"],bytes.fromhex(decoded["payload_hex"]))==raw
        assert decoded["crc_received"]==decoded["crc_calculated"]
    assert len(rows)==7


def test_bringup_probe_stale_reply_raw_receipt_and_never_feed():
    class Port:
        data=b""; commands=[]
        def write(self,raw):
            frame=protocol.decode(raw); self.commands.append(frame["command"])
            response=protocol.ACK if frame["command"]==protocol.PING else protocol.SYSTEM_STATUS
            self.data=protocol.encode(99,response,b"\x01")+protocol.encode(frame["request_id"],response,b"\x01")
            return len(raw)
        def read(self,count): result=self.data[:count]; self.data=self.data[count:]; return result
    port=Port(); result=probe(port,count=1,sleep=lambda _:None)
    assert port.commands==[1,2] and result["feed_requests_sent"]==0
    assert result["result"]=="PASS" and all(r["rx_hex"] and r["request_correlated"] and r["crc_match"] for r in result["records"])
    assert [r["request_id"] for r in result["records"]]==[100,101]


def test_flash_dry_plan_no_stub_hash_profile_offset_and_no_erase_all(tmp_path):
    image=tmp_path/"firmware.factory.bin"; image.write_bytes(b"\xe9SYNTHETIC_HASH_ONLY_NOT_FIRMWARE")
    sha=hashlib.sha256(image.read_bytes()).hexdigest()
    result=flash_plan(image,sha,"diag_i2c","/dev/ttyACM0")
    assert all("--no-stub" in cmd for cmd in result["commands"])
    assert result["commands"][1][-2]=="0x0" and not result["erase_all"]
    assert not any("erase_flash" in cmd for cmd in result["commands"])
    for profile,hash_value in (("esp32s3_n16r8_sim",sha),("diag_i2c","0"*64)):
        with pytest.raises(ValueError): flash_plan(image,hash_value,profile,"/dev/ttyACM0")
    app=tmp_path/"firmware.bin"; app.write_bytes(image.read_bytes())
    assert flash_plan(app,sha,"diag_rtc","/dev/ttyACM0",True)["commands"][1][-2]=="0x10000"


def test_portable_bringup_python36_grammar_and_no_modern_app_import():
    files=list((ROOT/"jetson/bringup").glob("*.py"))+[ROOT/"ai/sampling.py",ROOT/"ai/label_schema.py"]
    for path in files:
        source=path.read_text(encoding="utf-8")
        tree=ast.parse(source,feature_version=(3,6))
        assert not any(isinstance(node,ast.NamedExpr) for node in ast.walk(tree))
        assert "from app." not in source and "import app." not in source
    # Host grammar audit, not a claim that a Python3.6 interpreter was executed here.


def test_portable_capture_dry_run_and_canonical_manifest_bridge(tmp_path,monkeypatch):
    from bringup.camera import run,acquire
    import cv2
    import numpy as np
    options=dict(device="fake",width=32,height=32,fps=10,fourcc="MJPG",seconds=5,frames=3,interval=0.1,
        minimum_spacing=0,session_id="synthetic",identity="OWNER_CAT",behavior="EATING")
    assert run(options,tmp_path/"captures",False)["camera_opened"] is False
    assert not (tmp_path/"captures").exists()
    values=[0.0]
    def clock(): values[0]+=0.1; return values[0]
    class Capture:
        index=0; released=False
        def isOpened(self): return True
        def set(self,*args): return False
        def get(self,key): return {cv2.CAP_PROP_FPS:10,cv2.CAP_PROP_FOURCC:cv2.VideoWriter_fourcc(*"MJPG")}.get(key,0)
        def read(self): self.index+=1; return True,np.full((32,32,3),self.index*30,dtype=np.uint8)
        def release(self): self.released=True
    cap=Capture(); folder=tmp_path/"stage"; folder.mkdir()
    result=acquire(options,folder,factory=lambda *args:cap,clock=clock)
    assert result["samples"]==3 and cap.released
    meta=SessionManifest.model_validate(json.loads((folder/"session.json").read_text()))
    assert meta.session_id=="synthetic" and meta.capture_fourcc=="MJPG" and not meta.usable
    rows=[json.loads(line) for line in (folder/"manifest.jsonl").read_text().splitlines()]
    assert all(r["identity_label"] is None and r["behavior_label"] is None and not r["usable"] for r in rows)


def test_public_provenance_is_offline_bootstrap_not_owner_or_final_test():
    from ai.public_data import validate_provenance
    record=dict(schema_version=1,dataset_id="synthetic_validation_record",publisher="FIXTURE_ONLY",version="fixture",
        source_url="https://example.org/source",license_name="FIXTURE_NOT_ACTUAL_LICENSE",license_url="https://example.org/license",
        accessed_at="2026-10-08T00:00:00+00:00",source_grouping="original_video_id",license_reviewed=True,
        use_for_final_test=False,label_mapping={"cat":"OTHER_CAT"})
    result=validate_provenance(record)
    assert not result["errors"] and result["downloaded"] is False and not result["production_accuracy_claim_allowed"]
    for change in ({"label_mapping":{"cat":"OWNER_CAT"}},{"license_reviewed":False},{"use_for_final_test":True},{"source_grouping":None}):
        assert validate_provenance({**record,**change})["status"]=="REJECTED"
