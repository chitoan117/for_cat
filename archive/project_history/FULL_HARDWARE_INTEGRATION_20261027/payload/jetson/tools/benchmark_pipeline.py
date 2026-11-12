"""Bounded HOST BENCHMARK of mock/synthetic/video flow; never a trained-AI performance claim."""

import argparse
import json
import time

from app.ai.budget import ProcessingBudget
from app.ai.pipeline import ObservationPipeline
from app.camera.video_file import VideoFileCameraProvider
from app.storage.repositories import RecordRepository
from tools.demo_replay import DemoCamera, DemoIdentityModel, DemoBehaviorModel
from tools.readiness_report import is_jetson


def benchmark_pipeline(frames=300, video=None):
    if not 1 <= frames <= 10000:
        raise ValueError("frames must be 1..10000")
    repo = RecordRepository(":memory:", max_rows=100)
    camera = VideoFileCameraProvider(video) if video else DemoCamera(frames)
    pipeline = ObservationPipeline(camera, repo, DemoIdentityModel(), DemoBehaviorModel(),
                replay_time=True, source="SYNTHETIC_DEMO", budget=ProcessingBudget(), sleep=lambda _: None,
                clock=time.perf_counter)
    started = time.perf_counter()
    try:
        pipeline.run(max_frames=min(10000, frames + 1), max_seconds=60)
        elapsed = max(time.perf_counter() - started, 1e-9)
        latency = sorted(pipeline.latencies)
        return {"label": "JETSON BENCHMARK" if is_jetson() else "HOST BENCHMARK ONLY",
                "models": "SYNTHETIC_TEST_MODEL; no trained-AI/GPU measurement",
                "frames_processed": pipeline.processed, "effective_fps": pipeline.processed / elapsed,
                "mean_processing_latency_ms": pipeline.latency_sum / pipeline.processed * 1000 if pipeline.processed else None,
                "p95_processing_latency_ms": latency[min(len(latency)-1, int(len(latency)*0.95))] * 1000 if latency else None,
                "latency_window_frames": len(latency), "skipped_frames": pipeline.skipped,
                "sessions": pipeline.sessions, "runtime_seconds": elapsed, "queue_depth": 1}
    finally:
        repo.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--video", help="optional user-provided file; no camera access")
    args = parser.parse_args()
    print(json.dumps(benchmark_pipeline(args.frames, args.video), indent=2))
