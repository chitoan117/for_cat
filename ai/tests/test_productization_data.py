"""Synthetic/video fixtures ONLY; no camera or real cat data is used."""
import hashlib
import json
from pathlib import Path
from threading import Event

import pytest

from ai.artifacts import relative_file
from ai.capture import capture,plan,_record
from ai.dataset import load_manifest,report,validate_row
from ai.interchange import export,import_export
from ai.releases import acceptance,create_release,ingest_sessions,leakage
from ai.sampling import SamplingPolicy
from ai.session import SessionManifest


def image_dataset(root, count=3):
    from PIL import Image
    root.mkdir(exist_ok=True); (root/"processed").mkdir(exist_ok=True)
    rows=[]
    for i in range(count):
        path=root/"processed"/f"{i}.png"
        Image.new("RGB",(16,16),(i*50,30,100)).save(path)
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(dict(sample_id=f"s-{i}",session_id=f"session-{i}",source_video="",timestamp=None,
            identity_label="OWNER_CAT",behavior_label="EATING",usable=True,hash=sha,source_hash=sha,path=f"processed/{i}.png"))
    (root/"manifest.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows),encoding="utf-8")
    splits={"train":["session-0"],"validation":["session-1"],"test":["session-2"]}
    (root/"splits.json").write_text(json.dumps(splits),encoding="utf-8")
    return rows,splits


def video(path):
    cv2=pytest.importorskip("cv2"); np=pytest.importorskip("numpy")
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),10,(32,32))
    assert writer.isOpened()
    for i in range(10): writer.write(np.full((32,32,3),i*20,dtype=np.uint8))
    writer.release()


def test_dry_run_never_opens_camera_or_writes(tmp_path):
    meta=plan("camera:0","future_session","OWNER_CAT","EATING",lighting="daylight")
    result=capture(meta,tmp_path/"output")
    assert result["status"]=="DRY_RUN" and result["camera_opened"] is False
    assert not (tmp_path/"output").exists() and meta.source_hash is None and not meta.usable


@pytest.mark.parametrize("change",[{"session_id":"../escape"},{"duration_seconds":0},{"max_frames":1001},
    {"recorded_at":"2026-10-03T12:00:00"},{"fps":float("nan")},{"schema_version":2},{"resolution":[9000,9000]}])
def test_session_schema_rejects_invalid(change):
    payload=plan("camera:0","session","OWNER_CAT","EATING").model_dump(mode="json")
    with pytest.raises(ValueError): SessionManifest.model_validate({**payload,**change})


def test_sampling_spacing_exact_duplicates_and_near_warning():
    p=SamplingPolicy(0.1,0.5)
    assert p.select(0,b"a",0)
    assert p.select(0.1,b"b",0) is None
    assert p.select(0.5,b"a",0) is None and p.duplicates==1
    assert p.select(1,b"b",0) and p.near_warnings==1
    with pytest.raises(ValueError): p.select(0.2,b"x")


def test_capture_video_spawn_commit_unannotated_no_overwrite(tmp_path):
    path=tmp_path/"synthetic.avi"; video(path)
    meta=plan(str(path),"synthetic_session","OWNER_CAT","EATING",duration=1,interval=0.2,minimum_spacing=0,max_frames=4)
    result=capture(meta,tmp_path/"captures",apply=True)
    root=Path(result["session_path"]); rows,errors=load_manifest(root)
    assert result["samples"]==4 and not errors and result["hardware_verified"] is False
    assert all(r["identity_label"] is None and r["behavior_label"] is None and not r["usable"] for r in rows)
    assert [r["source_offset_seconds"] for r in rows]==pytest.approx([0,0.2,0.4,0.6])
    recorded=SessionManifest.model_validate_json((root/"session.json").read_text())
    assert recorded.sample_count==4 and recorded.resolution==(32,32) and recorded.source_hash==meta.source_hash
    with pytest.raises(FileExistsError): capture(meta,tmp_path/"captures",apply=True)


def test_capture_explicit_graceful_stop_and_ingestion(tmp_path):
    path=tmp_path/"synthetic.avi"; video(path)
    root=tmp_path/"session"; root.mkdir()
    stop=Event(); stop.set()
    meta=plan(str(path),"synthetic","OWNER_CAT","EATING")
    assert _record(meta,root,stop)["stop_reason"]=="USER_STOP"
    assert not load_manifest(root)[0]
    # A second explicit, finite session exercises the real fixture decoder.
    other=tmp_path/"other"; other.mkdir()
    meta=plan(str(path),"synthetic","OWNER_CAT","EATING",interval=0.1,minimum_spacing=0,max_frames=3)
    _record(meta,other,Event())
    assert ingest_sessions([other],tmp_path/"dataset")["status"]=="DRY_RUN"
    assert not (tmp_path/"dataset").exists()
    assert ingest_sessions([other],tmp_path/"dataset",apply=True)["samples"]==3
    assert not load_manifest(tmp_path/"dataset")[1]


def test_leakage_reports_session_source_exact_and_near(tmp_path):
    rows,splits=image_dataset(tmp_path)
    rows[1]["source_hash"]=rows[0]["source_hash"]
    rows[2]["hash"]=rows[0]["hash"]
    splits["validation"].append("session-0")
    found=leakage(tmp_path,rows,splits)
    assert {r["code"] for r in found["failures"]}>={"SESSION_LEAKAGE","SOURCE_LEAKAGE","EXACT_DUPLICATE_LEAKAGE"}
    assert found["near_duplicates"]
    assert leakage(tmp_path,rows,splits,near_limit=1)["near_check_truncated"]


def test_release_gates_missing_classes_and_source_leakage(tmp_path):
    rows,splits=image_dataset(tmp_path)
    assert acceptance(tmp_path)["status"]=="PILOT_DATASET"
    candidate=acceptance(tmp_path,stage="TRAINING_CANDIDATE")
    assert candidate["status"]=="REJECTED" and candidate["usable_rate"]==1
    release=create_release(tmp_path,"pilot_v1",tmp_path/"releases",apply=True)
    assert release["sample_count"]==3 and release["source_hashes"] and release["manifest_hash"]
    with pytest.raises(FileExistsError): create_release(tmp_path,"pilot_v1",tmp_path/"releases",apply=True)
    rows[1]["source_hash"]=rows[0]["source_hash"]
    (tmp_path/"manifest.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows))
    assert report(tmp_path)["status"]=="DATASET_INVALID"
    assert acceptance(tmp_path)["status"]=="REJECTED"


def test_local_classification_round_trip_and_missing_session(tmp_path):
    root=tmp_path/"dataset"; rows,_=image_dataset(root)
    bundle=tmp_path/"bundle"; output=tmp_path/"returned"
    assert export(root,bundle)["status"]=="DRY_RUN" and not bundle.exists()
    assert export(root,bundle,apply=True)["uploaded"] is False
    assert import_export(bundle,output,apply=True)["split_allowed"] is False
    returned,_=load_manifest(output)
    assert [r["session_id"] for r in returned]==[r["session_id"] for r in rows]
    assert import_export(tmp_path,tmp_path/"untrusted")["status"]=="SESSION_METADATA_MISSING"
    meta=json.loads((bundle/"provenance.json").read_text())
    (bundle/"labels.json").write_text(json.dumps({meta["samples"][0]["export_path"]:"OTHER_CAT"}))
    annotated=tmp_path/"annotated"; import_export(bundle,annotated,apply=True)
    assert load_manifest(annotated)[0][0]["identity_label"]=="OTHER_CAT"
    del meta["samples"][0]["local_row"]["session_id"]
    (bundle/"provenance.json").write_text(json.dumps(meta))
    assert import_export(bundle,tmp_path/"missing")["status"]=="SESSION_METADATA_MISSING"


@pytest.mark.parametrize("name",["../outside.onnx","C:/outside.onnx","a\\b.png","/outside.png"])
def test_dataset_and_artifact_paths_reject_traversal(tmp_path,name):
    with pytest.raises(ValueError): relative_file(tmp_path,name)
    row=dict(sample_id="s",session_id="session",source_video="",timestamp=None,identity_label="UNKNOWN",
        behavior_label="UNSURE",usable=False,hash="0"*64,source_hash="1"*64,path=name)
    assert validate_row(row)


def test_interval_extraction_deterministic(tmp_path):
    from ai.scripts.extract_frames import extract
    raw=tmp_path/"raw"; raw.mkdir(); video(raw/"fixture.avi")
    one=extract("fixture.avi","synthetic",tmp_path,interval_seconds=0.2,minimum_spacing=0.3,max_frames=10)
    two=extract("fixture.avi","synthetic",tmp_path,interval_seconds=0.2,minimum_spacing=0.3,max_frames=10)
    assert one==two and one["frames"]==4 and not (tmp_path/"manifest.jsonl").exists()


@pytest.mark.parametrize("payload",[[],{"schema_version":1,"samples":["not-an-object"]},
    {"schema_version":1,"task":"identity","samples":[{"local_row":[]}]}])
def test_malformed_returned_provenance_rejected_without_import(tmp_path,payload):
    (tmp_path/"provenance.json").write_text(json.dumps(payload))
    with pytest.raises(ValueError): import_export(tmp_path,tmp_path/"output",apply=True)
    assert not (tmp_path/"output").exists()
