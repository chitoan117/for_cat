"""One deliberately started observation worker, no frame queue or automatic startup."""

from enum import Enum
from threading import Event, Thread, Lock, current_thread


class ServiceState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    FAULTED = "FAULTED"
    STOPPING = "STOPPING"


class ObservationService:
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.state = ServiceState.STOPPED
        self._stop = Event()
        self._thread = None
        self._lock = Lock()

    def run(self, max_frames=300, max_seconds=60, interval=0.05, max_failures=3):
        if self._thread is not None and self._thread.is_alive() and current_thread() is not self._thread:
            raise RuntimeError("observation worker already running")
        if not 1 <= max_frames <= 10000 or not 0 < max_seconds <= 3600 or \
                not 0 < interval <= 5 or not 1 <= max_failures <= 30:
            raise ValueError("invalid observation service bounds")
        self.state = ServiceState.STARTING
        if self._thread is None or current_thread() is not self._thread:
            self._stop.clear()
        started = self.pipeline.clock()
        failures = 0
        try:
            for _ in range(max_frames):
                if self._stop.is_set() or self.pipeline.clock() - started >= max_seconds:
                    break
                outcome = self.pipeline.process_one_frame()
                if outcome == "EOF":
                    break
                good = outcome in ("PROCESSED", "SKIPPED")
                failures = 0 if good else failures + 1
                self.state = ServiceState.RUNNING if good else ServiceState.DEGRADED
                if failures >= max_failures:
                    self.state = ServiceState.FAULTED
                    break
                delay = min(2.0, interval * 2 ** min(failures, 5))
                if current_thread() is self._thread:
                    self._stop.wait(delay)  # interruptible managed-worker pacing
                else:
                    self.pipeline.sleep(delay)
        except Exception:
            self.state = ServiceState.FAULTED
        finally:
            try:
                self.pipeline.stop("SERVICE_STOPPED")
            except Exception:
                self.state = ServiceState.FAULTED
            if self.pipeline.db_state != "READY":
                self.state = ServiceState.FAULTED
            elif self.state != ServiceState.FAULTED:
                self.state = ServiceState.STOPPED
        return self.status()

    def start_background(self, **bounds):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("observation worker already running")
            self._stop.clear()
            self._thread = Thread(target=self.run, kwargs=bounds, name="forr-cat-observation", daemon=True)
            self._thread.start()

    def stop(self, timeout=5) -> bool:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            if thread is current_thread():
                self.state = ServiceState.FAULTED
                return False  # no join-self; caller must observe incomplete shutdown
            self.state = ServiceState.STOPPING
            thread.join(timeout)
            if thread.is_alive():
                self.state = ServiceState.FAULTED
                return False  # blocking camera/model needs process-level intervention, not a restart loop
        else:
            self.pipeline.stop("SERVICE_STOPPED")
        if self.state != ServiceState.FAULTED:
            self.state = ServiceState.STOPPED
        return True

    def status(self):
        return {"state": self.state.value, "worker_alive": bool(self._thread and self._thread.is_alive()),
                "pipeline": self.pipeline.status()}
