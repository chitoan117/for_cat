import json
from pathlib import Path
import sqlite3
import sys
import pytest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'))
from app.ai_frame_contract import StateTap,WriterLock,PREFIX,SOURCE
from app.ai_state import AiStateReader

def frame(seq=1,epoch='producer_A',species='CAT',stamp=100000):
    return {'ai_schema_version':1,'data_source':'REAL','simulated':False,'actuator_execution':False,
            'source':SOURCE,'host_boot_id':'boot','producer_epoch':epoch,'health':'ONLINE',
            'classification':species,'confidence':.9 if species in ('CAT','DOG') else None,
            'source_frame_id':seq,'roi_sequence':seq,'roi_observation_ms':stamp,'updated_monotonic_ms':stamp,
            'roi_mode':'FULL_FRAME','roi_config_valid':True,'roi_calibrated':False,'bbox_available':True,
            'roi_decision_eligible':True,'frame_width':640,'frame_height':480,'detections':[]}
def send(tap,data):return tap.accept(PREFIX+json.dumps(data))
def row(path):
    with sqlite3.connect(path) as db:return json.loads(db.execute('SELECT body FROM ai_latest WHERE id=1').fetchone()[0])
def test_frame_to_canonical_reader_and_same_identity(tmp_path):
    p=tmp_path/'cache.db';t=StateTap(p,'boot',lambda:100)
    assert send(t,frame())
    result=AiStateReader(p,lambda:100,'boot').status()
    assert result['classification']=='CAT' and result['source_frame_id']==1 and result['producer_epoch']=='producer_A'
    assert result['data_source']=='REAL' and result['simulated'] is False
    assert not send(t,frame()) and not send(t,frame(seq=0))
    with sqlite3.connect(p) as db:assert db.execute('SELECT COUNT(*) FROM ai_latest').fetchone()[0]==1
def test_legacy_stdout_compatibility_and_no_overwrite_of_frame(tmp_path):
    p=tmp_path/'cache.db';t=StateTap(p,'boot',lambda:100)
    assert not t.accept('DETECTIONS CAT=0.9 MODE=latest PROCESSED=1')
    t.accept('ENGINE_CONTRACT=PASS; COCO CAT=15 DOG=16; monitoring only; no actuator path')
    assert t.accept('DETECTIONS CAT=0.99 DOG=0.8 MODE=latest PROCESSED=2')
    assert row(p)['classification']=='DOG'
    assert t.accept('NONE MODE=latest PROCESSED=3') and row(p)['classification']=='NONE'
    assert send(t,frame())
    assert not t.accept('NONE MODE=latest PROCESSED=4')
    assert row(p)['source_frame_id']==1
@pytest.mark.parametrize('mutation',[{'simulated':True},{'data_source':'MOCK'},{'host_boot_id':'other'},
    {'roi_observation_ms':98000,'updated_monotonic_ms':98000},{'updated_monotonic_ms':99999},
    {'source_frame_id':True},{'ai_schema_version':True},{'classification':'OWNER_CAT'},
    {'confidence':float('nan')},{'roi_mode':'ROI_ENABLED','roi_calibrated':False}])
def test_invalid_attribution_or_frame_cannot_replace_good(tmp_path,mutation):
    p=tmp_path/'cache.db';t=StateTap(p,'boot',lambda:100);assert send(t,frame())
    assert not send(t,{**frame(2),**mutation}) and row(p)['source_frame_id']==1
def test_epoch_restart_and_retired_producer_rejected(tmp_path):
    p=tmp_path/'cache.db';t=StateTap(p,'boot',lambda:100)
    assert send(t,frame(10)) and send(t,frame(1,'producer_B'))
    assert not send(t,frame(11)) and row(p)['producer_epoch']=='producer_B'
    assert send(t,{**frame(2,'producer_B'),'health':'DISCONNECTED'})
    assert AiStateReader(p,lambda:100,'boot').status()['classification']=='UNKNOWN'
def test_single_writer_os_lock(tmp_path):
    p=tmp_path/'cache.db'
    with WriterLock(p):
        with pytest.raises(OSError):
            with WriterLock(p):pytest.fail('second writer entered')
    with WriterLock(p):pass
def test_reader_never_presents_explicit_mock_as_real(tmp_path):
    p=tmp_path/'cache.db';t=StateTap(p,'boot',lambda:100)
    assert t.write({**frame(),'simulated':True,'data_source':'SIMULATED'})
    assert AiStateReader(p,lambda:100,'boot').status()['classification']=='UNKNOWN'
def test_duplicate_json_key_rejected(tmp_path):
    t=StateTap(tmp_path/'cache.db','boot',lambda:100)
    assert not t.accept(PREFIX+'{"health":"ONLINE","health":"DISCONNECTED"}')
