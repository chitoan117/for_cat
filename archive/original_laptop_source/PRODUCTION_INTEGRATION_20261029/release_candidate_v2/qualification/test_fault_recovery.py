import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import sys
import pytest
from test_ai_contract import StateTap,AiStateReader,frame,send,row
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'LIVE_CAMERA_REMOTE_PREP_20261028'))
from synthetic_video import render_frame
from app.camera.live_stream import FrameHub,VideoSettings
from app.dry_run_requests import DryRunRequests
from app.bowl_mass import BowlMassTracker,Context,GrossSample

def test_sqlite_busy_atomicity_and_retry_same_frame(tmp_path):
    p=tmp_path/'cache.db';t=StateTap(p,'boot',lambda:100);assert send(t,frame())
    with sqlite3.connect(p) as locked:
        locked.execute('BEGIN EXCLUSIVE')
        assert not send(t,frame(2)) and t.sequence==1 and t.storage_errors==1
        assert AiStateReader(p,lambda:100,'boot').status()['classification']=='UNKNOWN'
        locked.rollback()
    assert row(p)['source_frame_id']==1
    assert send(t,frame(2)) and t.sequence==2
def test_database_io_failure_does_not_claim_commit_or_recover_automatically(tmp_path,monkeypatch):
    import app.ai_frame_contract as contract
    p=tmp_path/'cache.db';clock=[100.];t=StateTap(p,'boot',lambda:clock[0]);assert send(t,frame())
    original=contract.sqlite3.connect
    def fail(*a,**k):raise sqlite3.OperationalError('injected I/O failure')
    monkeypatch.setattr(contract.sqlite3,'connect',fail)
    assert not send(t,frame(2)) and t.sequence==1
    monkeypatch.setattr(contract.sqlite3,'connect',original)
    clock[0]=102
    assert AiStateReader(p,lambda:clock[0],'boot').status()['health']=='STALE'
    assert not send(t,frame(2)) # old frame cannot become GOOD simply because DB recovered
    assert send(t,frame(2,stamp=102000))
def test_transaction_failure_retains_complete_metadata(tmp_path):
    p=tmp_path/'cache.db';t=StateTap(p,'boot',lambda:100);assert send(t,frame())
    with sqlite3.connect(p) as db:
        db.execute("CREATE TRIGGER reject_ai BEFORE UPDATE ON ai_latest BEGIN SELECT RAISE(ABORT,'injected'); END")
    assert not send(t,frame(2,species='DOG'))
    assert row(p)['classification']=='CAT' and row(p)['source_frame_id']==1
def test_startup_trt_failure_crash_eof_and_recovery(tmp_path):
    p=tmp_path/'cache.db';clock=[100.];t=StateTap(p,'boot',lambda:clock[0])
    assert t.disconnected() # before TensorRT construction, and on pipe EOF
    assert AiStateReader(p,lambda:100,'boot').status()['classification']=='UNKNOWN'
    assert not t.accept('TensorRT could not initialize')
    assert send(t,frame())
    assert t.disconnected()
    assert AiStateReader(p,lambda:100,'boot').status()['classification']=='UNKNOWN'
    clock[0]=101
    assert send(t,frame(1,'after_crash',stamp=101000))
    assert AiStateReader(p,lambda:101,'boot').status()['producer_epoch']=='after_crash'
def test_none_unknown_do_not_retain_cat(tmp_path):
    p=tmp_path/'cache.db';t=StateTap(p,'boot',lambda:100)
    for seq,species in enumerate(('CAT','NONE','UNKNOWN','DOG'),1):
        assert send(t,frame(seq,species=species))
        assert AiStateReader(p,lambda:100,'boot').status()['classification']==species
def test_camera_api_restart_empty_hub_and_reconnect():
    async def go():
        now=[100.];settings=VideoSettings(enabled=True,source='SIMULATED')
        old=FrameHub(settings,lambda:now[0]);data,meta=render_frame(1,100000)
        await old.publish(data,meta);token=old.acquire();assert token in old.viewers
        await old.close();new=FrameHub(settings,lambda:now[0])
        assert not old.viewers and new.status()['status']=='CAMERA_OFFLINE'
        now[0]=103;data,meta=render_frame(1,103000);meta['producer_epoch']='reconnected'
        await new.publish(data,meta);assert new.status()['status']=='CAMERA_ONLINE'
        await new.close()
    asyncio.run(go())
def test_ai_cache_and_concurrent_manual_scheduled_inbox_do_not_execute(tmp_path):
    p=tmp_path/'shared.db';tap=StateTap(p,'boot',lambda:100);assert send(tap,frame())
    inbox=DryRunRequests(p);inbox.enqueue('init','MANUAL','APP')
    def worker(kind):
        if kind=='AI':return [send(tap,frame(i)) for i in range(2,8)]
        return [inbox.enqueue('manual_one' if kind=='MANUAL' else 'scheduled_one',kind,'APP' if kind=='MANUAL' else '') for _ in range(4)]
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(worker,('AI','MANUAL','SCHEDULED')))
    assert results
    restarted=DryRunRequests(p)
    for identity in ('manual_one','scheduled_one'):
        pending=restarted.get(identity)
        assert pending['decision'] is None and pending['request']['actual_dispensed_grams'] is None
        assert pending['request']['actuator_execution'] is False
    with sqlite3.connect(p) as db:
        assert db.execute('SELECT COUNT(*) FROM feed_dry_run_requests').fetchone()[0]==3
        assert db.execute('SELECT COUNT(*) FROM ai_latest').fetchone()[0]==1
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

def test_food_continues_falling_after_fake_servo_closed_blocks_success():
    context=Context('FAULT_TEST','INOX','PAIR','BOOT',calibration_current_mount=True)
    def window(g,now):return [GrossSample(g,now-900+i*300,context) for i in range(4)]
    tracker=BowlMassTracker(context)
    tracker.confirm_empty_bowl(window(95,1900),1900,owner_confirmed_empty=True)
    tracker.begin_dispense(window(95,2900),2900)
    # Fake actuator has just closed at gross130; later settled mass includes1g
    # still in flight. A close command alone cannot be interpreted as SUCCESS.
    fake_servo_closed=True
    assert fake_servo_closed
    with pytest.raises(ValueError,match='OVERSHOOT'):
        tracker.finish_dispense(window(131,4900),4900)
    assert tracker.phase=='BLOCKED' and tracker.snapshot()['actuation_authorized'] is False
