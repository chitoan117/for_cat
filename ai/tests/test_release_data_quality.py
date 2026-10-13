"""Malformed/provenance/security cases with temporary SYNTHETIC fixtures only."""
import hashlib
import json
import random
from pathlib import Path

import pytest

from ai.artifacts import read_json, relative_file, write_json
from ai.capture import plan
from ai.dataset import load_manifest, report, split_sessions, validate_row, validate_splits
from ai.experiments import register_model
from ai.interchange import export, import_export
from ai.releases import ingest_sessions
from ai.session import SessionManifest
from ai.tests.test_productization_data import image_dataset


def test_seeded_metadata_and_session_fuzz_fail_clearly(tmp_path):
    rng=random.Random(77191)
    valid=dict(sample_id="s",session_id="source",source_video="",timestamp=None,identity_label="UNKNOWN",
        behavior_label="UNSURE",usable=False,hash="a"*64,source_hash="b"*64,path="processed/a.png")
    for _ in range(600):
        row={**valid,rng.choice(list(valid)):rng.choice([[],{},None,True,-1,"../bad","x"*1024])}
        assert isinstance(validate_row(row),list)
        sessions=[{**valid,"session_id":f"session_{rng.randrange(20)}","usable":True} for _ in range(rng.randrange(1,40))]
        first=split_sessions(sessions,42)
        assert first==split_sessions(list(reversed(sessions)),42) and not validate_splits(first)
    manifest=plan("camera:0","future","UNKNOWN","UNSURE").model_dump(mode="json")
    for field,value in (("schema_version",2),("session_id","../bad"),("notes","x"*513),("duration_seconds",float("nan"))):
        with pytest.raises(ValueError): SessionManifest.model_validate({**manifest,field:value})
    with pytest.raises(ValueError): relative_file(tmp_path,"../outside")
    (tmp_path/"nested.json").write_text("["*2000+"0"+"]"*2000)
    with pytest.raises(ValueError): read_json(tmp_path/"nested.json")


@pytest.mark.parametrize("kind",["empty","directory","corrupt","missing","duplicate_id","bad_json","unsupported_field"])
def test_dataset_chaos_reports_without_guessing(kind,tmp_path):
    if kind=="empty":
        assert report(tmp_path)["status"]=="DATASET_NOT_AVAILABLE"; return
    if kind=="directory":
        (tmp_path/"manifest.jsonl").mkdir(); assert load_manifest(tmp_path)[1]; return
    rows,_=image_dataset(tmp_path)
    if kind=="corrupt": (tmp_path/rows[0]["path"]).write_bytes(b"SYNTHETIC_CORRUPT")
    if kind=="missing": (tmp_path/rows[0]["path"]).unlink()
    if kind=="duplicate_id": rows[1]["sample_id"]=rows[0]["sample_id"]
    if kind=="unsupported_field": rows[0]["schema_version"]=999
    if kind in ("duplicate_id","unsupported_field"):
        (tmp_path/"manifest.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
    if kind=="bad_json": (tmp_path/"manifest.jsonl").write_text("{"*10000)
    assert report(tmp_path)["status"]=="DATASET_INVALID"


@pytest.mark.parametrize("problem",["session","source","label","schema","export_path"])
def test_interchange_provenance_is_required(problem,tmp_path):
    root=tmp_path/"dataset"; image_dataset(root); bundle=tmp_path/"export"
    export(root,bundle,apply=True)
    metadata=json.loads((bundle/"provenance.json").read_text())
    row=metadata["samples"][0]["local_row"]
    if problem=="session": row.pop("session_id")
    if problem=="source": row.pop("source_hash")
    if problem=="label": row["identity_label"]="OTHER_CAT"
    if problem=="schema": metadata["schema_version"]=999
    if problem=="export_path": metadata["samples"][0].pop("export_path")
    (bundle/"provenance.json").write_text(json.dumps(metadata))
    output=tmp_path/"return"
    if problem=="session": assert import_export(bundle,output,apply=True)["status"]=="SESSION_METADATA_MISSING"
    else:
        with pytest.raises(ValueError): import_export(bundle,output,apply=True)
    assert not output.exists()


def test_staging_cleanup_and_colliding_source_basenames(tmp_path,monkeypatch):
    from PIL import Image
    folder=tmp_path/"session"; folder.mkdir(); rows=[]
    for i,name in enumerate(("one","two")):
        path=folder/name/"same.png"; path.parent.mkdir()
        Image.new("RGB",(8,8),(i*80,20,30)).save(path)
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(dict(sample_id=f"s-{i}",session_id="session",source_video="",timestamp=None,identity_label=None,
            behavior_label=None,usable=False,hash=sha,source_hash="a"*64,path=f"{name}/same.png"))
    manifest=plan("camera:0","session","UNKNOWN","UNSURE").model_copy(update={"source_hash":"a"*64,"sample_count":2})
    (folder/"session.json").write_text(manifest.model_dump_json())
    (folder/"manifest.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
    destination=tmp_path/"ingested"; ingest_sessions([folder],destination,apply=True)
    assert report(destination)["status"]=="DATASET_AVAILABLE"
    new_rows,_=load_manifest(destination); assert len({r["path"] for r in new_rows})==2
    def fail(*args): raise OSError("synthetic copy failure")
    monkeypatch.setattr("ai.releases.shutil.copyfile",fail)
    with pytest.raises(OSError): ingest_sessions([folder],tmp_path/"failed",apply=True)
    assert not (tmp_path/"failed").exists() and not list(tmp_path.glob(".ingest-*"))


@pytest.mark.parametrize("mutation",["missing","directory","runtime","task","label","validated","activation"])
def test_model_metadata_cannot_activate_or_certify(mutation,tmp_path):
    path=tmp_path/"fixture.onnx"; path.write_bytes(b"SYNTHETIC_HASH_ONLY_NOT_A_MODEL")
    metadata=dict(model_id="fixture",task="identity",dataset_version="fixture",training_experiment="fixture",file=path.name,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),runtime="ONNX",input_shape=[1,3,224,224],
        label_map=["OWNER_CAT","OTHER_CAT","OTHER_OBJECT"],thresholds={})
    if mutation=="missing": path.unlink()
    if mutation=="directory": path.unlink(); path.mkdir()
    if mutation=="runtime": metadata["runtime"]="UNSUPPORTED"
    if mutation=="task": metadata["task"]="behavior"
    if mutation=="label": metadata["label_map"]=["UNKNOWN"]
    if mutation=="validated": metadata["validation_status"]="VALIDATED_JETSON"
    if mutation=="activation": metadata["activated"]=True
    with pytest.raises(ValueError): register_model(metadata,tmp_path,tmp_path/"registry",expected_task="identity",apply=True)
    assert not (tmp_path/"registry").exists()


def test_resolved_symlink_escape_is_rejected_without_read(monkeypatch,tmp_path):
    original=Path.resolve
    def resolve(path,*args,**kwargs):
        if path.name=="escape.onnx": return original(tmp_path.parent/"outside.onnx")
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"resolve",resolve)
    with pytest.raises(ValueError,match="symlink"): relative_file(tmp_path,"escape.onnx")
    # Deterministic simulated resolution; not an OS privilege/physical-file claim.


def test_failed_exclusive_metadata_write_does_not_leave_a_partial_registry(monkeypatch,tmp_path):
    path=tmp_path/"new.json"; original=Path.open
    class Failing:
        def __enter__(self):
            self.stream=original(path,"x",encoding="utf-8"); return self
        def write(self,content):
            self.stream.write(content[:3]); raise OSError("synthetic partial write")
        def __exit__(self,*args): self.stream.close()
    def opening(target,*args,**kwargs):
        return Failing() if target==path and args and args[0]=="x" else original(target,*args,**kwargs)
    monkeypatch.setattr(Path,"open",opening)
    with pytest.raises(OSError): write_json(path,{"schema_version":1})
    assert not path.exists()
