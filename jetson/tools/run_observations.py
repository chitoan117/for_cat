"""Explicit bounded offline video→mock predictions→canonical SQLite history. No live camera."""

import argparse
import json
from pathlib import Path

from app.ai.pipeline import ObservationPipeline
from app.camera.video_file import VideoFileCameraProvider
from app.storage.repositories import RecordRepository


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--database", default=":memory:", help="default discards offline history after run")
    parser.add_argument("--max-frames", type=int, default=300)
    args = parser.parse_args()
    repo = RecordRepository(args.database)
    try:
        pipeline = ObservationPipeline(VideoFileCameraProvider(str(args.video)), repo, replay_time=True)
        print(json.dumps(pipeline.run(max_frames=args.max_frames), indent=2))
        # UNKNOWN mocks: no invented observations or feeding actions.
    finally:
        repo.close()
