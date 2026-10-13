"""Bounded deterministic generative/chaos tests, ACCELERATED HOST SOAK only."""
import random
import sqlite3
from datetime import date, datetime, timedelta, timezone
from threading import Event

import pytest
from fastapi.testclient import TestClient

from app.ai.models import Identity, Recognition
from app.ai.service import ObservationService
from app.analytics.reports import FoodDefinition, FoodTrial, preference_report
from app.analytics.preference import trend
from app.behavior.fusion import SessionFusion, WeightSample
from app.behavior.models import Behavior
from app.behavior.temporal import Prediction, SessionSignal, SignalType, TemporalEngine
from app.config import HardwareConfig
from app.camera.base import CameraFrame
from app.main import create_app
from app.serial_link.link_manager import LinkManager
from app.serial_link.mock_transport import MockEsp32Transport
from app.serial_link.protocol import Command, FeedCode, Frame, FrameStreamDecoder, ProtocolError, decode, encode
from app.serial_link.real_transport import RealEsp32SerialTransport
from app.storage.event_store import Event as StoreEvent, InMemoryEventStore
from app.storage.records import BehaviorRecord, DrinkingSession, FeedingSession
from app.storage.records import FoodType
from app.storage.repositories import RecordRepository
from app.storage.summary import daily_summary
from app.vision.tracking import TrackEvidence, TrackLedger, attribution
from tools.demo_replay import DemoCamera, DemoIdentityModel, DemoBehaviorModel


def test_uart_seeded_round_trip_crc_length_stream_and_maximum_ids():
    rng = random.Random(0xF0CC)
    parser = FrameStreamDecoder()
    expected, actual = [], []
    for i in range(800):
        identifier = (0, 1, 0xFFFFFFFF)[i%3] if i<30 else rng.getrandbits(32)
        payload = rng.randbytes((0, 256, rng.randrange(257))[i%3])
        frame = Frame(identifier, rng.choice(list(Command)), payload)
        raw = encode(frame)
        assert decode(raw) == frame
        damaged = bytearray(raw); damaged[-1] ^= 1
        with pytest.raises(ProtocolError): decode(bytes(damaged))
        with pytest.raises(ProtocolError): decode(raw[:-1])
        expected.append(frame)
        cut = rng.randrange(len(raw)+1)
        actual.extend(parser.feed(raw[:cut], i))
        actual.extend(parser.feed(raw[cut:], i+0.01))
        assert len(parser.buffer) <= parser.max_buffer
    assert actual == expected
    rng = random.Random(90123)
    # Noise/corrupt candidates time out before authoritative next frame.
    for i in range(2000):
        parser.feed(rng.randbytes(rng.randrange(129)), 1000+i)
        parser.feed(b"", 1000+i+0.5)
        frame = Frame(i, Command.PING)
        assert frame in parser.feed(encode(frame), 1000+i+0.6)
        assert len(parser.buffer) <= 512


def test_uint32_exhaustion_duplicates_restart_and_stale_reply(tmp_path):
    path = tmp_path/"ids.db"
    repo = RecordRepository(path)
    now = datetime.now(timezone.utc).isoformat()
    with repo.connection:
        repo.connection.execute("INSERT INTO feed_requests VALUES (?,?,?,?)", (0xFFFFFFFE,"near_max","ERROR",now))
    assert repo.claim_feed("last")[0] == 0xFFFFFFFF
    assert repo.claim_feed("last")[2] is False
    with pytest.raises(OverflowError): repo.claim_feed("cannot_wrap")
    repo.close()
    with TestClient(create_app(db_path=path), raise_server_exceptions=False) as client:
        assert client.post("/api/v1/feed/manual",headers={"Idempotency-Key":"last"}).json()["request_id"] == 0xFFFFFFFF
        assert client.post("/api/v1/feed/manual",headers={"Idempotency-Key":"new"}).status_code == 503
        assert client.get("/api/v1/feed/manual/0").status_code == 400
    class Stale:
        def exchange(self, raw): return encode(Frame(1, Command.FEED_STATUS, b"\x01"))
    link = LinkManager(Stale())
    with pytest.raises(ProtocolError): link.exchange(0xFFFFFFFF, Command.FEED_STATUS)
    assert link.state.value == "DEGRADED"


@pytest.mark.parametrize("day", [date(2024,2,28),date(2024,2,29),date(2025,2,28),date(2026,12,31)])
def test_utc_storage_calendar_rollovers(day):
    repo = RecordRepository(":memory:")
    try:
        first = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)+timedelta(hours=23,minutes=59)
        second = first+timedelta(minutes=2)
        repo.add("drinking",DrinkingSession(session_id="first",started_at=first,duration_seconds=2))
        repo.add("drinking",DrinkingSession(session_id="second",started_at=second,duration_seconds=2))
        assert daily_summary(repo,day)["drinking_sessions"] == 1
        assert daily_summary(repo,second.date())["drinking_sessions"] == 1
        with pytest.raises(ValueError): datetime(2025,2,29,tzinfo=timezone.utc)
    finally: repo.close()


def test_atomic_visit_locked_db_rollback_reopen_and_exact_retry(tmp_path):
    path = tmp_path/"chaos.db"; repo=RecordRepository(path); locker=sqlite3.connect(path)
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    behavior=BehaviorRecord(session_id="atomic",behavior=Behavior.DRINKING,started_at=now,ended_at=now+timedelta(seconds=1))
    drinking=DrinkingSession(session_id="atomic",started_at=now,ended_at=behavior.ended_at)
    try:
        assert repo.connection.execute("PRAGMA journal_mode").fetchone()[0]=="wal"
        assert repo.connection.execute("PRAGMA busy_timeout").fetchone()[0]==2000
        repo.connection.execute("PRAGMA busy_timeout=25")  # bounded deliberate lock injection only
        locker.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.OperationalError): repo.add_visit(behavior,drinking)
        locker.rollback()
        repo.connection.set_authorizer(lambda action,a,*rest: sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_INSERT and a=="typed_records" else sqlite3.SQLITE_OK)
        with pytest.raises(sqlite3.DatabaseError): repo.add_visit(behavior,drinking)
        repo.connection.set_authorizer(None)
        assert repo.count("behavior")==repo.count("drinking")==0
        assert repo.add_visit(behavior,drinking)
        assert not repo.add_visit(behavior,drinking)
        with pytest.raises(ValueError): repo.add_visit(behavior.model_copy(update={"duration_seconds":99}),drinking)
    finally: locker.close(); repo.close()
    again=RecordRepository(path)
    try: assert again.count("behavior")==again.count("drinking")==1
    finally: again.close()


def test_unsupported_database_revision_reports_its_real_cause(tmp_path):
    path=tmp_path/"future.db"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=999")
    with pytest.raises(RuntimeError,match="unsupported record schema version"):
        RecordRepository(path)


def test_storage_failure_before_request_prevents_any_intent(monkeypatch):
    app=create_app(store=InMemoryEventStore())
    with TestClient(app,raise_server_exceptions=False) as client:
        def fail(*args): raise sqlite3.OperationalError("synthetic disk write failure")
        monkeypatch.setattr(app.state.records,"claim_feed",fail)
        assert client.post("/api/v1/feed/manual").status_code==503
        assert app.state.transport.feeds=={}
        assert client.get("/api/v1/health").status_code==200


def test_generic_event_failure_keeps_durable_terminal_truth(monkeypatch):
    app=create_app(store=InMemoryEventStore())
    with TestClient(app,raise_server_exceptions=False) as client:
        key={"Idempotency-Key":"stable"}
        identifier=client.post("/api/v1/feed/manual",headers=key).json()["request_id"]
        app.state.transport.complete_feed(identifier,FeedCode.SUCCESS)
        def fail(*args): raise sqlite3.OperationalError("synthetic event failure")
        monkeypatch.setattr(app.state.store,"append",fail)
        assert client.get("/api/v1/status").status_code==503
        assert client.post("/api/v1/feed/manual",headers=key).json()["state"]=="SUCCESS"
        assert client.get("/api/v1/status").json()["feeds"][0]["state"]=="SUCCESS"
        assert app.state.records.count("feeding")==1
        assert len(app.state.transport.feeds)==1


def test_restart_pending_and_peer_reset_never_resend(tmp_path):
    path=tmp_path/"pending.db"; peer=MockEsp32Transport(); header={"Idempotency-Key":"uncertain"}
    with TestClient(create_app(db_path=path,transport=peer)) as client:
        identifier=client.post("/api/v1/feed/manual",headers=header).json()["request_id"]
    peer.feeds.clear()  # simulate peer volatile result cache reset
    with TestClient(create_app(db_path=path,transport=peer)) as client:
        assert client.post("/api/v1/feed/manual",headers=header).json()["request_id"]==identifier
        assert client.get("/api/v1/status").json()["feeds"][0]["state"]=="PENDING"
        assert peer.feeds=={}


@pytest.mark.parametrize("days",[1,7],ids=["ACCELERATED_HOST_SOAK_24H","ACCELERATED_HOST_SOAK_7D"])
def test_accelerated_host_soak_sparse_events_days_bounds_and_faults(days):
    from jetson.tests.test_observation_pipeline import SyntheticCamera,SyntheticIdentityModel
    times=[]; origin=datetime(2026,12,31,tzinfo=timezone.utc)
    for hour in range(days*24):
        base=hour*3600
        times.extend(base+x for x in (0,0.6,1.2,3,10,10.6,11.2,13))
    camera=SyntheticCamera(times)
    # UTC calendar spans midnight/year changes; monotonic event offsets remain independent.
    def read():
        if camera.index==len(times):
            camera.eof=True
            return None
        index=camera.index; camera.index+=1
        return CameraFrame(origin+timedelta(seconds=times[index]),bytes([index%8])*12,2,2,True)
    camera.read=read
    class Behaviors:
        def predict(self,frame,identity):
            from app.behavior.models import BehaviorObservation
            kind=([Behavior.EATING]*3+[Behavior.LEAVING]+[Behavior.DRINKING]*3+[Behavior.LEAVING])[frame.pixels[0]]
            return BehaviorObservation(timestamp=frame.captured_at,identity=identity,behavior=kind,confidence=0.9,food_roi=True,water_roi=True)
    app=create_app(store=InMemoryEventStore(max_events=8),camera=camera,identity_model=SyntheticIdentityModel(),
        behavior_model=Behaviors(),hardware=HardwareConfig(camera_provider="VIDEO",video_file="synthetic"),pipeline_source="SYNTHETIC_TEST_DATA")
    app.state.records.max_rows=8  # deliberate retention/ledger-capacity pressure, not production override
    app.state.records.add("food_type",FoodType(food_type="soak_food"))
    with TestClient(app) as client:
        pipeline=app.state.pipeline
        for i in range(len(times)):
            app.state.transport.online=i%17!=0
            assert pipeline.process_one_frame()=="PROCESSED"
            if i%17==0:
                assert client.get("/api/v1/status").json()["esp32_online"] is False
            if i%8==7:
                app.state.transport.online=True
                attempt=client.post("/api/v1/feed/manual",headers={"Idempotency-Key":f"hour_{i//8}"})
                assert attempt.status_code in (202,503)
                if attempt.status_code==202:
                    app.state.transport.complete_feed(attempt.json()["request_id"],FeedCode.SUCCESS)
                client.get("/api/v1/status")
                assert client.get("/api/v1/preferences").json()[0]["status"]=="INSUFFICIENT_DATA"
                app.state.store.append(StoreEvent(kind="SOAK"))
        pipeline.stop()
        assert pipeline.frames==days*24*8 and pipeline.sessions==days*24*2
        assert len(pipeline.latencies)<=256 and pipeline._pending_write is None
        assert len(pipeline.tracker.approach)<=4 and len(pipeline.tracker.last_end)<=4
        assert len(app.state.store.list())<=8 and len(app.state.feeds.link.pending)<=8
        visits=app.state.records.list("behavior",limit=1000)
        assert len({v.session_id for v in visits})==len(visits)
        assert app.state.records.count("behavior")<=8 and app.state.records.count("drinking")<=8
        assert pipeline.status()["automatic_feed_authorized"] is False and len(app.state.transport.feeds)<=8
        for offset in range(days+1):
            report=daily_summary(app.state.records,(origin+timedelta(days=offset)).date())
            assert report["reliable_food_consumed_grams"] is None
    # UTC-span accelerated sparse-event workload, NOT 24h/7d wall-time reliability.


def test_managed_shutdown_reports_blocked_worker_then_cleans_after_release():
    entered,release=Event(),Event()
    class Slow(DemoIdentityModel):
        def predict(self,frame):
            entered.set()
            if not release.wait(3): raise RuntimeError("test release missing")
            return super().predict(frame)
    app=create_app(store=InMemoryEventStore(),camera=DemoCamera(6),identity_model=Slow(),behavior_model=DemoBehaviorModel())
    service=app.state.observations
    try:
        service.start_background(max_frames=2,interval=0.001)
        assert entered.wait(1)
        with pytest.raises(RuntimeError): service.run(max_frames=1)
        assert not service.stop(timeout=0.01)
        assert service.status()["state"]=="FAULTED" and service.status()["worker_alive"]
    finally:
        release.set(); assert service.stop(timeout=3)
        assert not service.status()["worker_alive"]
        app.state.records.close(); app.state.store.close()


def test_shutdown_during_visit_write_does_not_close_under_worker(monkeypatch):
    entered,release=Event(),Event()
    app=create_app(store=InMemoryEventStore(),camera=DemoCamera(6),identity_model=DemoIdentityModel(),
        behavior_model=DemoBehaviorModel(),hardware=HardwareConfig(camera_provider="VIDEO",video_file="synthetic"))
    write=app.state.records.add_visit
    def delayed(*args):
        entered.set()
        if not release.wait(3): raise sqlite3.OperationalError("test write release missing")
        return write(*args)
    monkeypatch.setattr(app.state.records,"add_visit",delayed)
    service=app.state.observations
    try:
        service.start_background(max_frames=7,interval=0.001)
        assert entered.wait(1)
        assert not service.stop(timeout=0.01)
        assert service.status()["state"]=="FAULTED" and app.state.records.health()=="READY"
    finally:
        release.set(); assert service.stop(timeout=3)
        assert not service.status()["worker_alive"]
        assert app.state.records.count("behavior")==1
        app.state.records.close(); app.state.store.close()


def test_wall_forward_and_backward_jumps_do_not_inflate_event_duration():
    now=datetime(2026,1,1,tzinfo=timezone.utc); engine=TemporalEngine()
    for mono,wall in ((0,now),(0.6,now+timedelta(days=30)),(1.2,now-timedelta(days=30))):
        engine.update(Prediction(timestamp=wall,monotonic_seconds=mono,identity=Identity.OWNER_CAT,
            behavior=Behavior.DRINKING,confidence=0.9,water_roi=True))
    finished=engine.close_session()[0]
    assert finished.duration_seconds==1.2 and finished.ended_at==now+timedelta(seconds=1.2)


def test_crossing_and_identity_flips_do_not_join_subject_sessions():
    now=datetime(2026,1,1,tzinfo=timezone.utc); engine=TemporalEngine(); ledger=TrackLedger()
    a=TrackEvidence("a",Identity.OWNER_CAT,Behavior.EATING); b=TrackEvidence("b",Identity.OTHER_CAT,Behavior.EATING)
    ledger.update([a,b],0); ledger.update([b,a],0.6)
    assert attribution([b,a])["subject_track"]=="AMBIGUOUS"
    assert [row["first_seen"] for row in ledger.update([a,b],1.2)]==[0,0]
    events=[]
    for mono,identity in ((0,Identity.OWNER_CAT),(0.6,Identity.OWNER_CAT),(0.9,Identity.OTHER_CAT),(2.3,Identity.OTHER_CAT),(2.9,Identity.OTHER_CAT)):
        events.extend(engine.update(Prediction(timestamp=now+timedelta(seconds=mono),monotonic_seconds=mono,
            identity=identity,behavior=Behavior.EATING,confidence=0.9,food_roi=True)))
    events.extend(engine.close_session())
    ended=[e for e in events if e.signal==SignalType.END]
    assert [e.identity for e in ended]==[Identity.OWNER_CAT,Identity.OTHER_CAT]
    assert ended[0].ended_at<=ended[1].started_at


@pytest.mark.parametrize("identity",[Identity.UNKNOWN,Identity.OTHER_CAT])
def test_legacy_preference_does_not_treat_non_owner_weight_as_clean_owner_evidence(identity):
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    sessions=[FeedingSession(session_id=f"weight-{i}",food_type="food",requested_at=now,cat_identity=identity,
        source="VALIDATED_SENSOR",dispensed_grams=20,estimated_consumed_grams=10,
        approach_delay_seconds=1,repeat_visits=1) for i in range(3)]
    assert trend("food",sessions)["status"]=="INSUFFICIENT_DATA"


@pytest.mark.parametrize("scenario",["camera","model","serial_during_eating","database_after_confirm"])
def test_composite_failure_matrix_preserves_health_and_no_actions(scenario,monkeypatch):
    app=create_app(store=InMemoryEventStore(),camera=DemoCamera(24),identity_model=DemoIdentityModel(),
        behavior_model=DemoBehaviorModel(),hardware=HardwareConfig(camera_provider="VIDEO",video_file="synthetic"))
    with TestClient(app,raise_server_exceptions=False) as client:
        pipeline=app.state.pipeline
        if scenario=="camera": monkeypatch.setattr(pipeline.camera,"open",lambda:False)
        if scenario=="model":
            def bad(frame): raise RuntimeError("synthetic model error")
            monkeypatch.setattr(pipeline.identity,"predict",bad)
        if scenario=="serial_during_eating": app.state.transport.online=False
        if scenario=="database_after_confirm":
            def failed(*args): raise sqlite3.OperationalError("synthetic database fault")
            monkeypatch.setattr(app.state.records,"add_visit",failed)
        pipeline.sleep=lambda _:None
        outcome=app.state.observations.run(max_frames=25,max_failures=2,interval=0.001)
        assert client.get("/api/v1/health").status_code==200
        assert app.state.transport.feeds=={} and not pipeline.status()["automatic_feed_authorized"]
        assert outcome["state"]==("STOPPED" if scenario=="serial_during_eating" else "FAULTED")
        if scenario=="database_after_confirm": assert pipeline.status()["pending_writes"]==1


def test_temporal_oscillation_identity_flip_tracks_and_missing_confounders():
    now=datetime(2026,1,1,tzinfo=timezone.utc); engine=TemporalEngine()
    starts=[]; ends=[]
    for i,kind in enumerate([Behavior.EATING,Behavior.EATING,Behavior.OTHER,Behavior.EATING,Behavior.UNKNOWN,Behavior.EATING,Behavior.LEAVING]):
        events=engine.update(Prediction(timestamp=now+timedelta(seconds=i*0.6),monotonic_seconds=i*0.6,
            identity=Identity.OWNER_CAT,behavior=kind,confidence=0.9,food_roi=True))
        starts.extend(e for e in events if e.signal==SignalType.START); ends.extend(e for e in events if e.signal==SignalType.END)
    ends.extend(engine.close_session())
    assert len(starts)==len(ends)==1 and engine.active is None
    ledger=TrackLedger(ttl_seconds=1)
    for ids in ([Identity.OWNER_CAT,Identity.OTHER_CAT],[Identity.OTHER_CAT]*2):
        tracks=[TrackEvidence(str(i),identity,Behavior.EATING) for i,identity in enumerate(ids)]
        assert attribution(tracks)["subject_track"]=="AMBIGUOUS"
    single=TrackEvidence("one",Identity.OWNER_CAT,Behavior.DRINKING)
    ledger.update([single],0); assert ledger.update([],2)==[]
    assert ledger.update([single],3)[0]["first_seen"]==3
    food=FoodDefinition(food_id="food",display_name="Fixture")
    trials=[FoodTrial(feeding=FeedingSession(session_id=f"s-{i}",requested_at=now,food_type="food",source="VALIDATED_SENSOR",
        cat_identity=Identity.OWNER_CAT,dispensed_grams=20,estimated_consumed_grams=10,approach_delay_seconds=3,repeat_visits=1),
        subject_track="one",attribution="CLEAN") for i in range(3)]
    assert preference_report(food,trials)["analysis"]["status"]=="INSUFFICIENT_DATA"


def test_unconfirmed_candidate_cannot_bridge_an_unobserved_long_gap():
    now=datetime(2026,1,1,tzinfo=timezone.utc); engine=TemporalEngine()
    def positive(seconds):
        return Prediction(timestamp=now+timedelta(seconds=seconds),monotonic_seconds=seconds,
            identity=Identity.OWNER_CAT,behavior=Behavior.EATING,confidence=0.9,food_roi=True)
    assert engine.update(positive(0))==[]
    assert engine.update(positive(10))==[]
    started=engine.update(positive(10.6))[0]
    assert started.started_at==now+timedelta(seconds=10)
    assert engine.close_session()[0].duration_seconds==0.6


def test_fusion_impossible_disappearance_and_stale_post_are_absent():
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    start=SessionSignal(signal=SignalType.START,session_id="e",identity=Identity.OWNER_CAT,behavior=Behavior.EATING,started_at=now)
    end=start.model_copy(update={"signal":SignalType.END,"ended_at":now+timedelta(seconds=2)})
    feed=FeedingSession(session_id="f",requested_at=now,cat_identity=Identity.OWNER_CAT,dispensed_grams=10)
    before=[WeightSample(50,True,now)]*3; after=[WeightSample(0,True,end.ended_at)]*3
    assert SessionFusion().fuse(start,end,feeding=feed,weight_before=before,weight_after=after).estimated_food_consumed_grams is None
    stale=[WeightSample(40,True,now+timedelta(minutes=5))]*3
    assert SessionFusion().fuse(start,end,feeding=feed,weight_before=before,weight_after=stale).estimated_food_consumed_grams is None


@pytest.mark.parametrize("value",[float("nan"),float("inf"),-1,1000])
def test_serial_timeout_configuration_cannot_create_infinite_wait(value):
    with pytest.raises(ValueError): RealEsp32SerialTransport("synthetic",timeout=value)
