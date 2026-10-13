import json
import random

import pytest

from ai.dataset import load_manifest, report, split_sessions, validate_row, validate_splits
from ai.evaluation import evaluate
from ai.scripts.label_dataset import label
from ai.scripts.split_dataset import split
from ai.scripts.import_capture import import_capture
from ai.scripts.import_video import import_video
from ai.training import prepare


def row(n: int) -> dict:
    return {"sample_id": f"s-{n}", "session_id": f"session-{n // 3}",
            "source_video": "", "timestamp": None, "identity_label": "OWNER_CAT",
            "behavior_label": "EATING", "usable": True, "hash": f"{n:064x}",
            "source_hash": f"{n:064x}", "path": f"processed/s-{n}.jpg"}


def test_empty_dataset_reports_missing_cleanly(tmp_path):
    assert report(tmp_path) == {"status": "DATASET_NOT_AVAILABLE", "samples": 0}
    assert split(tmp_path)["status"] == "DATASET_NOT_AVAILABLE"
    assert prepare("identity", tmp_path)["status"] == "DATASET_NOT_AVAILABLE"
    assert evaluate([], "identity")["status"] == "PREDICTIONS_NOT_AVAILABLE"


def test_session_split_reproducible_no_leakage(tmp_path):
    rows = [row(i) for i in range(30)]
    one = split_sessions(rows, seed=42)
    assert one == split_sessions(list(reversed(rows)), seed=42)
    assert not validate_splits(one)
    assert len(one["train"] + one["validation"] + one["test"]) == 10
    assert validate_splits({"train": ["session-1"], "validation": ["session-1"], "test": []})
    (tmp_path / "manifest.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert split(tmp_path)["status"] == "DRY_RUN"
    assert split(tmp_path, apply=True)["status"] == "SPLIT"
    with pytest.raises(FileExistsError):
        split(tmp_path, apply=True)  # no silent overwrite
    assert prepare("identity", tmp_path)["status"] == "DATASET_INVALID"  # images are deliberately absent


def test_metadata_parser_resists_malformed_objects_and_json(tmp_path):
    rng_rows = [{"identity_label": []}, [], {"path": ["../evil"]},
                {"sample_id": "../bad", "identity_label": {"bad": 1}}]
    for item in rng_rows:
        assert validate_row(item)
    (tmp_path / "manifest.jsonl").write_text('not-json\n{"sample_id": [1]}\n', encoding="utf-8")
    rows, errors = load_manifest(tmp_path)
    assert rows == [] and errors
    assert report(tmp_path)["status"] == "DATASET_INVALID"


def test_bounded_metadata_fuzz_no_tracebacks():
    rng = random.Random(928)
    values = [None, [], {}, 1, -1, True, "../bad", "" * 1, "x" * 257]
    fields = ("sample_id", "session_id", "timestamp", "hash", "path",
              "identity_label", "behavior_label", "source_offset_seconds")
    for _ in range(500):
        entry = row(1)
        entry[rng.choice(fields)] = rng.choice(values)
        assert isinstance(validate_row(entry), list)


def test_resumable_labeling_skip_and_no_silent_relabel(tmp_path):
    item = row(1)
    item["identity_label"] = item["behavior_label"] = None
    (tmp_path / "manifest.jsonl").write_text(json.dumps(item) + "\n", encoding="utf-8")
    assert label(tmp_path, "s-1", "SKIP", "UNSURE")["status"] == "DRY_RUN"
    assert load_manifest(tmp_path)[0][0]["identity_label"] is None
    assert label(tmp_path, "s-1", "SKIP", "UNSURE", apply=True)["usable"] is False
    with pytest.raises(ValueError, match="already labeled"):
        label(tmp_path, "s-1", "OWNER_CAT", "EATING", apply=True)


def test_metrics_only_from_supplied_synthetic_test_predictions():
    # SYNTHETIC_TEST_DATA: arithmetic test, not AI accuracy evidence.
    rows = [{"actual": "OTHER_CAT", "predicted": "OWNER_CAT"},
            {"actual": "OTHER_CAT", "predicted": "OTHER_CAT"},
            {"actual": "OWNER_CAT", "predicted": "OWNER_CAT"}]
    result = evaluate(rows, "identity")
    assert result["other_cat_to_owner_false_acceptance_rate"] == 0.5
    assert result["other_cat_to_owner_false_acceptance_count"] == 1
    assert result["other_cat_test_count"] == 2
    with pytest.raises(ValueError):
        evaluate([{"actual": "cat", "predicted": "OWNER_CAT"}], "identity")


def test_opt_in_capture_video_import_and_corruption(tmp_path):
    pytest.importorskip("PIL")  # Jetson core tests don't require Pillow
    from PIL import Image

    photo = tmp_path / "synthetic.png"
    Image.new("RGB", (3, 3), (0, 0, 0)).save(photo)
    root = tmp_path / "dataset"
    assert import_capture(photo, "synthetic_session", root)["status"] == "DRY_RUN"
    assert not (root / "manifest.jsonl").exists()
    assert import_capture(photo, "synthetic_session", root, apply=True)["status"] == "IMPORTED"
    with pytest.raises((ValueError, FileExistsError)):
        import_capture(photo, "synthetic_session", root, apply=True)
    assert report(root)["samples"] == 1
    corrupt = tmp_path / "broken.png"
    corrupt.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="not verified"):
        import_capture(corrupt, "synthetic_session", root)
    video = tmp_path / "test.mp4"
    video.write_bytes(b"synthetic source file for import only")
    assert import_video(video, "synthetic_session", root)["status"] == "DRY_RUN"
    imported = import_video(video, "synthetic_session", root, apply=True)
    assert imported["status"] == "IMPORTED"
    with pytest.raises(ValueError, match="already imported"):
        import_video(video, "synthetic_session", root, apply=True)


def test_training_plan_requires_real_image_files_and_session_splits(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    root = tmp_path / "dataset"
    for i in range(3):
        image = tmp_path / f"synthetic-{i}.png"
        Image.new("RGB", (3, 3), (i * 80, 0, 0)).save(image)
        imported = import_capture(image, f"session-{i}", root, apply=True)
        label(root, imported["sample_id"], "OWNER_CAT", "EATING", apply=True)
    assert split(root, apply=True)["status"] == "SPLIT"
    plan = prepare("identity", root)
    assert plan["status"] == "READY_FOR_FUTURE_TRAINER"
    assert all(plan["counts"][name] == 1 for name in ("train", "validation", "test"))
    assert plan["metrics"] is None and plan["model_metadata"] is None
