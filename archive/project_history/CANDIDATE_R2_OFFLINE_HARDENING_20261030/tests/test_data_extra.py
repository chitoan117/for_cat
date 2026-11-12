import sys,sqlite3
from pathlib import Path
from datetime import datetime,timezone
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'candidate/backend'))
from app.api.routes import FeedService
from app.serial_link.mock_transport import MockEsp32Transport
from app.serial_link.protocol import FeedCode
from app.storage.event_store import SQLiteEventStore
from app.storage.repositories import RecordRepository
from app.storage.records import DrinkingSession,BehaviorRecord
from app.behavior.models import Behavior
@pytest.mark.parametrize('actual,controller_state',[(38,'FAULT'),(41,'COMPLETE')])
def test_mass_qualification_alone_cannot_override_other_gates(tmp_path,actual,controller_state):
    path=tmp_path/'mass.sqlite3';store=SQLiteEventStore(path);repo=RecordRepository(path);t=MockEsp32Transport()
    meta={'source':'SIMULATED','physical_pass':False,'actual_dispensed_grams':actual,'latest_observed_grams':actual,'state':controller_state}
    try:
        service=FeedService(t,store,records=repo,simulation_result_reader=lambda _:meta)
        ack=service.request_feed();t.complete_feed(ack.request_id,FeedCode.SUCCESS)
        result=service.status().feeds[0];assert result.state=='ERROR' and result.actual_dispensed_grams==actual
        assert result.mass_in_band==(actual==38)
    finally:repo.close();store.close()
def test_drinking_without_evidence_is_not_materialized(tmp_path):
    repo=RecordRepository(tmp_path/'drink.sqlite3');now=datetime.now(timezone.utc)
    try:
        behavior=BehaviorRecord(session_id='SYNTHETIC_VISIT',started_at=now,behavior=Behavior.DRINKING,source='UNVALIDATED')
        drink=DrinkingSession(session_id=behavior.session_id,started_at=now,source='UNVALIDATED')
        with pytest.raises(ValueError):repo.add_visit(behavior,drink)
        assert repo.count('drinking')==0 and repo.count('behavior')==0
    finally:repo.close()
def test_conflicting_terminal_retry_does_not_overwrite(tmp_path):
    path=tmp_path/'retry.sqlite3';store=SQLiteEventStore(path);repo=RecordRepository(path);t=MockEsp32Transport()
    meta={'source':'SIMULATED','physical_pass':False,'actual_dispensed_grams':38,'latest_observed_grams':38,'state':'COMPLETE'}
    service=FeedService(t,store,records=repo,simulation_result_reader=lambda _:meta)
    try:
        ack=service.request_feed();t.complete_feed(ack.request_id,FeedCode.SUCCESS);service.status()
        meta['actual_dispensed_grams']=40;meta['latest_observed_grams']=40
        with pytest.raises(ValueError):service._set(ack.request_id,service.feeds[ack.request_id],final_received=True)
        assert repo.get('feeding','feed-1').dispensed_grams==38
        assert sum(x.state=='SUCCESS' for x in store.list())==1
    finally:repo.close();store.close()
def test_restart_pending_does_not_resend_request(tmp_path):
    path=tmp_path/'pending.sqlite3';t=MockEsp32Transport();a=SQLiteEventStore(path);b=RecordRepository(path)
    service=FeedService(t,a,records=b);first=service.request_feed('SYNTHETIC_PENDING');b.close();a.close()
    a=SQLiteEventStore(path);b=RecordRepository(path)
    try:
        resumed=FeedService(t,a,records=b);assert resumed.request_feed('SYNTHETIC_PENDING')==first
        assert len(t.feeds)==1 and b.count('feeding')==0
    finally:b.close();a.close()
