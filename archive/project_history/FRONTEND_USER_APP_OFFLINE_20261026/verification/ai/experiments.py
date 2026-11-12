"""No training/runtime installation. Validated experiment bundles and inert model registry."""
import hashlib
import importlib.metadata
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai.artifacts import read_json, relative_file, write_json
from ai.dataset import digest
from ai.training import LABEL_MAPS


class Experiment(BaseModel):
    model_config=ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal[1]=1
    experiment_id: str=Field(pattern=r"^[a-z0-9_-]{1,64}$")
    dataset_version: str=Field(pattern=r"^[a-z0-9_-]{1,64}$")
    task: Literal["detector","identity","behavior"]
    architecture: str=Field(min_length=1,max_length=64)
    seed: int=Field(ge=0,le=2**32-1)
    input_size: tuple[int,int]
    epochs: int=Field(ge=1,le=10000)
    batch_size: int=Field(ge=1,le=1024)
    optimizer: Literal["Adam","AdamW","SGD"]
    learning_rate: float=Field(gt=0,le=1)
    augmentation: list[str]=Field(max_length=32)
    early_stopping: int=Field(ge=1,le=10000)
    class_weights: dict[str,float] | None=None
    thresholds: dict[str,float]=Field(default_factory=dict)

    @model_validator(mode="after")
    def semantics(self):
        labels=LABEL_MAPS.get(self.task,["CAT"])
        if any(not 16<=n<=4096 for n in self.input_size) or any(len(x)>64 for x in self.augmentation):
            raise ValueError("invalid input/augmentation")
        if self.class_weights is not None and (set(self.class_weights)!=set(labels) or any(not 0<x<=100 for x in self.class_weights.values())):
            raise ValueError("class weights must cover exact task label map")
        if any(key not in labels or not 0<=value<=1 for key,value in self.thresholds.items()):
            raise ValueError("invalid thresholds")
        return self


def candidates():
    entries=read_json(Path(__file__).parent/"registry"/"candidates.json")
    return entries["candidates"]


def source_version(root):
    root=Path(root).resolve()
    try:
        git=subprocess.run(["git","rev-parse","HEAD"],cwd=root,capture_output=True,text=True,timeout=5)
        revision=git.stdout.strip() if git.returncode==0 else None
        dirty=subprocess.run(["git","status","--porcelain"],cwd=root,capture_output=True,text=True,timeout=5).stdout.strip() if revision else None
    except (OSError,subprocess.TimeoutExpired):
        revision=dirty=None
    sha=hashlib.sha256(); count=0
    for directory in ("ai","jetson/app","esp32/include","esp32/src","scripts"):
        for path in sorted((root/directory).rglob("*")):
            if path.is_file() and path.suffix in (".py",".h",".cpp",".ps1",".sh") and "__pycache__" not in path.parts:
                sha.update(path.relative_to(root).as_posix().encode()); sha.update(bytes.fromhex(digest(path))); count+=1
    return {"git_revision": revision,"git_dirty": bool(dirty) if revision else None,"source_tree_sha256": sha.hexdigest(),"source_files": count}


def prepare_bundle(config, release, output, *, apply=False):
    experiment=Experiment.model_validate(config)
    registry={r["candidate_id"]: r for r in candidates()}
    candidate=registry.get(experiment.architecture)
    if candidate is None or candidate["task"]!=experiment.task:
        raise ValueError("architecture must match candidate/task registry")
    if not isinstance(release,dict) or release.get("dataset_version")!=experiment.dataset_version or release.get("validation_status") not in ("PILOT_DATASET","TRAINING_CANDIDATE","TEST_CANDIDATE") or not release.get("manifest_hash") or not isinstance(release.get("sample_count"),int) or release["sample_count"]<=0:
        raise ValueError("validated nonempty versioned dataset required")
    if release["validation_status"]=="TEST_CANDIDATE":
        raise ValueError("final test candidate cannot be a training experiment source")
    result={"schema_version":1,"status":"EXPERIMENT_PREPARED_NOT_TRAINED", "created_at":datetime.now(timezone.utc).isoformat(),
        "config":experiment.model_dump(mode="json"),"dataset_release":release,"source":source_version(Path(__file__).resolve().parent.parent),
        "environment":{"python":platform.python_version(),"platform":platform.platform(),
          "packages":sorted(f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions())},
        "label_map":LABEL_MAPS.get(experiment.task,["CAT"]),"metrics":None,"thresholds":experiment.thresholds,
        "model_artifact_hash":None,"evaluation_report":None,"trained":False,
        "finalization_required":["metrics","model artifact hash","evaluation report","runtime/export contract"]}
    if apply: write_json(Path(output)/experiment.experiment_id/"experiment.json",result)
    return result


class ModelEntry(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)
    schema_version: Literal[1]=1
    model_id: str=Field(pattern=r"^[a-z0-9_-]{1,64}$")
    task: Literal["detector","identity","behavior"]
    dataset_version: str=Field(pattern=r"^[a-z0-9_-]{1,64}$")
    training_experiment: str=Field(pattern=r"^[a-z0-9_-]{1,64}$")
    file: str
    sha256: str=Field(pattern=r"^[a-f0-9]{64}$")
    runtime: Literal["PYTORCH","ONNX","TENSORRT"]
    input_shape: tuple[int,int,int,int]
    label_map: list[str]
    thresholds: dict[str,float]
    validation_status: Literal["EXPERIMENTAL","VALIDATED_HOST","VALIDATED_JETSON","REJECTED"]="EXPERIMENTAL"

    @model_validator(mode="after")
    def semantics(self):
        expected=LABEL_MAPS.get(self.task,["CAT"])
        if self.label_map!=expected or self.input_shape[0]!=1 or self.input_shape[1]!=3 or any(not 16<=x<=4096 for x in self.input_shape[2:]):
            raise ValueError("task label map and static NCHW input required")
        if any(key not in expected or not 0<=value<=1 for key,value in self.thresholds.items()):
            raise ValueError("invalid model thresholds")
        return self


def register_model(metadata, artifact_root, registry_root, *, expected_task, apply=False):
    entry=ModelEntry.model_validate(metadata)
    if entry.task!=expected_task:
        raise ValueError("expected task mismatch")
    if entry.validation_status not in ("EXPERIMENTAL","REJECTED"):
        raise ValueError("registration cannot confer host/Jetson validation")
    path=relative_file(Path(artifact_root),entry.file)
    suffixes={"ONNX":(".onnx",),"PYTORCH":(".pt",".pth"),"TENSORRT":(".engine",)}
    if path.suffix.lower() not in suffixes[entry.runtime] or digest(path)!=entry.sha256:
        raise ValueError("artifact missing/type/hash mismatch")
    result={**entry.model_dump(mode="json"),"registered_at":datetime.now(timezone.utc).isoformat(),"activated":False}
    if apply: write_json(Path(registry_root)/f"{entry.model_id}.json",result)
    return {"status":"REGISTERED_INACTIVE" if apply else "DRY_RUN","entry":result,"activated":False}


def archive_result(bundle, metrics, evaluation_report, artifact_root, artifact_name, output, *, apply=False):
    """Archive caller-supplied results; metadata tool cannot certify how a model was trained."""
    Experiment.model_validate(bundle["config"])
    if bundle.get("status")!="EXPERIMENT_PREPARED_NOT_TRAINED" or not isinstance(metrics,dict) or not metrics or not isinstance(evaluation_report,dict) or evaluation_report.get("status") not in ("EVALUATED_SUPPLIED_PREDICTIONS","EVALUATED_SUPPLIED_EVENTS"):
        raise ValueError("prepared experiment plus supplied metrics/evaluation required")
    import json
    json.dumps(metrics,allow_nan=False); json.dumps(evaluation_report,allow_nan=False)
    artifact=relative_file(Path(artifact_root),artifact_name)
    result={**bundle,"status":"SUPPLIED_EXPERIMENT_RESULT_UNVERIFIED","metrics":metrics,
        "evaluation_report":evaluation_report,"model_artifact_hash":digest(artifact),"artifact_file":artifact_name,
        "result_environment":{"python":platform.python_version(),"platform":platform.platform()},
        "result_source":source_version(Path(__file__).resolve().parent.parent),"artifact_supplied":True,
        "validation_status":"EXPERIMENTAL","activated":False}
    if apply: write_json(Path(output),result)
    return result
