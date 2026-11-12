"""Audit reconstruction uses the recorder's frozen prefix, preserving original data."""
import json
from pathlib import Path
import sys
import pytest
KIT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(KIT/'tools'))
from reconcile_hx_acceptance import review_archive
from image_layout import sha
def fixture(tmp_path):
    messages=tmp_path/'messages.jsonl'
    rows=[{'phase':'WEIGHT_WINDOW','message':{'valid':True,'monotonic_ms':i*300,'measurement_grams':v}} for i,v in enumerate((34.9,35.1,99.0),1)]
    messages.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary={'kind':'HX711_REFERENCE_PHYSICAL_OBSERVATION','operator_mass_g':35,
        'artifacts_sha256':{'messages.jsonl':sha(messages)},'weight_window':{'measurement_grams':{'count':2,'mean':35,'min':34.9,'max':35.1,'first':34.9,'last':35.1}},
        'weight_window_pass':True,'initial_status':{'offset':-100,'scale_factor_counts_per_gram':-1064.4473}}
    (tmp_path/'summary.json').write_text(json.dumps(summary));return messages
def test_summary_time_prefix_not_final_status_tail_and_no_original_rewrite(tmp_path):
    messages=fixture(tmp_path);before=messages.read_bytes()
    result=review_archive(tmp_path,35)
    assert result['raw_sample_count']==2 and result['signed_mean_g']==35
    assert result['post_summary_tail_samples_retained']==1 and messages.read_bytes()==before
def test_original_artifact_corruption_is_not_blessed_by_owner_decision(tmp_path):
    messages=fixture(tmp_path);messages.write_text(messages.read_text()+'{}\n')
    with pytest.raises(ValueError,match='checksum'):review_archive(tmp_path,35)
