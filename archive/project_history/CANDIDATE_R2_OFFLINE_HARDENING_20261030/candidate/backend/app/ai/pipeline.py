"""Injected prediction→temporal→typed-history orchestration. NEVER authorizes feeding."""

import time
import sqlite3
from collections import deque
from uuid import uuid4

from app.ai.interfaces import (BehaviorModel, IdentityModel, MockBehaviorModel, MockIdentityModel)
from app.behavior.fusion import SessionFusion
from app.behavior.temporal import Prediction, SessionSignal, SignalType, TemporalEngine
from app.camera.base import CameraProvider
from app.observability import get_logger
from app.observability import WarningLimiter
from app.ai.budget import ProcessingBudget
from app.camera.frame_ops import limit_frame
from app.vision.geometry import NormalizedBox
from app.status import ComponentState
from app.storage.repositories import RecordRepository


class ObservationPipeline:
    def __init__(self, camera: CameraProvider, records: RecordRepository,
                 identity_model: IdentityModel | None = None, behavior_model: BehaviorModel | None = None,
                 tracker: TemporalEngine | None = None, *, source: str = "UNVALIDATED",
                 clock=time.monotonic, sleep=time.sleep, replay_time: bool = False,
                 fusion_context=None, budget: ProcessingBudget | None = None, shadow_mode: bool = True,
                 identity_threshold: float | None = None, behavior_threshold: float | None = None,
                 food_roi: NormalizedBox | None = None, water_roi: NormalizedBox | None = None,
                 approach_roi: NormalizedBox | None = None):
        self.camera, self.records = camera, records
        self.identity = identity_model if identity_model is not None else MockIdentityModel()
        self.behavior = behavior_model if behavior_model is not None else MockBehaviorModel()
        self.tracker = tracker if tracker is not None else TemporalEngine()
        self.source = source
        self.clock, self.sleep, self.replay_time = clock, sleep, replay_time
        # Optional future measurement/session gateway; default supplies no sensor evidence.
        self.fusion_context = fusion_context
        self.budget = budget or ProcessingBudget()
        self.shadow_mode = shadow_mode
        self.identity_threshold, self.behavior_threshold = identity_threshold, behavior_threshold
        self.food_roi, self.water_roi = food_roi, water_roi
        self.approach_roi = approach_roi
        self.mock_models = isinstance(self.identity, MockIdentityModel) and isinstance(self.behavior, MockBehaviorModel)
        self.ai_state = ComponentState.MOCK if self.mock_models else ComponentState.NOT_VALIDATED
        self.camera_state = ComponentState.NOT_CONFIGURED
        self.running = False
        self.frames = self.failures = self.sessions = 0
        self._start: SessionSignal | None = None
        self._namespace = uuid4().hex[:12]
        self._first_timestamp = None
        self.logger = get_logger()
        self.warnings = WarningLimiter(clock=clock)
        self.db_state = "READY"
        self._pending_write = None
        self._models_loaded = False
        self._ever_started = False
        self.processed = self.skipped = 0
        self._last_inference_at = float("-inf")
        self.latencies = deque(maxlen=256)
        self.latency_sum = 0.0
        for model in (self.identity, self.behavior):
            if getattr(model, "health", lambda: "NOT_VALIDATED")() == "NOT_CONFIGURED":
                self.ai_state = ComponentState.NOT_CONFIGURED

    def start(self) -> bool:
        if self.running:
            return True
        try:
            if not self._models_loaded:
                loaded = []
                for model in (self.identity, self.behavior):
                    load = getattr(model, "load", None)
                    if load is not None and not load():
                        for previous in loaded:
                            getattr(previous, "close", lambda: None)()
                        self.ai_state = ComponentState.NOT_CONFIGURED
                        return False
                    loaded.append(model)
                self._models_loaded = True
            opened = self.camera.open()
        except Exception:
            for model in (self.identity, self.behavior):
                try:
                    getattr(model, "close", lambda: None)()
                except Exception:
                    pass
            self._models_loaded = False
            opened = False
        self.running = opened
        if opened and self._ever_started:
            self.tracker = TemporalEngine(self.tracker.min_frames, self.tracker.confirm_seconds,
                           self.tracker.dropout_seconds, self.tracker.cooldown_seconds, self.tracker.min_confidence)
            self._namespace = uuid4().hex[:12]
            self._first_timestamp = None
            self._last_inference_at = float("-inf")
        self._ever_started = self._ever_started or opened
        self.camera_state = ComponentState.MOCK if opened else ComponentState.OFFLINE
        return opened

    def _consume(self, signals: list[SessionSignal], reason="BEHAVIOR_STOPPED") -> None:
        for signal in signals:
            signal = signal.model_copy(update={"session_id": f"{self._namespace}-{signal.session_id}"})
            if signal.signal == SignalType.START:
                self._start = signal
            elif self._start is not None:
                self._pending_write = (self._start, signal, reason)
                self._start = None
                self._drain_pending()

    def _drain_pending(self) -> None:
        if self._pending_write is None:
            return
        start, end, reason = self._pending_write
        context = self.fusion_context(start, end) if self.fusion_context is not None else {}
        SessionFusion(self.records).fuse(start, end, source=self.source,
                                          completion_reason=reason, **context)
        self._pending_write = None
        self.db_state = "READY"
        self.sessions += 1
        self.logger.info("observation session stored", extra={"component": "ai_pipeline",
                          "session_id": end.session_id, "event_type": end.behavior.value})

    def _storage_failure(self) -> str:
        self.failures += 1
        self.db_state = "NOT_AVAILABLE"
        self.warnings.warn(self.logger, "database", "observation storage unavailable",
                           {"component": "storage", "event_type": "WRITE_FAILED"})
        return "STORAGE_FAILURE"

    def process_one_frame(self) -> str:
        try:
            self._drain_pending()  # retry at most one completed visit before reading more frames
        except sqlite3.Error:
            return self._storage_failure()
        if not self.running and not self.start():
            return "MODEL_NOT_CONFIGURED" if self.ai_state == ComponentState.NOT_CONFIGURED else "CAMERA_OFFLINE"
        try:
            frame = self.camera.read()
        except Exception:
            frame = None
        if frame is None:
            if getattr(self.camera, "eof", False):
                self.stop("EOF")
                self.camera_state = ComponentState.OFFLINE
                return "EOF"
            self.failures += 1
            self.camera_state = ComponentState.OFFLINE
            self.warnings.warn(self.logger, "camera", "camera frame unavailable",
                               {"component": "camera", "event_type": "OFFLINE"})
            return "CAMERA_OFFLINE"
        self.camera_state = ComponentState.MOCK if frame.synthetic or self.replay_time else ComponentState.ONLINE
        self.frames += 1
        if self._first_timestamp is None:
            self._first_timestamp = frame.captured_at
        elapsed = ((frame.media_seconds if frame.media_seconds is not None else
                   (frame.captured_at - self._first_timestamp).total_seconds())
                   if self.replay_time else self.clock())
        stale = frame.monotonic_seconds is not None and not self.replay_time and \
                self.clock() - frame.monotonic_seconds > self.budget.max_age_seconds
        if stale or (self.frames - 1) % self.budget.frame_skip or (self.budget.inference_fps and
                    elapsed - self._last_inference_at < 1 / self.budget.inference_fps):
            self.skipped += 1
            return "SKIPPED"
        self._last_inference_at = elapsed
        began = self.clock()
        try:
            frame = limit_frame(frame, self.budget.max_width, self.budget.max_height)
            recognition = self.identity.predict(frame)
            behavior = self.behavior.predict(frame, recognition.identity)
            if behavior.identity != recognition.identity:
                raise ValueError("identity/behavior evidence mismatch")
            confidence = (min(recognition.confidence, behavior.confidence)
                          if recognition.confidence is not None and behavior.confidence is not None else None)
            if recognition.ambiguous or (self.identity_threshold is not None and
                    (recognition.confidence is None or recognition.confidence < self.identity_threshold)) or \
                    (self.behavior_threshold is not None and (behavior.confidence is None or
                                                               behavior.confidence < self.behavior_threshold)):
                confidence = None
            food_roi, water_roi = behavior.food_roi, behavior.water_roi
            if self.food_roi is not None:
                food_roi = food_roi and recognition.bounding_box is not None and self.food_roi.contains_center(recognition.bounding_box)
            if self.water_roi is not None:
                water_roi = water_roi and recognition.bounding_box is not None and self.water_roi.contains_center(recognition.bounding_box)
            if self.approach_roi is not None and behavior.behavior.value in ("NEAR_FOOD", "NEAR_WATER"):
                in_approach = recognition.bounding_box is not None and self.approach_roi.contains_center(recognition.bounding_box)
                food_roi = behavior.food_roi and in_approach if behavior.behavior.value == "NEAR_FOOD" else food_roi
                water_roi = behavior.water_roi and in_approach if behavior.behavior.value == "NEAR_WATER" else water_roi
            prediction = Prediction(timestamp=frame.captured_at, monotonic_seconds=elapsed,
                                    identity=recognition.identity, behavior=behavior.behavior,
                                    confidence=confidence, food_roi=food_roi, water_roi=water_roi)
            self._consume(self.tracker.update(prediction))
        except sqlite3.Error:
            return self._storage_failure()
        except Exception:
            self.failures += 1
            self.ai_state = ComponentState.DEGRADED
            self.warnings.warn(self.logger, "model", "prediction processing failed",
                               {"component": "ai_pipeline", "event_type": "MODEL_FAILURE"})
            # A failed prediction is dropout, not evidence of continued eating.
            try:
                self._consume(self.tracker.flush(elapsed), "PREDICTION_DROPOUT")
            except sqlite3.Error:
                return self._storage_failure()
            return "MODEL_FAILURE"
        latency = max(0, self.clock() - began)
        self.latencies.append(latency)
        self.latency_sum += latency
        self.processed += 1
        self.ai_state = ComponentState.MOCK if self.mock_models else ComponentState.NOT_VALIDATED
        return "PROCESSED"

    def stop(self, reason: str = "STOPPED") -> None:
        try:
            self._drain_pending()
            self._consume(self.tracker.close_session(), reason)
        except sqlite3.Error:
            self._storage_failure()  # retained single pending write; no shutdown crash loop
        finally:
            self.running = False
            for resource in (self.camera, self.identity, self.behavior):
                try:
                    close = getattr(resource, "close", None)
                    if close is not None:
                        close()
                except Exception:
                    self.warnings.warn(self.logger, "close", "component close failed",
                                       {"component": "lifecycle", "event_type": "CLOSE_FAILED"})
            self._models_loaded = False

    def run(self, max_frames: int = 300, max_seconds: float = 60, interval: float = 0.05,
            max_failures: int = 3, stop_when=None) -> dict:
        if not 1 <= max_frames <= 10000 or not 0 < max_seconds <= 3600 or \
                not 0 < interval <= 5 or not 1 <= max_failures <= 30:
            raise ValueError("invalid pipeline loop bounds")
        started = self.clock()
        failures = 0
        try:
            for _ in range(max_frames):
                if self.clock() - started >= max_seconds or stop_when is not None and stop_when():
                    break
                outcome = self.process_one_frame()
                if outcome == "EOF":
                    break
                failures = failures + 1 if outcome not in ("PROCESSED", "SKIPPED") else 0
                if failures >= max_failures:
                    break
                self.sleep(min(2.0, interval * 2 ** min(failures, 5)))
        finally:
            self.stop("LOOP_STOPPED")
        return self.status()

    def status(self) -> dict:
        return {"state": self.ai_state.value, "camera": self.camera_state.value,
                "running": self.running, "frames": self.frames, "failures": self.failures,
                "sessions": self.sessions, "trained_model_validated": False,
                "shadow_mode": self.shadow_mode, "automatic_feed_authorized": False,
                "processed": self.processed, "skipped": self.skipped, "queue_depth": 1,
                "pending_writes": int(self._pending_write is not None), "database": self.db_state}
