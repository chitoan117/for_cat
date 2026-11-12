from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
import os
from threading import RLock
from fastapi.staticfiles import StaticFiles
from app.frontend_assets import resolve_flutter_frontend

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
from app.device_state import Esp32StateReader
from app.api.esp32_routes import router as esp32_router
from app.api.system_routes import router as system_router
from app.system_state import RealHardwareProvider, MockProvider, SystemStateService
from app.ai_state import AiStateReader
from app.api.meal_plan_routes import router as meal_plan_router
from app.scheduled_worker import ScheduledWorker
from app.hx711_view import Hx711GramView
from app.api.hx711_routes import router as hx711_router
from app.camera.live_stream import FrameHub, VideoSettings, router as camera_router
from app.camera.remote_access import RemotePolicy, CameraAccessMiddleware
from app.http_middleware import EmptyFeedBodyMiddleware


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
    flutter_web_dir: str | Path | None = None,
    scheduled_worker_enabled: bool | None = None,
    live_camera: FrameHub | None = None,
    remote_policy: RemotePolicy | None = None,
    simulation_feed_results=None,
) -> FastAPI:
    hardware = hardware if hardware is not None else HardwareConfig.from_env()
    video = live_camera if live_camera is not None else FrameHub(VideoSettings.from_env(os.environ))
    access = remote_policy if remote_policy is not None else RemotePolicy.from_env(os.environ)
    if video.settings.enabled and (hardware.camera_provider == 'USB' or isinstance(camera, UsbWebcamCameraProvider)):
        raise ValueError('C++ owns webcam capture; Python USB camera must not be opened concurrently')
    if video.settings.enabled and access.mode == 'DISABLED':
        raise ValueError('enabled video requires LOCAL_DEMO or TAILSCALE_SERVE access boundary')
    frontend = resolve_flutter_frontend(flutter_web_dir or os.environ.get('FORCAT_FLUTTER_WEB_DIR'))
    bridge_mode = os.environ.get('ESP32_BRIDGE_ENABLED', '0')
    if bridge_mode not in ('0', '1'):
        raise ValueError('ESP32_BRIDGE_ENABLED must be 0 or 1')
    if bridge_mode == '1' and hardware.esp32_transport != 'MOCK':
        raise ValueError('C++ bridge owns serial; binary SERIAL transport must not run concurrently')
    provider_mode = os.environ.get('SYSTEM_STATE_PROVIDER', 'REAL')
    if provider_mode not in ('REAL', 'MOCK'):
        raise ValueError('SYSTEM_STATE_PROVIDER must be REAL or MOCK')
    worker_flag = os.environ.get('SCHEDULED_DRY_RUN_WORKER_ENABLED', '0')
    if worker_flag not in ('0', '1'):
        raise ValueError('SCHEDULED_DRY_RUN_WORKER_ENABLED must be 0 or 1')
    enabled = worker_flag == '1' if scheduled_worker_enabled is None else scheduled_worker_enabled
    if type(enabled) is not bool or (enabled and (bridge_mode != '1' or provider_mode != 'REAL')):
        raise ValueError('Scheduled DRY RUN worker requires REAL SystemState and existing C++ bridge')
    poll_seconds = float(os.environ.get('SCHEDULED_DRY_RUN_POLL_SECONDS', '2'))
    if not 1 <= poll_seconds <= 30:
        raise ValueError('Scheduled DRY RUN poll interval must be 1..30s')
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
        await application.state.system_state.start()
        await application.state.scheduled_worker.start()
        try:
            yield
        finally:
            await application.state.live_camera.close()
            await application.state.scheduled_worker.stop()
            await application.state.system_state.stop()
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
    application.state.live_camera = video
    application.state.remote_policy = access
    application.state.flutter_web_dir = frontend
    application.state.store_path = str(db_path)
    application.state.meal_plans = None
    application.state.meal_plan_lock = RLock()
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
    application.state.esp32_reader = Esp32StateReader(db_path) if bridge_mode == '1' else None
    application.state.system_state = SystemStateService(
        RealHardwareProvider(application.state.esp32_reader or Esp32StateReader(db_path), AiStateReader(db_path), Hx711GramView(db_path))
        if provider_mode == 'REAL' else MockProvider())
    application.state.scheduled_worker = ScheduledWorker(db_path,
        application.state.system_state.snapshot, application.state.meal_plan_lock,
        enabled=enabled, poll_seconds=poll_seconds)
    # Phase 2 never forwards feed commands to physical hardware.
    application.state.feeds = FeedService(serial_transport, event_store,
                                          allow_feed_requests=hardware.esp32_transport == "MOCK" and bridge_mode == '0',
                                          records=records,simulation_result_reader=simulation_feed_results)
    if hardware.cors_origins:
        application.add_middleware(CORSMiddleware, allow_origins=list(hardware.cors_origins),
                                   allow_methods=["GET", "POST"], allow_headers=["Idempotency-Key", "Content-Type"])

    application.add_middleware(EmptyFeedBodyMiddleware)
    application.add_middleware(CameraAccessMiddleware, policy=access)
    application.include_router(router)
    if frontend is not None:
        application.mount('/flutter', StaticFiles(directory=str(frontend), html=False), name='flutter-assets')
    application.include_router(esp32_router)
    application.include_router(system_router)
    application.include_router(meal_plan_router)
    application.include_router(hx711_router)
    application.include_router(camera_router)
    return application


def __getattr__(name):
    """Preserve uvicorn app.main:app while plain module imports stay side-effect free."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
