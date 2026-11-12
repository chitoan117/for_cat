"""Generated MP4/noise fixtures ONLY. Never imported real footage or animal truth."""
import copy
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys

import pytest

from ai.behavior_readiness import readiness, write_reports
from ai.dataset import load_manifest
from ai.label_schema import BEHAVIOR_V2
from ai.manifest_io import dataset_lock
from ai.quality import near_pairs
from ai.releases import leakage
from ai.scripts.extract_frames import extract
from ai.scripts.import_video import import_directory, import_video, load_sources
from ai.scripts.prepare_behavior_v2 import annotation_template, extract_sessions
from ai.scripts.split_dataset import split
from ai.temporal_annotations import annotate_intervals, seconds


def video(path, seed=1, frames=60, flat=False):
    import cv2
    import numpy as np

    rng = np.random.default_rng(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Encode at an ASCII path then rename: tests Unicode SOURCE names on Windows.
    temporary = path.parent / f"encoder_{seed}.mp4"
    writer = cv2.VideoWriter(str(temporary), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 48))
    assert writer.isOpened(), "MP4 encoder required for actual codec fixture validation"
    try:
        for _ in range(frames):
            writer.write(np.full((48,64,3), 80, np.uint8) if flat else rng.integers(0,256,(48,64,3),dtype=np.uint8))
    finally:
        writer.release()
    temporary.rename(path)
    return path


def dataset(tmp_path, count=3, flat=False):
    incoming, root = tmp_path / "incoming", tmp_path / "dataset"
    for index in range(count):
        video(incoming / f"cat {index}.mp4", seed=index+1, flat=flat)
    import_directory(incoming, root, apply=True)
    extract_sessions(root, apply=True)
    return incoming, root


def recipe(root, source, intervals=None, name="human.json"):
    document = annotation_template(root, source["session_id"])
    document.update(annotation_source="HUMAN_REVIEWED", reviewer="SYNTHETIC_TEST_FIXTURE",
                    intervals=intervals or [{"start": 0, "end": 2, "label": "EATING"},
                                           {"start": 2, "end": 4, "label": "DRINKING"},
                                           {"start": 4, "end": 6, "label": "IDLE"}])
    path = root.parent / name
    path.write_text(json.dumps(document), encoding="utf-8-sig")
    return path, document


def test_batch_import_unicode_collision_safe_sessions_duplicates_and_rerun(tmp_path):
    incoming, root = tmp_path / "incoming", tmp_path / "dataset"
    first = video(incoming / "Ăn 猫 01.MP4", seed=1)
    second = video(incoming / "sub folder" / "Ăn 猫 01.MP4", seed=2)
    shutil.copyfile(first, incoming / "copy same bytes.mp4")
    result = import_directory(incoming, root)
    assert result["input_files"] == 3 and result["independent_sources"] == 2 and not root.exists()
    result = import_directory(incoming, root, apply=True)
    sources = load_sources(root)
    assert len(sources) == 2 and len({source["session_id"] for source in sources}) == 2
    assert sorted(len(source["original_aliases"]) for source in sources) == [1, 2]
    assert any(source["original_filename"] == "Ăn 猫 01.MP4" for source in sources)
    assert all(source["media"]["fps"] == 10 and source["media"]["width"] == 64 for source in sources)
    assert all(source["media"]["duration_seconds"] == 6 and source["import_timestamp"] for source in sources)
    before = (root / "sources.jsonl").read_bytes()
    import_directory(incoming, root, apply=True)
    assert (root / "sources.jsonl").read_bytes() == before
    alternate = tmp_path / "alternate"
    import_directory(incoming, alternate, apply=True)
    assert {source["session_id"] for source in load_sources(alternate)} == {source["session_id"] for source in sources}
    assert first.exists() and second.exists()
    with pytest.raises(ValueError, match="session ID collision"):
        _collision(first, second, tmp_path / "collision")


def _collision(first, second, root):
    import_video(first, "fixed_session", root, apply=True)
    import_video(second, "fixed_session", root, apply=True)


def test_extraction_timestamps_sequences_quality_and_safe_resume(tmp_path):
    _, root = dataset(tmp_path, 1)
    rows, errors = load_manifest(root)
    assert not errors and len(rows) == 12
    assert [row["frame_index"] for row in rows] == list(range(0,60,5))
    assert [row["sample_sequence"] for row in rows] == list(range(12))
    assert [row["source_offset_seconds"] for row in rows] == [index/2 for index in range(12)]
    assert all(row["behavior_label"] is None and row["subject_label"] is None and not row["usable"] for row in rows)
    assert all("blur_variance" in row["quality"] and "near_duplicate_warning" in row["quality"] for row in rows)
    source = load_sources(root)[0]
    path, _ = recipe(root, source)
    annotate_intervals(root, path, apply=True, boundary_seconds=0)
    before = (root / "manifest.jsonl").read_bytes()
    extract_sessions(root, apply=True)
    assert (root / "manifest.jsonl").read_bytes() == before
    with pytest.raises(ValueError, match="policy"):
        extract(source["source_video"], source["session_id"], root, apply=True, resume=True,
                schema_version=2, interval_seconds=1, minimum_spacing=0.5, max_frames=1000)
    assert (root / "manifest.jsonl").read_bytes() == before


def test_interval_boundaries_correction_and_history_are_atomic(tmp_path):
    _, root = dataset(tmp_path, 1)
    source = load_sources(root)[0]
    path, document = recipe(root, source)
    unchanged = (root / "manifest.jsonl").read_bytes()
    result = annotate_intervals(root, path)
    assert result["changed_samples"] == 12 and (root / "manifest.jsonl").read_bytes() == unchanged
    result = annotate_intervals(root, path, apply=True)
    labels = {row["source_offset_seconds"]: row["behavior_label"] for row in load_manifest(root)[0]}
    assert labels[0] == "EATING" and labels[2] == labels[4] == "UNSURE"
    assert labels[2.5] == "DRINKING" and labels[4.5] == "IDLE"
    assert annotate_intervals(root, path, apply=True)["status"] == "UNCHANGED"
    before = (root / "manifest.jsonl").read_bytes()
    document["intervals"] = [{"start": "00:00.0", "end": "00:03.0", "label": "UNKNOWN"},
                             {"start": "00:03.0", "end": "00:06.0", "label": "UNSURE"}]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="conflicts"):
        annotate_intervals(root, path, apply=True)
    assert (root / "manifest.jsonl").read_bytes() == before
    corrected = annotate_intervals(root, path, apply=True, replace=True)
    values = load_manifest(root)[0]
    assert {row["behavior_label"] for row in values} == {"UNKNOWN", "UNSURE"}
    assert all(not row["usable"] for row in values)
    backup = root / "annotations/history" / corrected["revision"] / "manifest_before.jsonl"
    assert backup.read_bytes() == before
    with dataset_lock(root):
        with pytest.raises(ValueError, match="writer lock"):
            annotate_intervals(root, path, apply=True, replace=True)


@pytest.mark.parametrize("problem", ["overlap", "predictions", "wrong_source", "like", "beyond_end"])
def test_bad_interval_documents_do_not_modify_manifest(tmp_path, problem):
    _, root = dataset(tmp_path, 1)
    path, document = recipe(root, load_sources(root)[0])
    if problem == "overlap": document["intervals"][1]["start"] = 1
    elif problem == "predictions": document["annotation_source"] = "AI_PREDICTIONS"
    elif problem == "wrong_source": document["source_hash"] = "0"*64
    elif problem == "like": document["intervals"][0]["label"] = "LIKE"
    else: document["intervals"][-1]["end"] = 99
    path.write_text(json.dumps(document), encoding="utf-8")
    before = (root / "manifest.jsonl").read_bytes()
    with pytest.raises(ValueError): annotate_intervals(root, path, apply=True)
    assert (root / "manifest.jsonl").read_bytes() == before


def test_template_is_never_ground_truth_and_tiny_dataset_not_ready(tmp_path):
    _, root = dataset(tmp_path, 1)
    source = load_sources(root)[0]
    document = annotation_template(root, source["session_id"])
    path = tmp_path / "template.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="HUMAN_REVIEWED"):
        annotate_intervals(root, path, apply=True)
    assert split(root, apply=True)["status"] == "NOT_READY" and not (root / "splits.json").exists()
    report = readiness(root)
    assert report["status"] == "NOT_READY" and report["per_label"]["UNANNOTATED"]["samples"] == 12


def test_readiness_report_complete_coverage_and_corruption(tmp_path):
    incoming, root = dataset(tmp_path)
    for index, source in enumerate(load_sources(root)):
        path, _ = recipe(root, source, name=f"human_{index}.json")
        annotate_intervals(root, path, apply=True, boundary_seconds=0)
    groups = split(root, apply=True)["splits"]
    assert all(len(value) == 1 for value in groups.values()) and split(root, apply=True)["status"] == "UNCHANGED"
    report = readiness(root)
    assert report["status"] == "READY_FOR_PILOT_TRAINING", report["failures"]
    assert report["source_videos"] == 3 and report["samples_extracted_retained"] == 36
    assert report["total_known_source_duration_seconds"] == 18
    assert all(report["per_label"][label]["samples"] == 12 for label in BEHAVIOR_V2)
    from ai.training import prepare
    assert prepare("behavior_v2", root)["status"] == "READY_FOR_FUTURE_TRAINER"
    files = write_reports(report, tmp_path / "report")
    assert json.loads(Path(files["json"]).read_text())["status"] == "READY_FOR_PILOT_TRAINING"
    assert "Sampling-cell coverage" in Path(files["markdown"]).read_text()
    with pytest.raises(FileExistsError): write_reports(report, tmp_path / "report")
    row = load_manifest(root)[0][0]
    (root / row["path"]).write_bytes(b"synthetic corrupt fixture")
    report = readiness(root)
    assert report["status"] == "NOT_READY" and report["corrupt_samples"] == 1
    with pytest.raises(ValueError, match="corrupt/changed"):
        extract_sessions(root, apply=True)
    assert all(path.exists() for path in incoming.glob("*.mp4"))


def test_eating_only_and_manual_leakage_never_ready(tmp_path):
    _, root = dataset(tmp_path)
    for index, source in enumerate(load_sources(root)):
        path, _ = recipe(root, source, [{"start": 0, "end": 6, "label": "EATING"}], f"eat_{index}.json")
        annotate_intervals(root, path, apply=True, boundary_seconds=0)
    groups = split(root, apply=True)["splits"]
    report = readiness(root)
    assert report["status"] == "NOT_READY" and "INSUFFICIENT_LABEL_COVERAGE:DRINKING" in report["failures"]
    groups["test"].extend(groups["train"])
    (root / "splits.json").write_text(json.dumps(groups), encoding="utf-8")
    assert readiness(root)["leakage"]["confirmed_leakage"]


def test_preference_metadata_is_not_trainable_or_a_water_roi_redefinition(tmp_path):
    incoming = tmp_path / "incoming"
    video(incoming / "food A.mp4")
    root = tmp_path / "dataset"
    meta = {"defaults": {"food_variant": "square_kibble", "preference_trial_id": "trial_01", "trial_order": 1,
                         "food_bowl_position": "RED_FOOD_ROI", "session_pair_or_group": "pair_01"}}
    import_directory(incoming, root, apply=True, metadata_document=meta)
    extract_sessions(root, apply=True)
    rows = load_manifest(root)[0]
    assert all(row["food_variant"] == "square_kibble" and row["behavior_label"] is None for row in rows)
    assert tuple(BEHAVIOR_V2) == ("EATING", "DRINKING", "IDLE")
    changed = copy.deepcopy(meta); changed["defaults"]["food_variant"] = "bone_kibble"
    with pytest.raises(ValueError, match="metadata conflict"):
        import_directory(incoming, root, apply=True, metadata_document=changed)
    changed["defaults"]["food_bowl_position"] = "BLUE_WATER_ROI"
    with pytest.raises(ValueError, match="BLUE=WATER"):
        import_directory(incoming, tmp_path / "bad", apply=True, metadata_document=changed)


def test_source_alias_and_preference_groups_cannot_cross_splits():
    from ai.session_groups import source_groups
    rows = [dict(schema_version=2, sample_id="s1", session_id="one", source_hash="a"*64, hash="1"*64, session_pair_or_group="pair"),
            dict(schema_version=2, sample_id="s2", session_id="two", source_hash="b"*64, hash="2"*64, session_pair_or_group="pair")]
    assert len(source_groups(rows)) == 1
    checked = leakage(Path("."), rows, {"train": ["one"], "validation": ["two"], "test": []}, near_limit=0)
    assert any(item["code"] == "SESSION_GROUP_LEAKAGE" for item in checked["failures"])


def test_near_index_matches_brute_force_including_identical_signatures():
    rng = random.Random(7)
    values = [rng.getrandbits(64) for _ in range(10)] + [0,0,1,3,7]
    items = [dict(sample_id=f"s{index}", dhash=f"{value:016x}", split="train" if index % 2 else "test",
                  source_hash=str(index % 3)) for index, value in enumerate(values)]
    expected = [(a,b) for a in range(len(items)) for b in range(a+1,len(items)) if (values[a]^values[b]).bit_count() <= 3]
    result = near_pairs(items)
    assert result["complete"] and result["pairs"] == len(expected)
    assert result["cross_split_pairs"] == sum(items[a]["split"] != items[b]["split"] for a,b in expected)
    assert not near_pairs(items, comparison_limit=1)["complete"]


def test_orchestration_dry_run_and_rerun_never_label_samples(tmp_path):
    incoming = tmp_path / "incoming"
    video(incoming / "clip.mp4")
    root = tmp_path / "dataset"
    command = [sys.executable, "-B", "-m", "ai.scripts.prepare_behavior_v2", "prepare",
               "--videos-dir", str(incoming), "--dataset-root", str(root)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 2 and json.loads(result.stdout)["status"] == "NOT_READY" and not root.exists()
    for _ in range(2):
        result = subprocess.run(command + ["--apply"], capture_output=True, text=True)
        assert result.returncode == 2, result.stderr
        assert json.loads(result.stdout)["source_videos"] == 1
    assert all(row["behavior_label"] is None for row in load_manifest(root)[0])


def test_exact_duplicates_and_blur_are_detected_without_quality_deletion(tmp_path):
    _, root = dataset(tmp_path, 1, flat=True)
    rows = load_manifest(root)[0]
    source = load_sources(root)[0]
    receipt = json.loads((root / "extractions" / (source["session_id"] + ".json")).read_text())
    assert receipt["duplicate_frames_skipped"] > 0
    assert rows and all(row["quality"]["blur_warning"] for row in rows)
    assert all((root / row["path"]).exists() for row in rows)


def test_interrupted_annotation_commit_preserves_manifest(tmp_path, monkeypatch):
    _, root = dataset(tmp_path, 1)
    path, _ = recipe(root, load_sources(root)[0])
    before = (root / "manifest.jsonl").read_bytes()
    def fail_replace(*args):
        raise OSError("SYNTHETIC atomic-commit failure")
    monkeypatch.setattr("ai.manifest_io.os.replace", fail_replace)
    with pytest.raises(OSError, match="atomic-commit"):
        annotate_intervals(root, path, apply=True)
    assert (root / "manifest.jsonl").read_bytes() == before
    assert not (root / ".dataset-write.lock").exists()


def test_import_copy_failure_never_removes_source(tmp_path, monkeypatch):
    incoming, root = tmp_path / "incoming", tmp_path / "dataset"
    original = video(incoming / "clip.mp4")
    before = original.read_bytes()
    def fail_copy(*args):
        raise OSError("SYNTHETIC copy failure")
    monkeypatch.setattr("ai.scripts.import_video.shutil.copyfileobj", fail_copy)
    with pytest.raises(OSError, match="copy failure"):
        import_directory(incoming, root, apply=True)
    assert original.read_bytes() == before and not list((root / "raw").glob("*.mp4"))


def test_split_refresh_requires_explicit_action_and_preserves_previous_split(tmp_path):
    incoming, root = dataset(tmp_path)
    split(root, apply=True)
    before = (root / "splits.json").read_bytes()
    video(incoming / "new clip.mp4", seed=99)
    import_directory(incoming, root, apply=True)
    extract_sessions(root, apply=True)
    with pytest.raises(FileExistsError, match="refresh"):
        split(root, apply=True)
    assert (root / "splits.json").read_bytes() == before
    split(root, apply=True, refresh=True)
    assert next((root / "split_history").iterdir()).read_bytes() == before


def test_near_review_is_human_scoped_and_cannot_approve_structural_leakage(tmp_path):
    from PIL import Image
    from ai.dataset import digest
    _, root = dataset(tmp_path)
    for index, source in enumerate(load_sources(root)):
        path, _ = recipe(root, source, name=f"human_{index}.json")
        annotate_intervals(root, path, apply=True, boundary_seconds=0)
    split(root, apply=True)
    rows = load_manifest(root)[0]
    for index, item in enumerate(rows):
        path = root / item["path"]
        Image.new("RGB", (64,48), (index*5, index*5, index*5)).save(path)
        item["hash"] = digest(path)
    (root / "manifest.jsonl").write_text("".join(json.dumps(item)+"\n" for item in rows), encoding="utf-8")
    report = readiness(root)
    assert report["near_duplicates"]["cross_split_pairs"] > 0 and report["status"] == "NOT_READY"
    review = tmp_path / "review.json"
    document = {"review_source": "HUMAN_REVIEWED_SOURCE_SESSIONS", "notes": "SYNTHETIC fixture review only",
                "manifest_sha256": report["manifest_sha256"], "reviewed_source_pairs": report["near_duplicates"]["cross_source_pairs"]}
    review.write_text(json.dumps(document), encoding="utf-8")
    assert readiness(root, near_review=review)["status"] == "READY_FOR_PILOT_TRAINING"
    groups = json.loads((root / "splits.json").read_text())
    groups["test"].extend(groups["train"])
    (root / "splits.json").write_text(json.dumps(groups), encoding="utf-8")
    report = readiness(root, near_review=review)
    assert report["status"] == "NOT_READY" and report["leakage"]["confirmed_leakage"]
    document["manifest_sha256"] = "0"*64
    review.write_text(json.dumps(document), encoding="utf-8")
    assert "NEAR_REVIEW_DOCUMENT_INVALID_OR_STALE" in readiness(root, near_review=review)["failures"]


def test_source_video_corruption_is_reported_without_overwriting_original(tmp_path):
    incoming, root = dataset(tmp_path, 1)
    original = next(incoming.glob("*.mp4")).read_bytes()
    source = load_sources(root)[0]
    (root / "raw" / source["source_video"]).write_bytes(b"SYNTHETIC corrupt staging copy")
    report = readiness(root)
    assert any(item.startswith("SOURCE_VIDEO_HASH_MISMATCH") for item in report["failures"])
    with pytest.raises(ValueError, match="changed/corrupt"):
        import_directory(incoming, root, apply=True)
    assert next(incoming.glob("*.mp4")).read_bytes() == original


def test_explicit_offline_sampling_budget_preserves_legacy_default():
    from ai.sampling import SamplingPolicy
    legacy, extended = SamplingPolicy(0.5, 0), SamplingPolicy(0.5, 0, max_samples=1002)
    for index in range(1000):
        assert legacy.select(index/2, str(index).encode())
        assert extended.select(index/2, str(index).encode())
    with pytest.raises(ValueError, match="budget"):
        legacy.select(500, b"new")
    assert extended.select(500, b"new")


@pytest.mark.parametrize("value", [True, "00:99.0", -1, float("nan"), "bad"])
def test_bad_time_codes(value):
    with pytest.raises(ValueError): seconds(value)
