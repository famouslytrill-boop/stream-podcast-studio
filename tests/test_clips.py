"""Validation failures and real FFmpeg export tests using synthetic media only."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.clip_tools import StudioError, render, validate_clips


class ClipValidationTests(unittest.TestCase):
    def setUp(self):
        self.media = {"duration_seconds": 30, "audio_stream_count": 2}
        self.clip = {"id": "clip-01", "in_seconds": 1, "out_seconds": 4, "title": "Actual test",
                     "audio_stream": 1, "context_reviewed": True, "rights_reviewed": True}

    def test_invalid_cuts_tracks_and_filenames(self):
        changes = [{"in_seconds": True}, {"in_seconds": float("nan")}, {"out_seconds": 31},
                   {"out_seconds": 1}, {"audio_stream": True}, {"audio_stream": 2},
                   {"id": "../outside"}, {"id": "con"}, {"layout": "unknown"}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(StudioError):
                validate_clips({"clips": [{**self.clip, **change}]}, self.media)

    def test_duplicate_ids_and_batch_limit(self):
        for clips in ([self.clip, self.clip], [self.clip] * 4, []):
            with self.assertRaises(StudioError):
                validate_clips({"clips": clips}, self.media)

    def test_confirmation_requires_boolean_true(self):
        item = {**self.clip, "context_reviewed": "true", "rights_reviewed": 1}
        checked = validate_clips({"clips": [item]}, self.media)
        self.assertEqual(checked[0]["review_pending"], ["context_reviewed", "rights_reviewed"])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class ClipExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="ember-clip-tests-")
        cls.root = Path(cls.tmp.name)
        cls.source = cls.root / "source with spaces.mkv"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                        "testsrc2=size=640x360:rate=30", "-f", "lavfi", "-i",
                        "anullsrc=r=48000:cl=stereo", "-f", "lavfi", "-i",
                        "sine=frequency=440:sample_rate=48000", "-t", "5", "-map", "0:v",
                        "-map", "1:a", "-map", "2:a", "-c:v", "libx264", "-threads", "2",
                        "-c:a", "pcm_s16le", str(cls.source)], check=True, capture_output=True)
        cls.original_hash = hashlib.sha256(cls.source.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def manifest(self, name, reviewed=True):
        data = {"source": self.source.name, "clips": [
            {"id": "fit", "in_seconds": 0.5, "out_seconds": 2, "title": "Synthetic fit test",
             "layout": "fit", "audio_stream": 1, "context_reviewed": reviewed, "rights_reviewed": reviewed},
            {"id": "crop", "in_seconds": 2, "out_seconds": 3.5, "title": "Synthetic crop test",
             "layout": "center-crop", "audio_stream": 1, "context_reviewed": reviewed, "rights_reviewed": reviewed},
        ]}
        path = self.root / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_review_gate_and_existing_outputs(self):
        with self.assertRaises(StudioError):
            render(self.manifest("unreviewed.json", False), self.root / "blocked")
        self.assertFalse((self.root / "blocked").exists())
        out = self.root / "existing"
        out.mkdir()
        (out / "keep.txt").write_text("preserve me")
        with self.assertRaises(StudioError):
            render(self.manifest("existing.json"), out)
        self.assertEqual((out / "keep.txt").read_text(), "preserve me")

    def test_real_export_both_layouts_selected_audio_and_unchanged_source(self):
        result = render(self.manifest("approved.json"), self.root / "exports")
        self.assertEqual(len(result["clips"]), 2)
        self.assertFalse(result["published"])
        for clip in result["clips"]:
            self.assertTrue(clip["decode_verified"])
            self.assertEqual((clip["encoded"]["width"], clip["encoded"]["height"]), (1080, 1920))
            raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i",
                                  str(self.root / "exports" / clip["file"]), "-vn", "-ac", "1",
                                  "-f", "s16le", "-"], check=True, capture_output=True).stdout
            import array
            samples = array.array("h", raw)
            self.assertGreater(max(abs(x) for x in samples), 1000,
                               "Must select the tone track rather than the silent first audio track")
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.original_hash)

    def test_network_source_is_refused(self):
        path = self.root / "network.json"
        path.write_text(json.dumps({"source": "https://example.com/video.mp4", "clips": []}))
        with self.assertRaises(StudioError):
            render(path, self.root / "network-output")


if __name__ == "__main__":
    unittest.main()
