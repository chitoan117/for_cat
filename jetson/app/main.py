from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import FeedService, router
from app.camera.base import CameraProvider
from app.camera.mock_camera import MockCameraProvider
from app.camera.video_file import VideoFileCameraProvider
from app.behavior.temporal import TemporalEngine
from app.ai.interfaces import IdentityModel, BehaviorModel
from app.ai.pipeline import ObservationPipeline
from app.ai.service import ObservationService
from app.ai.budget import ProcessingBudget
from app.ai.runtime import ExternalRuntimeAdapter
from app.observability import get_logger
from app.camera.usb_webcam import UsbWebcamCameraProvider
from app.config import MAX_EVENTS, HardwareConfig
from app.serial_link.mock_transport import MockEsp32Transport
from app.serial_link.real_transport import RealEsp32SerialTransport
from app.serial_link.transport import SerialTransport
from app.storage.event_store import EventStore, SQLiteEventStore
from app.storage.repositories import RecordRepository


def create_app(
    db_path: str | Path | None = None,
    transport: SerialTransport | None = None,
    max_events: int = MAX_EVENTS,
    store: EventStore | None = None,
    hardware: HardwareConfig | None = None,
    camera: CameraProvider | None = None,
    identity_model: IdentityModel | None = None,
    behavior_model: BehaviorModel | None = None,
    pipeline_source: str = "UNVALIDATED",
) -> FastAPI:
    hardware = hardware if hardware is not None else HardwareConfig.from_env()
    db_path = hardware.db_path if db_path is None else db_path
    if max_events == MAX_EVENTS:
        max_events = hardware.max_events
    event_store = store if store is not None else SQLiteEventStore(db_path, max_events=max_events)
    camera_provider = camera if camera is not None else (
        MockCameraProvider() if hardware.camera_provider == "MOCK"
        else UsbWebcamCameraProvider(hardware.camera_device, settings=hardware.capture) if hardware.camera_provider == "USB"
        else VideoFileCameraProvider(hardware.video_file)
    )
    serial_transport = transport if transport is not None else (
        MockEsp32Transport() if hardware.esp32_transport == "MOCK"
        else RealEsp32SerialTransport(hardware.esp32_serial_device,
                                      reconnect_backoff_seconds=hardware.serial_reconnect_backoff_seconds)
    )
    try:
        records = RecordRepository(db_path if store is None else ":memory:")
    except Exception:
        if store is None:
            event_store.close()  # factory-owned connection on failed schema initialization
        raise
    if hardware.ai_runtime != "MOCK":
        identity_model = identity_model or ExternalRuntimeAdapter(hardware.ai_runtime, hardware.identity_model_path,
                                                                  hardware.identity_threshold)
        behavior_model = behavior_model or ExternalRuntimeAdapter(hardware.ai_runtime, hardware.behavior_model_path,
                                                                  hardware.behavior_threshold)
    get_logger().setLevel(hardware.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            yield
        finally:
            worker_stopped = application.state.observations.stop()
            if isinstance(serial_transport, RealEsp32SerialTransport):
                serial_transport.close()
            if worker_stopped:
                try:
                    records.close()
                finally:
                    event_store.close()

    application = FastAPI(title="forr_cat Jetson API", version="0.1.0", lifespan=lifespan)

    @application.exception_handler(sqlite3.Error)
    async def unavailable_storage(request, exc):
        get_logger().error("local storage unavailable", extra={"component": "storage", "event_type": "DATABASE_FAILURE"})
        return JSONResponse(status_code=503, content={"detail": "local storage unavailable"})
    application.state.store = event_store
    application.state.records = records
    application.state.preference_min_sessions = hardware.preference_min_sessions
    application.state.behavior_engine = TemporalEngine(hardware.behavior_confirm_frames,
                                                        hardware.behavior_confirm_seconds)
    application.state.pipeline = ObservationPipeline(camera_provider, records, identity_model, behavior_model,
                                tracker=application.state.behavior_engine, source=pipeline_source,
                                replay_time=hardware.camera_provider == "VIDEO",
                                budget=ProcessingBudget(hardware.inference_fps, hardware.max_processing_width,
                                  hardware.max_processing_height, hardware.frame_skip, hardware.queue_depth,
                                  hardware.max_frame_age_seconds), shadow_mode=hardware.ai_shadow_mode,
                                identity_threshold=hardware.identity_threshold,
                                behavior_threshold=hardware.behavior_threshold,
                                food_roi=hardware.food_roi, water_roi=hardware.water_roi,
                                approach_roi=hardware.approach_roi)
    application.state.observations = ObservationService(application.state.pipeline)
    application.state.hardware = hardware
    application.state.transport = serial_transport
    application.state.camera = camera_provider
    application.state.esp32_mode = hardware.esp32_transport
    # Phase 2 never forwards feed commands to physical hardware.
    application.state.feeds = FeedService(serial_transport, event_store,
                                          allow_feed_requests=hardware.esp32_transport == "MOCK",
                                          records=records)
    if hardware.cors_origins:
        application.add_middleware(CORSMiddleware, allow_origins=list(hardware.cors_origins),
                                   allow_methods=["GET", "POST"], allow_headers=["Idempotency-Key", "Content-Type"])

    @application.middleware("http")
    async def bound_feed_body(request, call_next):
        if request.method == "POST" and request.url.path == "/api/v1/feed/manual":
            length = request.headers.get("content-length")
            if length is not None:
                try:
                    parsed = int(length)
                    if parsed < 0:
                        return JSONResponse(status_code=400, content={"detail": "invalid Content-Length"})
                    if parsed > 0:
                        return JSONResponse(status_code=413, content={"detail": "feed request body not supported"})
                except ValueError:
                    return JSONResponse(status_code=400, content={"detail": "invalid Content-Length"})
            # A false Content-Length:0 must not bypass the empty-body contract.
            async for part in request.stream():
                if part:
                    return JSONResponse(status_code=413, content={"detail": "feed request body not supported"})
        return await call_next(request)

    application.include_router(router)
    return application


def __getattr__(name):
    """Preserve uvicorn app.main:app while plain module imports stay side-effect free."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
