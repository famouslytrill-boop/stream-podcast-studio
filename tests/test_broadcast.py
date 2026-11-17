import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from unittest.mock import patch

from hub.capture import scan, validate_root
from hub.core import digest
from tests.test_hub import HubFixture
from tools.studio_tools import StudioError


class BroadcastTests(HubFixture):
    def action(self,kind,params):
        action=self.ws.propose(kind,params)
        result=self.wait_job(self.ws.approve(action["id"],action["plan_sha256"]))
        self.assertEqual(result["state"],"completed",result.get("error"))
        return result

    def clip(self,**changes):
        return {"media_id":self.item["id"],"start":0,"end":1,"label":"Opening",**changes}

    def test_episode_review_final_caption_time_and_segment_bounds(self):
        base={"title":"Episode","clips":[self.clip()],"content_reviewed":True}
        bad=[{"content_reviewed":False},{"clips":[]},{"clips":[self.clip(end=40)]},{"clips":[self.clip(audio_track=9)]},
             {"captions":"1\n00:00:00,000 --> 00:00:01,500\nToo late\n","captions_reviewed":True},
             {"captions":"1\n00:00:00,000 --> 00:00:00,500\nReview needed\n"}]
        for change in bad:
            with self.subTest(change=change),self.assertRaises(StudioError):self.ws.propose("episode",{**base,**change})

    def test_real_multi_source_video_episode_and_chapters(self):
        other=Path(self.tmp.name)/"other.mp4"
        subprocess.run(["ffmpeg","-nostdin","-v","error","-f","lavfi","-i","color=c=red:s=320x180:r=30:d=3",
                        "-f","lavfi","-i","sine=frequency=800:sample_rate=48000:duration=3","-c:v","libx264","-threads","2","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(other)],check=True)
        item=self.ws.import_media(other,"Closing.mp4")
        job=self.action("episode",{"title":"Two sources","format":"landscape","clips":[self.clip(media_id=item["id"],label="Red opening",end=1),self.clip(label="Game",start=2,end=3)],
                                   "content_reviewed":True,"speech_cleanup":True,"captions_reviewed":True,"captions":"1\n00:00:01,000 --> 00:00:01,700\nFinal timeline\n"})
        receipt=job["result"];out=self.ws.root/"exports"/job["id"]
        self.assertEqual([x["name"] for x in receipt["files"]],["episode.mp4","podcast.wav","podcast.mp3"])
        self.assertTrue(all(x["full_decode_verified"] for x in receipt["files"]))
        self.assertTrue(receipt["speech_cleanup_applied"])
        self.assertEqual([c["start_ms"] for c in receipt["chapters"]],[0,1000])
        probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_chapters","-show_streams","-of","json",str(out/"episode.mp4")]))
        self.assertEqual([c["tags"]["title"] for c in probe["chapters"]],["Red opening","Game"])
        frame=subprocess.check_output(["ffmpeg","-nostdin","-v","error","-i",str(out/"episode.mp4"),"-frames:v","1","-vf","scale=1:1","-pix_fmt","rgb24","-f","rawvideo","-"])
        self.assertGreater(frame[0],200);self.assertLess(frame[1],25)
        wav=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-of","json",str(out/"podcast.wav")]))["streams"][0]
        self.assertEqual(wav["codec_name"],"pcm_s24le")
        self.assertEqual(job["progress"]["completed_steps"],5)
        self.assertEqual(digest(other),item["sha256"])
        self.assertIn("delivery.zip",receipt["downloads"])

    def test_audio_only_episode_can_reorder_segments(self):
        job=self.action("episode",{"title":"Podcast","clips":[self.clip(start=2,end=3),self.clip(start=0,end=1)],"content_reviewed":True})
        self.assertEqual(len(job["result"]["files"]),2)
        self.assertEqual(job["result"]["files"][0]["media"]["duration"],2)

    def test_changed_episode_source_cannot_finish(self):
        action=self.ws.propose("episode",{"title":"Episode","clips":[self.clip()],"content_reviewed":True})
        self.ws.media_path(self.item["id"]).write_bytes(b"changed")
        job=self.wait_job(self.ws.approve(action["id"],action["plan_sha256"]))
        self.assertEqual(job["state"],"failed")
        self.assertIn("checksum",job["error"])

    def test_remux_preserves_two_compressed_audio_tracks(self):
        path=Path(self.tmp.name)/"capture.mkv"
        subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(self.source),"-f","lavfi","-i","sine=frequency=900:sample_rate=48000:duration=8",
                        "-map","0:v:0","-map","0:a:0","-map","1:a:0","-c:v","copy","-c:a","aac","-shortest",str(path)],check=True)
        item=self.ws.import_media(path,"OBS capture.mkv")
        with self.assertRaises(StudioError):self.ws.propose("edit_copy",{"media_id":item["id"]})
        job=self.action("edit_copy",{"media_id":item["id"],"content_reviewed":True})
        r=job["result"]
        self.assertTrue(r["compressed_stream_hashes_match"])
        self.assertFalse(r["transcoded"])
        self.assertEqual(r["audio_tracks_preserved"],2)
        self.assertEqual(r["files"][0]["media"]["audio_tracks"],2)
        self.assertEqual(digest(path),item["sha256"])

    def folder(self):
        root=Path(self.tmp.name)/"OBS Recordings";root.mkdir()
        path=root/"finished.mp4";shutil.copyfile(self.source,path)
        stamp=time.time()-10;os.utime(path,(stamp,stamp))
        self.ws.recordings_root=root
        return root,path

    def test_capture_scan_is_scoped_and_import_is_reviewed(self):
        root,path=self.folder();(root/"unrelated.txt").write_text("not media");(root/"subfolder").mkdir();shutil.copyfile(self.source,root/"subfolder/hidden.mp4")
        items=scan(self.ws)["recordings"]
        self.assertEqual([i["name"] for i in items],["finished.mp4"])
        self.assertNotIn(str(root),json.dumps(items))
        with self.assertRaises(StudioError):self.ws.propose("capture_import",{"recording_id":items[0]["id"]})
        job=self.action("capture_import",{"recording_id":items[0]["id"],"recording_finished_reviewed":True})
        imported=self.ws.get("media",job["result"]["media_id"])
        self.assertEqual(imported["sha256"],digest(path))
        self.assertNotIn(str(root),json.dumps(job))

    def test_capture_changed_after_review_and_recent_files_rejected(self):
        root,path=self.folder();item=scan(self.ws)["recordings"][0]
        action=self.ws.propose("capture_import",{"recording_id":item["id"],"recording_finished_reviewed":True})
        with path.open("ab") as out:out.write(b"changed")
        job=self.wait_job(self.ws.approve(action["id"],action["plan_sha256"]))
        self.assertEqual(job["state"],"failed")
        self.assertFalse(scan(self.ws)["recordings"][0]["stable"])
        self.assertEqual(len(self.ws.listing("media")),1)

    def test_capture_active_obs_and_mid_copy_changes_are_rejected(self):
        _,path=self.folder();item=scan(self.ws)["recordings"][0]
        with patch.object(self.ws,"obs_password_configured",return_value=True),patch("hub.obs.status",return_value={"recording":{"outputActive":True}}):
            a=self.ws.propose("capture_import",{"recording_id":item["id"],"recording_finished_reviewed":True})
            job=self.wait_job(self.ws.approve(a["id"],a["plan_sha256"]))
            self.assertEqual(job["state"],"failed");self.assertIn("OBS is recording",job["error"])
        original=self.ws.import_media
        def changed(source,name):
            copied=original(source,name)
            with path.open("ab") as stream:stream.write(b"new-data")
            return copied
        with patch.object(self.ws,"import_media",side_effect=changed):
            a=self.ws.propose("capture_import",{"recording_id":item["id"],"recording_finished_reviewed":True})
            job=self.wait_job(self.ws.approve(a["id"],a["plan_sha256"]))
            self.assertEqual(job["state"],"failed")
            self.assertEqual(len(self.ws.listing("media")),1)

    def test_capture_root_is_explicit_local_and_links_are_not_followed(self):
        for bad in ("https://example.com/recordings","//server/share",".",str(Path.home()),str(Path(Path.cwd().anchor))):
            with self.subTest(value=bad),self.assertRaises(StudioError):validate_root(bad)
        root,path=self.folder()
        try:(root/"linked.mp4").symlink_to(self.source)
        except OSError:return
        self.assertEqual([x["name"] for x in scan(self.ws)["recordings"]],[path.name])
