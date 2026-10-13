"""HOST VIDEO CODEC VERIFIED; fixtures never enter ai/datasets or access a camera."""

import tempfile
from pathlib import Path

import pytest

from ai.dataset import load_manifest, report, split_sessions, validate_splits
from ai.scripts.import_capture import import_capture
from ai.scripts.import_video import import_video
from ai.scripts.extract_frames import extract
from ai.scripts.label_dataset import label
from ai.scripts.split_dataset import split


def encode_fixture(path, count=12, offset=0):
    import cv2
    import numpy as np

    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    assert writer.isOpened(), "available MJPG video encoder required for HOST VIDEO CODEC validation"
    try:
        for index in range(count):
            image = np.full((48, 64, 3), offset + index * 12, dtype=np.uint8)
            image[0:8, 0:8] = (index * 3, 100, 200)
            writer.write(image)
    finally:
        writer.release()


def test_opencv_generated_video_decodes_order_timestamps_and_eof(tmp_path):
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    import numpy as np
    from app.camera.video_file import VideoFileCameraProvider

    with tempfile.TemporaryDirectory(dir=tmp_path) as work:
        path = Path(work) / "synthetic.avi"
        encode_fixture(path)
        camera = VideoFileCameraProvider(str(path))
        assert camera.open()
        frames = []
        try:
            while (frame := camera.read()) is not None:
                frames.append(frame)
        finally:
            camera.close()
        assert len(frames) == 12 and camera.eof
        assert camera.read() is None
        for index, frame in enumerate(frames):
            assert (frame.width, frame.height, frame.pixel_format) == (64, 48, "BGR")
            pixels = np.frombuffer(frame.pixels, np.uint8).reshape(48, 64, 3)
            assert abs(float(pixels[20:40, 20:50].mean()) - index * 12) < 4
            if index:
                assert abs((frame.captured_at - frames[index-1].captured_at).total_seconds() - 0.1) < 0.02
    assert not path.exists()


def test_temporary_video_dataset_roundtrip_sessions_labels_split_and_report(tmp_path):
    pytest.importorskip("cv2")
    pytest.importorskip("PIL")
    from PIL import Image

    with tempfile.TemporaryDirectory(dir=tmp_path) as work:
        root = Path(work) / "dataset"
        for session in range(3):
            source = Path(work) / f"synthetic-{session}.avi"
            encode_fixture(source, count=6, offset=session * 5)
            assert import_video(source, f"synthetic_{session}", root)["status"] == "DRY_RUN"
            receipt = import_video(source, f"synthetic_{session}", root, apply=True)
            extracted = extract(receipt["source_video"], f"synthetic_{session}", root,
                                every=2, max_frames=3, apply=True, metadata={"lighting": "SYNTHETIC_TEST_DATA"})
            assert extracted["frames"] == 3
            with pytest.raises(ValueError, match="already imported"):
                import_video(source, f"synthetic_{session}", root, apply=True)
        rows, errors = load_manifest(root)
        assert len(rows) == 9 and errors == []
        for row in rows:
            assert row["source_hash"] and row["source_offset_seconds"] >= 0
            label(root, row["sample_id"], "OWNER_CAT", "EATING", apply=True)
        assert report(root)["status"] == "DATASET_AVAILABLE"
        groups = split(root, seed=42, apply=True)["splits"]
        labeled, _ = load_manifest(root)
        assert groups == split_sessions(labeled, 42)
        assert validate_splits(groups) == []
        assert all(len(group) == 1 for group in groups.values())
        # Image import/UNUSABLE representation is independent of the video sessions.
        still = Path(work) / "still.png"
        Image.new("RGB", (8, 8), (10, 250, 40)).save(still)
        capture = import_capture(still, "unusable_still", root, apply=True)
        label(root, capture["sample_id"], "SKIP", "SKIP", usable=False, apply=True)
        assert report(root)["unusable"] == 1
        with pytest.raises((ValueError, FileExistsError)):
            import_capture(still, "unusable_still", root, apply=True)
        (root / rows[0]["path"]).write_bytes(b"corrupt synthetic fixture")
        broken = report(root)
        assert broken["status"] == "DATASET_INVALID" and broken["image_integrity"]["CORRUPT"] == 1
    assert not root.exists()
