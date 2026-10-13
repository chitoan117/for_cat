import re
import time
from collections import OrderedDict, deque
from datetime import date, datetime, timezone
from enum import Enum
from threading import RLock

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from typing import Literal

from app.serial_link.protocol import Command, FeedCode, Frame, ProtocolError
from app.serial_link.link_manager import LinkManager
from app.observability import get_logger
from app.serial_link.transport import SerialTransport
from app.storage.event_store import Event, EventStore
from app.storage.records import FeedingSession
from app.storage.repositories import RecordRepository
from app.storage.summary import daily_summary
from app.storage.history import history
from app.analytics.preference import PreferencePolicy, trend
from app.status import ComponentState, LinkState

router = APIRouter(prefix="/api/v1")


class FeedState(str, Enum):
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class FeedResult(BaseModel):
    request_id: int
    state: FeedState


class ApiError(BaseModel):
    detail: str


class Status(BaseModel):
    esp32_online: bool
    feeds: list[FeedResult]
    camera: ComponentState = ComponentState.MOCK
    esp32: ComponentState = ComponentState.MOCK
    sensors: ComponentState = ComponentState.NOT_CONNECTED
    link_state: LinkState = LinkState.UNCONFIGURED
    link_stats: dict[str, int] = Field(default_factory=dict)
    simulated_water: dict[str, str | bool] | None = None
    software_status: Literal["SOFTWARE_OK"] = "SOFTWARE_OK"
    hardware_validation: Literal["HARDWARE_NOT_VALIDATED"] = "HARDWARE_NOT_VALIDATED"
    ai: dict = Field(default_factory=dict)
    readiness: dict = Field(default_factory=dict)
    observation_service: dict = Field(default_factory=dict)


class FeedService:
    def __init__(self, transport: SerialTransport, store: EventStore, allow_feed_requests: bool = True,
                 records: RecordRepository | None = None):
        self.transport = transport
        self.link = LinkManager(transport, max_pending=min(store.max_events, 256))
        self.store = store
        self.records = records
        self.allow_feed_requests = allow_feed_requests
        self.lock = RLock()
        self.feeds: OrderedDict[int, FeedState] = OrderedDict()
        self.request_times: dict[int, datetime] = {}
        self.keys: OrderedDict[str, int] = OrderedDict()
        self.logger = get_logger()
        self.recent_requests: deque[float] = deque(maxlen=30)
        previous = list(reversed(store.list(limit=store.max_events, kind="FEED")))
        for event in previous:
            if event.request_id is not None and event.state is not None:
                self.feeds[event.request_id] = FeedState(event.state)
                if event.state == FeedState.REQUEST_RECEIVED:
                    self.request_times[event.request_id] = event.timestamp
                key = event.details.get("client_key")
                if key:
                    self.keys[key] = event.request_id
        if self.records is not None:
            for request_id, state, client_key, created_at in reversed(self.records.recent_feeds(min(store.max_events, 256))):
                self.feeds[request_id] = FeedState(state)
                self.request_times.setdefault(request_id, datetime.fromisoformat(created_at))
                if client_key:
                    self.keys[client_key] = request_id
        for request_id, state in self.feeds.items():
            if state == FeedState.PENDING and len(self.link.pending) < 256:
                self.link.mark_pending(request_id)
        self.next_id = max(self.feeds, default=0) + 1

    def _set(self, request_id: int, state: FeedState, client_key: str | None = None) -> None:
        event = Event(kind="FEED", request_id=request_id, state=state,
                      details={"client_key": client_key} if client_key else {})
        terminal = None
        if state in (FeedState.SUCCESS, FeedState.REJECTED, FeedState.ERROR):
            terminal = FeedingSession(session_id=f"feed-{request_id}",
                requested_at=self.request_times.get(request_id, event.timestamp), result=state.value,
                source=("SOFTWARE_SIMULATOR" if type(self.transport).__module__.startswith("app.simulator")
                        else "MOCK" if self.allow_feed_requests else "SERIAL_REQUEST_BLOCKED"))
        if self.records is not None:
            self.records.commit_feed_state(request_id, state.value, terminal)
        self.store.append(event)
        self.feeds[request_id] = state
        if state == FeedState.REQUEST_RECEIVED:
            self.request_times[request_id] = event.timestamp
        self.logger.info("feed state changed", extra={"component": "feed", "request_id": request_id,
                                                      "event_type": state.value})
        if state == FeedState.PENDING:
            self.link.mark_pending(request_id)
        elif state in (FeedState.SUCCESS, FeedState.REJECTED, FeedState.ERROR):
            self.link.mark_done(request_id)
        while len(self.feeds) > self.store.max_events:
            terminal = next((key for key, value in self.feeds.items()
                             if value not in (FeedState.PENDING, FeedState.REQUEST_RECEIVED)), None)
            if terminal is None:
                break
            del self.feeds[terminal]
            self.request_times.pop(terminal, None)
        self.keys = OrderedDict((key, value) for key, value in self.keys.items()
                                if value in self.feeds)

    def _exchange(self, request_id: int, command: Command) -> Frame:
        return self.link.exchange(request_id, command)

    def request_feed(self, client_key: str | None = None) -> FeedResult:
        with self.lock:
            if client_key is not None:
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", client_key):
                    raise HTTPException(status_code=400, detail="invalid Idempotency-Key")
                if self.records is not None:
                    prior = self.records.find_feed(client_key=client_key)
                    if prior is not None:
                        return FeedResult(request_id=prior[0], state=FeedState(prior[1]))
                if client_key in self.keys:
                    key_id = self.keys[client_key]
                    return FeedResult(request_id=key_id, state=self.feeds[key_id])
            now = time.monotonic()
            while self.recent_requests and now - self.recent_requests[0] >= 60:
                self.recent_requests.popleft()
            if len(self.recent_requests) >= self.recent_requests.maxlen:
                raise HTTPException(status_code=429, detail="feed request rate limit exceeded")
            if len(self.link.pending) >= min(self.store.max_events, 256) or (
                len(self.feeds) >= self.store.max_events and all(
                state in (FeedState.PENDING, FeedState.REQUEST_RECEIVED) for state in self.feeds.values()
            )):
                raise HTTPException(status_code=503, detail="pending request capacity reached")
            if self.records is None and self.next_id > 0xFFFFFFFF:
                raise HTTPException(status_code=503, detail="request ID space exhausted")
            if self.records is not None:
                try:
                    request_id, saved_state, is_new = self.records.claim_feed(client_key)
                    if not is_new:
                        return FeedResult(request_id=request_id, state=FeedState(saved_state))
                except OverflowError as exc:
                    raise HTTPException(status_code=503, detail=str(exc)) from exc
            else:
                request_id = self.next_id
            self.recent_requests.append(now)
            self.next_id = max(self.next_id, request_id + 1)
            self._set(request_id, FeedState.REQUEST_RECEIVED, client_key)
            if client_key is not None:
                self.keys[client_key] = request_id
            if not self.allow_feed_requests:
                self._set(request_id, FeedState.REJECTED)
                return FeedResult(request_id=request_id, state=FeedState.REJECTED)
            try:
                reply = self._exchange(request_id, Command.FEED_REQUEST)
                if reply.command == Command.NACK:
                    state = FeedState.REJECTED
                elif reply.command == Command.ACK and reply.payload == bytes([Command.FEED_REQUEST]):
                    state = FeedState.PENDING
                else:
                    state = FeedState.ERROR
            except (ConnectionError, TimeoutError, ProtocolError, ValueError):
                state = FeedState.ERROR
            self._set(request_id, state)
            return FeedResult(request_id=request_id, state=state)

    def status(self) -> Status:
        with self.lock:
            if self.records is not None:
                for request_id in list(self.feeds):
                    prior = self.records.find_feed(request_id=request_id)
                    if prior is not None and prior[1] in ("SUCCESS", "REJECTED", "ERROR"):
                        self.feeds[request_id] = FeedState(prior[1])
                        self.link.mark_done(request_id)
            try:
                system = self._exchange(0, Command.GET_STATUS)
                online = system.command == Command.SYSTEM_STATUS and system.payload == b"\x01"
                if not online:
                    self.link.state = LinkState.DEGRADED
            except (ConnectionError, TimeoutError, ProtocolError, ValueError):
                online = False
            if online:
                for request_id, state in list(self.feeds.items()):
                    if state != FeedState.PENDING:
                        continue
                    try:
                        reply = self._exchange(request_id, Command.FEED_STATUS)
                        if reply.command == Command.FEED_STATUS and len(reply.payload) == 1:
                            code = FeedCode(reply.payload[0])
                            if code != FeedCode.PENDING:
                                self._set(request_id, FeedState[code.name])
                        # An ACK or NACK is not an operation result; keep PENDING.
                    except (ConnectionError, TimeoutError, ProtocolError, ValueError):
                        pass  # Unknown outcome remains pending; never invent success.
            if self.link.state == LinkState.OFFLINE:
                online = False  # link can vanish after GET_STATUS, during a result poll
            return Status(esp32_online=online, feeds=[FeedResult(request_id=k, state=v) for k, v in self.feeds.items()],
                          link_state=self.link.state, link_stats=self.link.stats())

    def get(self, request_id: int) -> FeedResult:
        with self.lock:
            prior = self.records.find_feed(request_id=request_id) if self.records is not None else None
            if prior is not None:
                return FeedResult(request_id=prior[0], state=FeedState(prior[1]))
            if request_id not in self.feeds:
                prior = self.records.find_feed(request_id=request_id) if self.records is not None else None
                if prior is not None:
                    return FeedResult(request_id=prior[0], state=FeedState(prior[1]))
                raise HTTPException(status_code=404, detail="feed request not found or no longer retained")
            return FeedResult(request_id=request_id, state=self.feeds[request_id])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/status", response_model=Status)
def status(request: Request):
    result = request.app.state.feeds.status()
    pipeline = request.app.state.pipeline
    try:
        result.camera = (pipeline.camera_state if pipeline.frames or pipeline.running else
                         ComponentState(request.app.state.camera.health()))
    except (ValueError, OSError, RuntimeError):
        result.camera = ComponentState.FAULT
    result.esp32 = (ComponentState.MOCK if request.app.state.esp32_mode == "MOCK"
                    else ComponentState.DEGRADED if result.link_state == LinkState.DEGRADED
                    else ComponentState.ONLINE if result.esp32_online else ComponentState.OFFLINE)
    if type(request.app.state.transport).__module__.startswith("app.simulator"):
        water = request.app.state.transport.water
        result.simulated_water = {"state": water.state.value, "pump_simulated_on": water.pump_on}
    result.ai = pipeline.status()
    result.observation_service = request.app.state.observations.status()
    db_state = request.app.state.records.health()
    observation_ready = pipeline.running and pipeline.db_state == "READY" and \
                        pipeline.camera_state in (ComponentState.ONLINE, ComponentState.MOCK) and \
                        pipeline.ai_state not in (ComponentState.DEGRADED, ComponentState.FAULT, ComponentState.NOT_CONFIGURED)
    result.readiness = {"api": "READY", "database": db_state,
                        "observations": "PARTIAL" if observation_ready else "NOT_READY",
                        "esp32_link": result.link_state.value,
                        "real_ai": "UNVERIFIED", "hardware": "UNVERIFIED"}
    return result


@router.get("/readiness")
def readiness(request: Request):
    # Passive cached readiness: never starts camera, serial or GPU runtime.
    pipeline = request.app.state.pipeline
    database = request.app.state.records.health()
    link_ready = (request.app.state.hardware.esp32_transport == "MOCK" or
                  request.app.state.feeds.link.state == LinkState.ONLINE)
    return {"api": "READY", "database": database,
            "camera": pipeline.camera_state.value, "ai": pipeline.ai_state.value,
            "esp32_link": request.app.state.feeds.link.state.value,
            "observation_service": request.app.state.observations.state.value,
            "ready": link_ready and database == "READY" and pipeline.running and pipeline.db_state == "READY" and
                     pipeline.camera_state in (ComponentState.MOCK, ComponentState.ONLINE) and
                     pipeline.ai_state in (ComponentState.MOCK, ComponentState.NOT_VALIDATED),
            "real_hardware_validated": False, "real_ai_validated": False}


@router.get("/events", response_model=list[Event])
def events(request: Request, limit: int = 100):
    return history(request.app.state.store, request.app.state.records, None, limit)


@router.post("/feed/manual", response_model=FeedResult,
             responses={202: {"model": FeedResult}, 400: {"model": ApiError}, 413: {"model": ApiError},
                        429: {"model": ApiError}, 503: {"model": ApiError}})
def feed_manual(request: Request, response: Response, idempotency_key: str | None = Header(default=None)):
    result = request.app.state.feeds.request_feed(idempotency_key)
    response.status_code = 202 if result.state == FeedState.PENDING else 200
    return result


@router.get("/feed/manual/{request_id}", response_model=FeedResult,
            responses={400: {"model": ApiError}, 404: {"model": ApiError}, 503: {"model": ApiError}})
def feed_result(request: Request, request_id: int):
    if request_id < 1 or request_id > 0xFFFFFFFF:
        raise HTTPException(status_code=400, detail="request ID out of range")
    return request.app.state.feeds.get(request_id)


@router.get("/behavior", response_model=list[Event])
def behavior(request: Request):
    return history(request.app.state.store, request.app.state.records, "BEHAVIOR")


@router.get("/feeding-history", response_model=list[Event])
def feeding_history(request: Request):
    return history(request.app.state.store, request.app.state.records, "FEED")


@router.get("/drinking-history", response_model=list[Event])
def drinking_history(request: Request):
    return history(request.app.state.store, request.app.state.records, "DRINKING")


@router.get("/sessions/feeding")
def feeding_sessions(request: Request, limit: int = 100):
    return request.app.state.records.list("feeding", limit=limit)


@router.get("/sessions/drinking")
def drinking_sessions(request: Request, limit: int = 100):
    return request.app.state.records.list("drinking", limit=limit)


@router.get("/preferences")
def preferences(request: Request):
    repo = request.app.state.records
    feeds = repo.list("feeding", limit=1000)
    if repo.count("feeding") > len(feeds):
        raise HTTPException(status_code=409, detail="preference evidence exceeds bounded query window")
    food_types = {x.food_type for x in repo.list("food_type")}
    food_types.update(x.food_type for x in feeds if x.food_type)
    return [trend(food, feeds,
                  PreferencePolicy(min_sessions=request.app.state.preference_min_sessions))
            for food in sorted(food_types)]


@router.get("/food-types")
def food_types(request: Request):
    return request.app.state.records.list("food_type")


@router.get("/daily-summary")
def summary(request: Request, day: date | None = None):
    if day == date.max:
        raise HTTPException(status_code=422, detail="date exceeds supported daily query interval")
    return daily_summary(request.app.state.records, day or datetime.now(timezone.utc).date(),
                         min_sessions=request.app.state.preference_min_sessions)
