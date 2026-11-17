import copy
import http.client
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from hub.core import Workspace, digest, probe_media
from hub.mcp import Client, TOOLS, dispatch
from hub.obs import validate_action
from hub.render import render_bumper, render_sequence
from hub.server import StudioServer
from tools.studio_tools import StudioError


class HubFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory()
        cls.source = Path(cls.fixtures.name) / "synthetic.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=8",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8", "-c:v", "libx264", "-threads", "2",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(cls.source)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Workspace(Path(self.tmp.name) / "personal")
        self.item = self.ws.import_media(self.source, "my recording.mp4")

    def tearDown(self):
        self.ws.close()
        self.tmp.cleanup()

    def session(self, **changes):
        data = {"title": "Synthetic rehearsal", "media_id": self.item["id"], "format": "landscape",
                "audio_track": 0, "cuts": [{"start": 0, "end": 2}], "captions": "", "content_reviewed": True}
        data.update(changes)
        return self.ws.save_session(data)

    def wait_job(self, job):
        for _ in range(300):
            current = self.ws.get("jobs", job["id"])
            if current["state"] not in {"queued", "running"}:
                return current
            time.sleep(.1)
        self.fail("Synthetic job did not finish")

class HubCase(HubFixture):
    def test_browser_style_webm_without_duration_is_measured(self):
        path = Path(self.tmp.name) / "streaming-header.webm"
        result = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=600:duration=2", "-c:a", "libopus", "-f", "webm", "pipe:1"], capture_output=True, check=True)
        path.write_bytes(result.stdout)
        info = probe_media(path)
        self.assertAlmostEqual(info["duration"], 2, delta=.1)
        self.assertEqual(info["duration_basis"], "decoded_stream_timestamps")

    def test_another_server_cannot_recover_an_active_workspace(self):
        with self.assertRaisesRegex(StudioError, "already open"):
            Workspace(self.ws.root)

    def test_import_copies_and_hashes_source_without_modifying_it(self):
        self.assertEqual(self.item["sha256"], digest(self.source))
        self.assertNotEqual(self.ws.media_path(self.item["id"]), self.source)
        self.assertEqual(len(self.ws.pairing_key), 43)
        self.assertEqual(self.item["audio_tracks"], 1)

    def test_invalid_media_and_paths_are_rejected(self):
        with self.assertRaises(StudioError):
            self.ws.import_media(self.source, "not-playlist.m3u8")
        with self.assertRaises(StudioError):
            self.ws.media_path("../../outside")
        path = Path(self.tmp.name) / "bad.mp4"
        path.write_text("Not actually media")
        with self.assertRaises(StudioError):
            self.ws.import_media(path, "bad.mp4")
        self.assertEqual(len(self.ws.listing("media")), 1)

    def test_session_cut_budgets_numbers_and_optimistic_revision(self):
        for cuts in [[{"start": -1, "end": 1}], [{"start": 0, "end": 20}], [{"start": 0, "end": .1}], [{"start": float("nan"), "end": 2}], [{"start": 0, "end": 1}]*13]:
            with self.assertRaises(StudioError):
                self.session(cuts=cuts)
        original = self.session()
        updated = self.ws.save_session({**original, "title": "A revision"})
        self.assertEqual(updated["revision"], 2)
        with self.assertRaisesRegex(StudioError, "changed elsewhere"):
            self.ws.save_session(original)

    def test_captions_need_real_review_and_source_times(self):
        captions = "1\n00:00:00,000 --> 00:00:01,000\nA real moment\n"
        session = self.session(captions=captions)
        with self.assertRaisesRegex(StudioError, "review captions"):
            self.ws.propose("render", {"session_id": session["id"]})
        with self.assertRaises(StudioError):
            self.session(captions=captions.replace("00:00:01,000", "00:01:00,000"))

    def test_proposal_cannot_execute_without_owner_review(self):
        session = self.session(content_reviewed=False)
        with self.assertRaises(StudioError):
            self.ws.propose("render", {"session_id": session["id"]})
        self.assertEqual(self.ws.listing("jobs"), [])

    def test_approval_is_exact_and_one_use_with_real_export(self):
        original_hash = digest(self.source)
        session = self.session()
        action = self.ws.propose("render", {"session_id": session["id"]})
        with self.assertRaisesRegex(StudioError, "does not match"):
            self.ws.approve(action["id"], "0"*64)
        job = self.ws.approve(action["id"], action["plan_sha256"])
        with self.assertRaisesRegex(StudioError, "already used"):
            self.ws.approve(action["id"], action["plan_sha256"])
        result = self.wait_job(job)
        self.assertEqual(result["state"], "completed", result)
        receipt = result["result"]
        self.assertTrue(receipt["files"][0]["full_decode_verified"])
        self.assertFalse(receipt["published"])
        self.assertEqual(receipt["files"][0]["media"]["width"], 1280)
        self.assertEqual(digest(self.source), original_hash)
        self.assertEqual(digest(self.ws.media_path(self.item["id"])), original_hash)

    def test_changed_session_invalidates_approval(self):
        saved = self.session()
        action = self.ws.propose("render", {"session_id": saved["id"]})
        self.ws.save_session({**saved, "cuts": [{"start": 2, "end": 3}]})
        with self.assertRaisesRegex(StudioError, "changed after"):
            self.ws.approve(action["id"], action["plan_sha256"])

    def test_expiry_rejection_and_unsupported_actions(self):
        action = self.ws.propose("bumper", {"title": "Studio test"})
        with self.ws.db() as db:
            value = self.ws.get("actions", action["id"])
            value["expires"] = 0
            db.execute("UPDATE actions SET data=? WHERE id=?", (json.dumps(value), action["id"]))
        with self.assertRaises(StudioError):
            self.ws.approve(action["id"], action["plan_sha256"])
        another = self.ws.propose("bumper", {"title": "Different"})
        self.ws.reject(another["id"])
        with self.assertRaises(StudioError):
            self.ws.approve(another["id"], another["plan_sha256"])
        for kind in ("shell", "publish", "go_live", "delete"):
            with self.assertRaises(StudioError):
                self.ws.propose(kind, {})

    def test_real_vertical_reordered_captioned_sequence(self):
        captions = "1\n00:00:00,000 --> 00:00:01,500\nFirst moment\n\n2\n00:00:04,000 --> 00:00:05,500\nSecond moment\n"
        saved = self.session(format="vertical", cuts=[{"start": 4,"end": 6},{"start": 0,"end": 2}], captions=captions, captions_reviewed=True, fade=True)
        action = self.ws.propose("render", {"session_id": saved["id"]})
        job = self.ws.approve(action["id"], action["plan_sha256"])
        result = self.wait_job(job)
        self.assertEqual(result["state"], "completed", result)
        encoded = result["result"]["files"][0]["media"]
        self.assertEqual((encoded["width"], encoded["height"]), (1080, 1920))
        self.assertAlmostEqual(encoded["duration"], 4, delta=.1)
        srt = (self.ws.root / "exports" / job["id"] / "captions.srt").read_text()
        self.assertLess(srt.index("Second moment"), srt.index("First moment"))
        self.assertIn("00:00:02,000 --> 00:00:03,500", srt)

    def test_real_two_pass_podcast_export(self):
        saved = self.session(format="podcast", cuts=[{"start": 0,"end": 6}])
        action = self.ws.propose("render", {"session_id": saved["id"]})
        result = self.wait_job(self.ws.approve(action["id"], action["plan_sha256"]))
        self.assertEqual(result["state"], "completed", result)
        self.assertEqual(result["result"]["files"][0]["name"], "final.mp3")
        measured = json.loads((self.ws.root/"exports"/result["id"]/"audio-measurement.json").read_text())
        self.assertIn("output", measured)

    def test_real_bumper_handles_literal_filter_characters(self):
        action = self.ws.propose("bumper", {"title": "Dam's studio: {100%} ready", "theme": "hearth"})
        result = self.wait_job(self.ws.approve(action["id"], action["plan_sha256"]))
        self.assertEqual(result["state"], "completed", result)
        self.assertEqual(len(result["result"]["files"]), 2)
        self.assertTrue(all(f["full_decode_verified"] for f in result["result"]["files"]))

    def test_changed_source_cannot_produce_a_receipt(self):
        saved = self.session()
        action = self.ws.propose("render", {"session_id": saved["id"]})
        with self.ws.media_path(self.item["id"]).open("ab") as f:
            f.write(b"source changed")
        result = self.wait_job(self.ws.approve(action["id"], action["plan_sha256"]))
        self.assertEqual(result["state"], "failed")
        self.assertIn("checksum changed", result["error"])
        self.assertNotIn("result", result)

    def test_obs_controls_are_bounded_and_cannot_go_live(self):
        for params in [{"action":"StartStream"},{"action":"shell"},{"action":"record_start"},{"action":"volume","input":"mic","db":6}]:
            with self.assertRaises(StudioError):
                validate_action(params)
        self.assertEqual(validate_action({"action":"mute","input":"mic","muted":True})["muted"], True)
        self.assertEqual(validate_action({"action":"record_start","recording_consent":True})["action"], "record_start")


class HTTPTests(HubFixture):
    def setUp(self):
        super().setUp()
        self.server = StudioServer(self.ws, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        super().tearDown()

    def request(self, method, path, data=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=20)
        body = json.dumps(data).encode() if data is not None else None
        head = {"Origin": self.origin, "Content-Type": "application/json", **(headers or {})}
        connection.request(method, path, body, head)
        response = connection.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        connection.close()
        return result

    def pair(self):
        status, headers, raw = self.request("POST", "/api/pair", {"key": self.ws.pairing_key})
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0], "X-Studio-CSRF": json.loads(raw)["csrf"]}

    def test_authentication_origin_csrf_and_host(self):
        self.assertEqual(self.request("GET", "/api/state")[0], 401)
        paired = self.pair()
        self.assertEqual(self.request("GET", "/api/state", headers=paired)[0], 200)
        self.assertEqual(self.request("POST", "/api/propose", {"kind":"bumper","params":{"title":"Test"}}, {"Cookie":paired["Cookie"]})[0], 401)
        self.assertEqual(self.request("GET", "/api/state", headers={**paired,"Origin":"https://attacker.invalid"})[0], 401)
        self.assertEqual(self.request("GET", "/api/state", headers={**paired,"Host":"attacker.invalid"})[0], 401)

    def test_bearer_tools_cannot_approve_or_reveal_pairing_key(self):
        auth = {"Authorization": "Bearer " + self.ws.pairing_key}
        self.assertEqual(self.request("GET", "/api/state", headers=auth)[0], 200)
        self.assertEqual(self.request("GET", "/api/pairing-key", headers=auth)[0], 401)
        self.assertEqual(self.request("POST", "/api/approve", {}, auth)[0], 401)

    def test_media_ranges_and_static_traversal(self):
        auth = self.pair()
        status, headers, raw = self.request("GET", "/api/media/"+self.item["id"], headers={**auth,"Range":"bytes=0-15"})
        self.assertEqual(status, 206); self.assertEqual(len(raw), 16)
        self.assertIn("Content-Security-Policy", headers)
        self.assertEqual(self.request("GET", "/../.pairing-key", headers=auth)[0], 404)
        self.assertEqual(self.request("GET", "/api/media/../../.pairing-key", headers=auth)[0], 400)
        self.assertEqual(self.request("GET", "/api/media/"+self.item["id"], headers={**auth,"Range":"bytes=999999999-"})[0], 416)

    def test_mcp_discovery_and_harmless_real_call(self):
        client = Client(self.ws.root, self.server.server_port)
        initialized = dispatch({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}, client)
        self.assertEqual(initialized["result"]["serverInfo"]["version"], "0.4.0")
        result = dispatch({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"studio_status","arguments":{}}}, client)
        self.assertFalse(result["result"]["isError"])
        self.assertNotIn("approve", " ".join(t["name"] for t in TOOLS))
        self.assertNotIn(self.ws.pairing_key, json.dumps(result))
        with self.assertRaises(ValueError):
            client.call("studio_approve", {})


if __name__ == "__main__":
    unittest.main()
