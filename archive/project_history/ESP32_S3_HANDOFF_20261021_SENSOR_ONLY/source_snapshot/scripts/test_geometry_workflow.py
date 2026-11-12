"""Python 3.6+ stdlib CLI integration tests. Generated MP4/manual boxes only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class GeometryWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = os.environ["FOR_CAT_GEOMETRY_TOOL"]
        cls.maker = os.environ["FOR_CAT_GEOMETRY_FIXTURE"]
        cls.temp = tempfile.TemporaryDirectory(prefix="for-cat-geometry-cli-")
        cls.root = Path(cls.temp.name)
        cls.media = cls.root / "media"
        subprocess.check_call([cls.maker, str(cls.media)])

    @classmethod
    def tearDownClass(cls):
        # Keep bounded fixture evidence for review instead of pretending it is real.
        destination = os.environ.get("FOR_CAT_GEOMETRY_EVIDENCE")
        if destination:
            shutil.copytree(str(cls.root), destination)
        cls.temp.cleanup()

    def setUp(self):
        self.folder = self.root / self._testMethodName
        self.folder.mkdir()

    def run_tool(self, *args, **kwargs):
        result = subprocess.run([self.tool] + [str(a) for a in args],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
        expected = kwargs.get("expected", 0)
        self.assertEqual(result.returncode, expected, result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace"))
        return result

    def calibrate(self, name="cal", image=None, extra=()):
        out = self.folder / name
        self.run_tool("calibrate", "--image", image or self.media / "original.png",
                      "--food", "64,48,224,192", "--water", "416,48,576,192",
                      "--synthetic", "--out", out, *extra)
        return out

    def video(self, cal, name="validation", extra=()):
        out = self.folder / name
        self.run_tool("video", "--video", self.media / "fixture.mp4", "--calibration", cal,
                      "--synthetic", "--out", out, *extra)
        with (out / "report.json").open() as stream:
            return out, json.load(stream)

    def test_capture_original_frame(self):
        out = self.folder / "capture"
        self.run_tool("capture", "--video", self.media / "fixture.mp4", "--frame-index", "5", "--synthetic", "--out", out)
        data = json.loads((out / "capture.json").read_text())
        self.assertEqual((data["width"], data["height"], data["frame_index"]), (640, 480, 5))
        self.assertTrue((out / "original.png").is_file())
        self.assertFalse((out / "INCOMPLETE.txt").exists())

    def test_calibration_semantics_and_compatibility(self):
        cal = self.calibrate()
        data = json.loads((cal / "roi.candidate.json").read_text())
        meta = json.loads((cal / "calibration.json").read_text())
        self.assertEqual((data["food_bowl_color"], data["water_bowl_color"]), ("RED", "BLUE"))
        self.assertEqual(data["food_roi"], {"x1": 0.1, "y1": 0.1, "x2": 0.35, "y2": 0.4})
        self.assertEqual((meta["source_width"], meta["source_height"]), (640, 480))
        self.assertIn("calibrated_utc", meta)
        self.assertEqual(meta["config_sha256"], hashlib.sha256((cal / "roi.candidate.json").read_bytes()).hexdigest())
        self.run_tool("check-config", "--config", cal / "roi.candidate.json", "--synthetic")

    def test_overlay_preserves_original(self):
        image = self.media / "original.png"
        before = image.read_bytes()
        cal = self.calibrate()
        out = self.folder / "overlay"
        self.run_tool("overlay", "--image", image, "--calibration", cal, "--synthetic", "--out", out)
        self.assertEqual(image.read_bytes(), before)
        self.assertTrue((out / "overlay.png").stat().st_size > 0)
        self.assertFalse(json.loads((out / "verification.json").read_text())["reviewed_automatically"])

    def test_dimension_change_rejected(self):
        cal = self.calibrate()
        self.run_tool("overlay", "--image", self.media / "wrong_dimensions.png", "--calibration", cal,
                      "--synthetic", "--out", self.folder / "bad", expected=2)
        self.assertFalse((self.folder / "bad").exists())

    def test_invalid_and_overlapping_rois_rejected(self):
        for n, food in enumerate(("-1,0,20,20", "64,48,64,192", "64,48,700,192", "416,48,576,192")):
            self.run_tool("calibrate", "--image", self.media / "original.png", "--food", food,
                          "--water", "416,48,576,192", "--out", self.folder / ("bad" + str(n)), expected=2)

    def test_config_hash_change_rejected(self):
        cal = self.calibrate()
        path = cal / "roi.candidate.json"
        data = json.loads(path.read_text())
        data["geometry"]["near_distance"] = 0.04
        path.write_text(json.dumps(data))
        self.run_tool("overlay", "--image", self.media / "original.png", "--calibration", cal,
                      "--synthetic", "--out", self.folder / "bad", expected=2)

    def test_synthetic_opt_in_required(self):
        cal = self.calibrate()
        self.run_tool("check-config", "--config", cal / "roi.candidate.json", expected=2)
        self.run_tool("video", "--video", self.media / "fixture.mp4", "--calibration", cal,
                      "--out", self.folder / "bad", "--detector", "none", expected=2)

    def test_manual_video_metrics_and_evidence(self):
        out, report = self.video(self.calibrate(), extra=("--detections", self.media / "manual.csv"))
        self.assertEqual(report["purpose"], "GEOMETRY VALIDATION")
        self.assertEqual(report["frames_processed"], 50)
        self.assertGreater(report["near_food_ms"], 0)
        self.assertGreater(report["near_water_ms"], 0)
        self.assertGreater(report["ambiguous_frames"], 0)
        self.assertGreater(report["track_id_changes"], 0)
        self.assertGreater(report["reacquisitions"], 0)
        self.assertFalse(report["behavior_validation"])
        self.assertEqual(report["behavior_events"], 0)
        self.assertEqual(report["source_kind"], "SYNTHETIC_FIXTURE")
        for item in report["evidence"]:
            self.assertEqual(Path(item["path"]).name, item["path"])
            self.assertTrue((out / item["path"]).is_file())
        self.assertLessEqual(len(report["evidence"]), 9)
        self.assertTrue((out / "threshold_review.md").exists())

    def test_roi_only_has_no_fabricated_cat_metrics(self):
        out, report = self.video(self.calibrate(), extra=("--detector", "none"))
        self.assertEqual(report["cat_detections"], 0)
        self.assertEqual(report["near_food_ms"], 0)
        self.assertEqual(report["evidence"], [])
        self.assertIsNone(report["food_distance"]["median"])
        self.assertFalse(list(out.glob("*.jpg")))

    def test_sampled_media_timestamps(self):
        out, report = self.video(self.calibrate(), extra=("--detector", "none", "--every", "3"))
        rows = [json.loads(line) for line in (out / "frames.jsonl").read_text().splitlines()]
        self.assertEqual([row["frame_index"] for row in rows], list(range(0, 50, 3)))
        self.assertTrue(all(a["timestamp_ms"] < b["timestamp_ms"] for a, b in zip(rows, rows[1:])))
        self.assertGreater(report["sampled_span_ms"], 4000)

    def test_existing_artifacts_not_overwritten(self):
        cal = self.calibrate()
        before = (cal / "roi.candidate.json").read_bytes()
        self.run_tool("calibrate", "--image", self.media / "original.png", "--food", "64,48,224,192",
                      "--water", "416,48,576,192", "--synthetic", "--out", cal, expected=2)
        self.assertEqual((cal / "roi.candidate.json").read_bytes(), before)

    def test_production_letterbox_preprocess_decoder_regression(self):
        result = self.run_tool("self-test")
        self.assertIn(b"21 assertions PASS", result.stdout)

    def test_unknown_duplicate_and_bad_source_rejected(self):
        self.run_tool("capture", "--video", "missing.mp4", "--out", self.folder / "missing", expected=2)
        self.run_tool("capture", "--video", "a", "--video", "b", expected=2)
        self.run_tool("overlay", "--typo", "x", expected=2)

    def test_threshold_candidate_preserves_explicit_base(self):
        cal = self.calibrate()
        data = json.loads((cal / "roi.candidate.json").read_text())
        data["geometry"]["near_distance"] = 0.04
        base = self.folder / "base.json"
        base.write_text(json.dumps(data))
        candidate = self.calibrate("candidate", extra=("--base-config", base))
        after = json.loads((candidate / "roi.candidate.json").read_text())
        self.assertEqual(after["geometry"]["near_distance"], 0.04)
        self.assertEqual(after["tracker"], data["tracker"])
        self.assertEqual(after["food_roi"], data["food_roi"])

    def test_invalid_manual_csv_rejected(self):
        cal = self.calibrate()
        csv = self.folder / "invalid.csv"
        csv.write_text("frame_index,class_id,confidence,x1,y1,x2,y2\n0,15,0.9,20,20,10,10\n")
        self.run_tool("video", "--video", self.media / "fixture.mp4", "--calibration", cal,
                      "--synthetic", "--detections", csv, "--out", self.folder / "bad", expected=2)

    def test_frame_limit_explicit_partial_scope(self):
        _, report = self.video(self.calibrate(), extra=("--detector", "none", "--max-frames", "3"))
        self.assertEqual(report["termination"], "FRAME_LIMIT")
        self.assertEqual(report["frames_processed"], 3)

    def test_per_frame_no_accidental_behavior_assertion(self):
        out, _ = self.video(self.calibrate(), extra=("--detections", self.media / "manual.csv"))
        rows = [json.loads(line) for line in (out / "frames.jsonl").read_text().splitlines()]
        self.assertTrue(any(not row["cat_observed"] for row in rows))
        for row in rows:
            self.assertIsNone(row["behavior_observation"])
            self.assertEqual(row["behavior_events"], [])
            if not row["geometry_valid"]:
                self.assertIsNone(row["food_distance"])
                self.assertIsNone(row["water_distance"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
