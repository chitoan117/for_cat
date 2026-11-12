"""SYNTHETIC TEMPORARY FIXTURES ONLY: no real cat/video/model evidence."""
import ast
import json
from pathlib import Path

import pytest

from ai.dataset import load_manifest, report, split_sessions, validate_row
from ai.evaluation import evaluate
from ai.interchange import export, import_export
from ai.label_schema import BEHAVIOR_V2, task_label
from ai.releases import acceptance, create_release, leakage
from ai.scripts.extract_frames import extract
from ai.scripts.import_video import import_video
from ai.scripts.label_dataset import label
from ai.scripts.split_dataset import split
from ai.tests.test_video_roundtrip import encode_fixture
from ai.training import prepare


def row(**updates):
    value = dict(schema_version=2, sample_id="sample_1", session_id="session_1", source_video="fixture.avi",
                 timestamp=None, identity_label=None, subject_label="CAT", behavior_label="IDLE", usable=True,
                 hash="a"*64, source_hash="b"*64, path="processed/sample.png")
    return {**value, **updates}


@pytest.mark.parametrize("subject,behavior,usable", [
    ("NONE", "IDLE", False), ("CAT", "NONE", False), ("UNKNOWN", "IDLE", False),
    ("UNSURE", "EATING", True), (None, "IDLE", False), ("NONE", "NONE", True), ("UNKNOWN", "NONE", False)])
def test_uncertainty_and_absence_cannot_become_idle(subject, behavior, usable):
    assert validate_row(row(subject_label=subject, behavior_label=behavior, usable=usable))


def test_legacy_and_v2_are_separate_contracts():
    legacy = row()
    legacy.pop("schema_version")
    legacy.pop("subject_label")
    legacy.update(identity_label="OWNER_CAT", behavior_label="OTHER")
    assert not validate_row(legacy)
    assert task_label(legacy, "behavior_v2") is None
    assert not validate_row(row())
    assert task_label(row(), "identity") is None
    assert validate_row(row(identity_label="OWNER_CAT"))
    assert validate_row({**legacy, "behavior_label": "IDLE"})
    assert validate_row(row(schema_version=True))


def test_label_schema_remains_python36_importable():
    path = Path(__file__).parents[1] / "label_schema.py"
    ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 6))


def test_three_video_roundtrip_v2_reuses_import_extract_labels_splits_and_interchange(tmp_path):
    pytest.importorskip("cv2")
    pytest.importorskip("PIL")
    root = tmp_path / "dataset"
    for session in range(3):
        source = tmp_path / f"synthetic_{session}.avi"
        encode_fixture(source, count=16, offset=session * 5)
        receipt = import_video(source, f"synthetic_{session}", root, apply=True)
        result = extract(receipt["source_video"], f"synthetic_{session}", root, schema_version=2,
                         interval_seconds=0.5, minimum_spacing=0.5, max_frames=4, apply=True,
                         metadata={"lighting": "SYNTHETIC_TEST_DATA", "notes": "not animal evidence"})
        assert result["frames"] == 4
    rows, errors = load_manifest(root)
    assert not errors and len(rows) == 12
    for index, sample in enumerate(rows):
        assert sample["identity_label"] is None and sample["subject_label"] is None and not sample["usable"]
        assert sample["source_offset_seconds"] in (0, 0.5, 1, 1.5)
        result = label(root, sample["sample_id"], None, BEHAVIOR_V2[index % 3], subject="CAT", apply=True)
        assert result["usable"] and result["identity_label"] is None
    with pytest.raises(ValueError, match="already labeled"):
        label(root, rows[0]["sample_id"], None, "IDLE", subject="CAT", apply=True)
    groups = split(root, apply=True)["splits"]
    assert sorted(map(len, groups.values())) == [1, 1, 1]
    labeled, errors = load_manifest(root)
    assert not errors and groups == split_sessions(labeled)
    assert report(root)["missing_labels"] == 0
    assert report(root)["identity"] == {}
    assert acceptance(root, task="behavior_v2")["class_counts"] == {"EATING": 4, "DRINKING": 4, "IDLE": 4}
    planned = prepare("behavior_v2", root)
    assert planned["status"] == "DATASET_NOT_READY_FOR_TRAINING" and planned["label_map"] == list(BEHAVIOR_V2)
    assert "NEAR_DUPLICATE_CHECK_INCOMPLETE" not in planned["validation"]["warnings"]
    assert planned["metrics"] is None and planned["model_metadata"] is None
    released = create_release(root, "v2_fixture", tmp_path / "releases", task="behavior_v2")
    assert released["label_schema_version"] == 2
    exported = tmp_path / "export"
    assert export(root, exported, task="behavior_v2", apply=True)["samples"] == 12
    assert {path.name for path in (exported / "images").iterdir()} == set(BEHAVIOR_V2)
    imported = tmp_path / "import"
    assert import_export(exported, imported, apply=True)["samples"] == 12
    restored, errors = load_manifest(imported)
    assert not errors and all(sample["identity_label"] is None and sample["subject_label"] == "CAT" for sample in restored)
    assert split_sessions(restored) == groups
    bad_splits = {"train": list(groups["train"]), "validation": list(groups["validation"]), "test": list(groups["test"])}
    bad_splits["test"].extend(groups["train"])
    assert any(failure["code"] == "SESSION_LEAKAGE" for failure in leakage(root, labeled, bad_splits)["failures"])


@pytest.mark.parametrize("subject,behavior", [("NONE", "NONE"), ("UNKNOWN", "UNSURE"), ("CAT", "UNSURE")])
def test_review_labels_preserved_unusable_and_never_exported_as_idle(tmp_path, subject, behavior):
    pytest.importorskip("PIL")
    from PIL import Image
    from ai.dataset import digest

    (tmp_path / "processed").mkdir()
    image = tmp_path / "processed/sample.png"
    Image.new("RGB", (8, 8), "purple").save(image)
    sample = row(subject_label=None, behavior_label=None, usable=False, hash=digest(image))
    (tmp_path / "manifest.jsonl").write_text(json.dumps(sample) + "\n", encoding="utf-8")
    result = label(tmp_path, sample["sample_id"], None, behavior, subject=subject, apply=True)
    assert not result["usable"] and result["behavior_label"] == behavior
    assert not split_sessions(load_manifest(tmp_path)[0])["train"]
    with pytest.raises(ValueError, match="no usable"):
        export(tmp_path, tmp_path / "export", task="behavior_v2")


def test_v2_source_alias_leakage_is_rejected():
    samples = [row(sample_id="s1", session_id="session_a"), row(sample_id="s2", session_id="session_b", hash="c"*64)]
    result = leakage(Path("."), samples, {"train": ["session_a"], "validation": ["session_b"], "test": []}, near_limit=0)
    assert any(failure["code"] == "SOURCE_LEAKAGE" for failure in result["failures"])


def test_v2_evaluation_does_not_alias_unknown_to_idle():
    result = evaluate([{"actual": "IDLE", "predicted": "UNKNOWN"}], "behavior_v2")
    assert result["confusion_matrix"]["IDLE"]["UNKNOWN"] == 1
    assert result["confusion_matrix"]["IDLE"]["IDLE"] == 0
    with pytest.raises(ValueError):
        evaluate([{"actual": "OTHER", "predicted": "IDLE"}], "behavior_v2")


def test_v2_training_plan_only_ready_after_complete_session_and_quality_gates(tmp_path):
    pytest.importorskip("PIL")
    import hashlib
    import random
    from PIL import Image
    from ai.dataset import digest

    rng = random.Random(42)
    (tmp_path / "processed").mkdir()
    samples = []
    for session in range(3):
        for number, behavior in enumerate(BEHAVIOR_V2):
            name = f"fixture_{session}_{number}"
            path = tmp_path / f"processed/{name}.png"
            Image.frombytes("RGB", (48, 48), bytes(rng.randrange(256) for _ in range(48*48*3))).save(path)
            samples.append(row(sample_id=name, session_id=f"session_{session}", path=f"processed/{name}.png",
                               hash=digest(path), source_hash=hashlib.sha256(str(session).encode()).hexdigest(),
                               behavior_label=behavior, lighting=f"SYNTHETIC_{session % 2}",
                               view_angle=f"SYNTHETIC_{session % 2}"))
    (tmp_path / "manifest.jsonl").write_text("".join(json.dumps(sample) + "\n" for sample in samples), encoding="utf-8")
    split(tmp_path, apply=True)
    planned = prepare("behavior_v2", tmp_path)
    assert planned["status"] == "READY_FOR_FUTURE_TRAINER"
    assert planned["label_map"] == list(BEHAVIOR_V2) and planned["metrics"] is None
    assert not list(tmp_path.rglob("*.pt")) and not list(tmp_path.rglob("*.onnx"))
