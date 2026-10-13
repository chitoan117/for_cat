"""Local image-classification export with mandatory provenance sidecar. No uploads."""
import json
import shutil
import tempfile
from pathlib import Path

from ai.artifacts import read_json, relative_file, write_json
from ai.dataset import digest, image_integrity, load_manifest, validate_row, IDENTITY_LABELS, BEHAVIOR_LABELS


def export(root, output, *, task="identity", apply=False):
    if task not in ("identity", "behavior"):
        raise ValueError("classification task required")
    rows, errors = load_manifest(Path(root))
    if errors or not rows:
        raise ValueError("valid nonempty local manifest required")
    if Path(output).exists():
        raise FileExistsError("no export overwrite")
    selected = [r for r in rows if r["usable"] and r[f"{task}_label"] not in (None,"SKIP","UNSURE","UNKNOWN")]
    if not selected:
        raise ValueError("no usable annotated classification samples")
    sidecar = {"schema_version": 1, "task": task, "format": "CLASSIFICATION_FOLDERS_WITH_PROVENANCE", "samples": []}
    for row in selected:
        source = relative_file(Path(root),row["path"])
        if image_integrity(source)!="OK" or digest(source)!=row["hash"]:
            raise ValueError("sample integrity failure")
        path = f"images/{row[f'{task}_label']}/{row['sample_id']}{source.suffix.lower()}"
        sidecar["samples"].append({"export_path": path, "local_row": row})
    if apply:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".export-",dir=Path(output).parent))
        try:
            for item in sidecar["samples"]:
                target = stage/item["export_path"]; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(relative_file(Path(root),item["local_row"]["path"]),target)
            write_json(stage/"provenance.json",sidecar)
            stage.rename(output)
        finally:
            if stage.exists(): shutil.rmtree(stage)
    return {"status": "EXPORTED" if apply else "DRY_RUN", "samples": len(selected), "uploaded": False}


def import_export(source, output, *, apply=False):
    source, output = Path(source), Path(output)
    if not (source/"provenance.json").is_file():
        return {"status": "SESSION_METADATA_MISSING", "split_allowed": False}
    sidecar = read_json(source/"provenance.json")
    if not isinstance(sidecar,dict) or sidecar.get("schema_version")!=1 or not isinstance(sidecar.get("samples"),list) or not sidecar["samples"] or len(sidecar["samples"])>10000:
        raise ValueError("invalid provenance sidecar")
    if output.exists(): raise FileExistsError("no import overwrite")
    overrides=read_json(source/"labels.json") if (source/"labels.json").exists() else {}
    if not isinstance(overrides,dict) or sidecar.get("task") not in ("identity","behavior"):
        raise ValueError("invalid optional classification annotations")
    rows, files, seen = [], [], set()
    for item in sidecar["samples"]:
        if not isinstance(item,dict) or not isinstance(item.get("local_row"),dict):
            raise ValueError("invalid provenance sample object")
        row = item.get("local_row", {})
        if not row.get("session_id"):
            return {"status": "SESSION_METADATA_MISSING", "split_allowed": False}
        if validate_row(row) or row["sample_id"] in seen:
            raise ValueError("invalid/duplicate local row")
        exported = item.get("export_path")
        if not isinstance(exported, str):
            raise ValueError("PROVENANCE_INVALID: missing export_path")
        parts = Path(exported).parts
        if len(parts) != 3 or parts[0] != "images" or parts[1] != row[f"{sidecar['task']}_label"]:
            raise ValueError("PROVENANCE_INVALID: inconsistent task/folder label mapping")
        path = relative_file(source,exported)
        if image_integrity(path)!="OK" or digest(path)!=row["hash"]:
            raise ValueError("changed/re-encoded image needs human provenance reconciliation")
        if item["export_path"] in overrides:
            label=overrides[item["export_path"]]
            allowed=IDENTITY_LABELS if sidecar["task"]=="identity" else BEHAVIOR_LABELS
            if not isinstance(label,str) or label not in allowed:
                raise ValueError("invalid returned annotation label")
            row={**row, f"{sidecar['task']}_label":label,
                 "usable":row["usable"] and label not in ("UNKNOWN","UNSURE","SKIP")}
        seen.add(row["sample_id"])
        rows.append({**row,"path": f"processed/{row['sample_id']}{path.suffix.lower()}"}); files.append(path)
    if apply:
        output.parent.mkdir(parents=True,exist_ok=True)
        stage=Path(tempfile.mkdtemp(prefix=".import-",dir=output.parent))
        try:
            (stage/"processed").mkdir()
            for row,path in zip(rows,files): shutil.copyfile(path,stage/row["path"])
            (stage/"manifest.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows),encoding="utf-8")
            stage.rename(output)
        finally:
            if stage.exists(): shutil.rmtree(stage)
    return {"status": "IMPORTED_REQUIRES_SPLIT_VALIDATION" if apply else "DRY_RUN", "samples": len(rows), "split_allowed": False}
