"""Supplied SYNTHETIC_TEST_DATA only. No model training/inference metrics evidence."""
from pathlib import Path
import json
import hashlib
import pytest
from ai.evaluation import evaluate,evaluate_events,threshold_sweep
from ai.experiments import Experiment,candidates,prepare_bundle,register_model,archive_result


def config():
    return json.loads((Path(__file__).parents[1]/"experiments"/"example.json").read_text())


def test_empty_evaluations_emit_no_metrics():
    assert evaluate([],"identity")=={"status":"PREDICTIONS_NOT_AVAILABLE"}
    assert "accuracy" not in threshold_sweep([],"identity",[0.5])
    assert evaluate_events([],[])["status"]=="EVENTS_NOT_AVAILABLE"


def test_identity_macro_and_both_error_directions():
    rows=[dict(actual="OTHER_CAT",predicted="OWNER_CAT"),dict(actual="OTHER_CAT",predicted="OTHER_CAT"),
        dict(actual="OWNER_CAT",predicted="OTHER_CAT"),dict(actual="OWNER_CAT",predicted="OWNER_CAT"),
        dict(actual="OTHER_OBJECT",predicted="UNKNOWN")]
    result=evaluate(rows,"identity")
    assert result["accuracy"]==0.4 and result["other_cat_to_owner_false_acceptance_count"]==1
    assert result["owner_cat_to_other_false_rejection_count"]==1
    assert result["owner_cat_to_other_false_rejection_rate"]==0.5
    assert result["macro_precision"]==0.5 and result["unknown_rate"]==0.2
    assert result["per_class"]["OTHER_OBJECT"]["recall"]==0


def test_sweep_abstains_and_does_not_select_production_threshold():
    rows=[dict(actual="OTHER_CAT",predicted="OWNER_CAT",confidence=0.4),dict(actual="OWNER_CAT",predicted="OWNER_CAT",confidence=0.9)]
    report=threshold_sweep(rows,"identity",[0,0.5,1])
    assert report["results"][0]["other_cat_to_owner_false_acceptance_count"]==1
    assert report["results"][1]["other_cat_to_owner_false_acceptance_count"]==0
    assert report["results"][2]["unknown_rate"]==1
    assert report["selected_production_threshold"] is None
    with pytest.raises(ValueError): threshold_sweep([{**rows[0],"confidence":float("nan")}],"identity",[0.5])


def test_temporal_events_tolerance_overlap_no_cross_session_or_double_match():
    a=dict(event_id="a",session_id="source_a",track_id="cat_1",label="EATING",start=10,end=20)
    p={**a,"event_id":"p","start":10.2,"end":19.5}
    false={**p,"event_id":"wrong_source","session_id":"source_b"}
    missed={**a,"event_id":"drink","label":"DRINKING","start":30,"end":35}
    report=evaluate_events([a,missed],[p,{**p,"event_id":"duplicate_prediction"},false])
    assert len(report["matches"])==1 and len(report["false_events"])==2 and report["missed_events"]==["drink"]
    assert not evaluate_events([a],[p],start_tolerance=0.1)["matches"]
    with pytest.raises(ValueError): evaluate_events([a,a],[p])
    with pytest.raises(ValueError): evaluate_events([{**a,"end":float("nan")}],[p])


@pytest.mark.parametrize("change",[{"learning_rate":float("nan")},{"epochs":0},{"input_size":[1,1]},
    {"thresholds":{"OWNER_CAT":2}},{"class_weights":{"OWNER_CAT":1}},{"extra":True}])
def test_experiment_schema_rejects_invalid(change):
    with pytest.raises(ValueError): Experiment.model_validate({**config(),**change})


def test_experiment_bundle_requires_validated_release_and_stays_untrained(tmp_path):
    c=config(); release=dict(dataset_version=c["dataset_version"],validation_status="PILOT_DATASET",sample_count=3,manifest_hash="1"*64)
    with pytest.raises(ValueError): prepare_bundle(c,{**release,"validation_status":"REJECTED"},tmp_path)
    with pytest.raises(ValueError): prepare_bundle({**c,"architecture":"frame_classifier"},release,tmp_path)
    bundle=prepare_bundle(c,release,tmp_path,apply=True)
    assert bundle["metrics"] is None and bundle["model_artifact_hash"] is None and bundle["trained"] is False
    assert bundle["source"]["source_tree_sha256"] and bundle["environment"]["python"]
    with pytest.raises(FileExistsError): prepare_bundle(c,release,tmp_path,apply=True)
    assert all(x["deployment_status"]=="JETSON_NOT_TESTED" for x in candidates())


def model(file,sha):
    return dict(model_id="synthetic_artifact",task="identity",dataset_version="synthetic_dataset",training_experiment="synthetic_exp",
        file=file,sha256=sha,runtime="ONNX",input_shape=[1,3,224,224],label_map=["OWNER_CAT","OTHER_CAT","OTHER_OBJECT"],thresholds={})


def test_registration_hash_labels_task_path_validation_and_no_activation(tmp_path):
    # Arbitrary bytes test metadata hashing only; this is NOT a trained/valid ONNX model.
    path=tmp_path/"artifact.onnx"; path.write_bytes(b"SYNTHETIC_HASH_TEST_NOT_MODEL")
    entry=model(path.name,hashlib.sha256(path.read_bytes()).hexdigest()); registry=tmp_path/"registry"
    result=register_model(entry,tmp_path,registry,expected_task="identity",apply=True)
    assert result["activated"] is False and result["entry"]["validation_status"]=="EXPERIMENTAL"
    for change in ({"sha256":"0"*64},{"file":"../outside.onnx"},{"label_map":["OWNER_CAT"]},
                   {"validation_status":"VALIDATED_JETSON"}):
        with pytest.raises(ValueError): register_model({**entry,**change},tmp_path,registry,expected_task="identity")
    with pytest.raises(ValueError): register_model(entry,tmp_path,registry,expected_task="behavior")
    with pytest.raises(FileExistsError): register_model(entry,tmp_path,registry,expected_task="identity",apply=True)


def test_future_result_archival_preserves_provenance_without_validation_claim(tmp_path):
    c=config(); release=dict(dataset_version=c["dataset_version"],validation_status="PILOT_DATASET",sample_count=3,manifest_hash="1"*64)
    bundle=prepare_bundle(c,release,tmp_path)
    artifact=tmp_path/"hash_fixture.onnx"; artifact.write_bytes(b"SYNTHETIC_NOT_MODEL")
    evaluation=evaluate([dict(actual="OWNER_CAT",predicted="UNKNOWN")],"identity")
    saved=archive_result(bundle,{"fixture_accuracy":0},evaluation,tmp_path,artifact.name,tmp_path/"result.json",apply=True)
    assert saved["model_artifact_hash"]==hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert saved["validation_status"]=="EXPERIMENTAL" and not saved["activated"]
    with pytest.raises(ValueError): archive_result(bundle,{"bad":float("nan")},evaluation,tmp_path,artifact.name,tmp_path/"bad.json")


def test_malformed_release_and_prediction_objects_are_rejected(tmp_path):
    with pytest.raises(ValueError): prepare_bundle(config(),[],tmp_path)
    with pytest.raises(ValueError): threshold_sweep(["not-a-prediction"],"identity",[0.5])
