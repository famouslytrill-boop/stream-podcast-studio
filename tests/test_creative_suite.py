import json
from pathlib import Path
import struct
import subprocess
import time
import unittest
import wave
from unittest.mock import patch

from tests.test_hub import HubFixture
from hub.core import digest
from hub.projects import save_project, save_document, read_document
from hub.shell import run as shell
from hub.midi import make_notes
from tools.studio_tools import StudioError


class CreativeSuiteTests(HubFixture):
    def artwork(self):
        path = Path(self.tmp.name)/"art.png"
        subprocess.run(["ffmpeg","-nostdin","-v","error","-f","lavfi","-i","color=c=blue:s=320x180","-frames:v","1","-threads","1",str(path)],check=True)
        return self.ws.import_media(path,"art.png")

    def run_action(self, kind, params):
        action = self.ws.propose(kind, params)
        return self.wait_job(self.ws.approve(action["id"], action["plan_sha256"]))

    def test_projects_and_revisioned_actual_text_files(self):
        project = save_project(self.ws,{"title":"First song","kind":"music","bpm":100,"key":"A minor","assets":[self.item["id"]]})
        self.assertEqual(project["musical_metadata_basis"],"owner_supplied")
        first = save_document(self.ws,{"title":"Lyrics","project_id":project["id"],"content":"Verse one\n"})
        second = save_document(self.ws,{**first,"content":"Verse one\nA new line\n"})
        self.assertEqual((self.ws.root/"documents"/first["file"]).read_text(),"Verse one\n")
        self.assertEqual(read_document(self.ws,first["id"])["content"],second["content"])
        with self.assertRaisesRegex(StudioError,"changed elsewhere"):
            save_document(self.ws,first)
        with self.assertRaises(StudioError):
            save_project(self.ws,{**project,"revision":0})

    def test_shell_scoped_file_io_and_unknown_commands(self):
        doc=shell(self.ws,"new Session notes")["document"]
        value=shell(self.ws,f"write {doc['id']} 1 Literally $(echo private) and backticks `x`.")
        self.assertIn("$(echo private)",value["document"]["content"])
        self.assertEqual(shell(self.ws,"read "+doc["id"])["document"]["revision"],2)
        for command in ("powershell Get-ChildItem", "python -c print(1)", "read ../../.pairing-key", "open cmd.exe", "run shell {}"):
            with self.assertRaises(StudioError): shell(self.ws,command)
        self.assertEqual(shell(self.ws,"status")["counts"]["documents"],1)
        self.assertNotIn(self.ws.pairing_key,json.dumps(shell(self.ws,"apps")))

    def test_outside_document_changes_are_detected(self):
        doc=save_document(self.ws,{"title":"Notes","content":"Original"})
        (self.ws.root/"documents"/doc["file"]).write_text("Changed externally")
        with self.assertRaisesRegex(StudioError,"outside the hub"):read_document(self.ws,doc["id"])

    def test_mix_rights_bad_values_and_source_checksum(self):
        base={"title":"Mix","tracks":[{"media_id":self.item["id"],"end":3}],"rights_reviewed":True}
        for change in [{"rights_reviewed":False},{"tracks":[{"media_id":self.item["id"],"gain_db":20}]},{"tracks":[]},{"target_lufs":-5}]:
            with self.assertRaises(StudioError):self.ws.propose("music_mix",{**base,**change})
        action=self.ws.propose("music_mix",base)
        with self.ws.media_path(self.item["id"]).open("ab") as f:f.write(b"changed")
        result=self.wait_job(self.ws.approve(action["id"],action["plan_sha256"]))
        self.assertEqual(result["state"],"failed")
        self.assertIn("checksum",result["error"])

    def test_real_two_stem_balance_offset_mix(self):
        original=digest(self.ws.media_path(self.item["id"]))
        result=self.run_action("music_mix",{"title":"Stereo mix","rights_reviewed":True,"target_lufs":-16,"tracks":[
            {"media_id":self.item["id"],"start":0,"end":4,"pan":-1,"gain_db":-6},
            {"media_id":self.item["id"],"start":1,"end":4,"pan":1,"offset":.5,"gain_db":-9}]})
        self.assertEqual(result["state"],"completed",result)
        self.assertTrue(result["result"]["source_preserved"])
        self.assertIn("delivery.zip",result["result"]["downloads"])
        self.assertTrue(all(f["full_decode_verified"] for f in result["result"]["files"]))
        wav=self.ws.root/"exports"/result["id"]/"mix.wav"
        with wave.open(str(wav),"rb") as f:
            self.assertEqual(f.getsampwidth(),3); self.assertEqual(f.getnchannels(),2)
            samples=f.readframes(12000)
        left=max(abs(int.from_bytes(samples[i:i+3],"little",signed=True)) for i in range(0,len(samples),6))
        right=max(abs(int.from_bytes(samples[i+3:i+6],"little",signed=True)) for i in range(0,len(samples),6))
        self.assertGreater(left,1000);self.assertLess(right,max(2,left*.001))
        self.assertEqual(original,digest(self.ws.media_path(self.item["id"])))

    def test_real_artwork_music_video(self):
        art=self.artwork()
        self.assertTrue(art["image"])
        result=self.run_action("music_video",{"title":"Original music visual","audio_id":self.item["id"],"visual_id":art["id"],
                                              "end":3,"rights_reviewed":True,"motion":True,"waveform":True})
        self.assertEqual(result["state"],"completed",result)
        info=result["result"]["files"][0]
        self.assertEqual((info["media"]["width"],info["media"]["height"]),(1280,720))
        self.assertTrue(result["result"]["waveform_from_actual_audio"])

    def test_real_green_screen_composition(self):
        art=self.artwork(); path=Path(self.tmp.name)/"green.mp4"
        subprocess.run(["ffmpeg","-nostdin","-v","error","-f","lavfi","-i","color=c=0x00FF00:s=320x180:d=2:r=30",
                        "-vf","drawbox=x=140:y=60:w=40:h=60:color=yellow:t=fill","-c:v","libx264","-threads","2",str(path)],check=True)
        green=self.ws.import_media(path,"green.mp4")
        result=self.run_action("music_video",{"title":"Chroma test","audio_id":self.item["id"],"visual_id":art["id"],
            "foreground_id":green["id"],"end":2,"waveform":False,"rights_reviewed":True})
        self.assertEqual(result["state"],"completed",result)
        self.assertTrue(result["result"]["green_screen_applied"])
        output=self.ws.root/"exports"/result["id"]/"music-video.mp4"
        raw=subprocess.run(["ffmpeg","-v","error","-ss","1","-i",str(output),"-vf","scale=32:18","-frames:v","1","-pix_fmt","rgb24","-f","rawvideo","pipe:1"],capture_output=True,check=True).stdout
        # Background near lower-left becomes blue; foreground in center stays yellow.
        background=raw[(14*32+2)*3:(14*32+2)*3+3]
        center=raw[(10*32+16)*3:(10*32+16)*3+3]
        self.assertGreater(background[2],150);self.assertLess(background[1],70)
        self.assertGreater(center[0],120);self.assertGreater(center[1],120)

    def test_short_footage_needs_explicit_looping(self):
        path=Path(self.tmp.name)/"short.mp4"
        subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(self.source),"-t","1","-c","copy",str(path)],check=True)
        short=self.ws.import_media(path,"short.mp4")
        params={"title":"Loop","audio_id":self.item["id"],"visual_id":short["id"],"end":3,"rights_reviewed":True}
        with self.assertRaisesRegex(StudioError,"shorter"):
            self.ws.propose("music_video",params)
        self.assertTrue(self.ws.propose("music_video",{**params,"loop_visual":True})["params"]["loop_visual"])

    def test_real_midi_sketch_and_diatonic_notes(self):
        notes=make_notes({"key":"A minor","bars":4})
        self.assertTrue(all(n["note"]%12 in {0,2,4,5,7,9,11} for n in notes if n["channel"]!=9))
        result=self.run_action("midi",{"title":"A minor sketch","bars":1,"key":"A minor","bpm":120})
        self.assertEqual(result["state"],"completed",result)
        data=(self.ws.root/"exports"/result["id"]/"sketch.mid").read_bytes()
        self.assertEqual(data[:4],b"MThd");self.assertEqual(struct.unpack(">IHHH",data[4:14]),(6,1,4,480))
        self.assertEqual(data.count(b"MTrk"),4)
        self.assertIn("guide.wav",result["result"]["downloads"])

    def test_engineering_recipe_and_launch_allowlist(self):
        action=shell(self.ws,"check")["proposal"]
        result=self.wait_job(self.ws.approve(action["id"],action["plan_sha256"]))
        self.assertEqual(result["state"],"completed",result)
        self.assertEqual(result["result"]["report"]["source_files_changed"],0)
        self.assertFalse(result["result"]["report"]["github_checks_started"])
        self.assertEqual(result["progress"]["completed_steps"],3)
        with self.assertRaises(StudioError):self.ws.propose("launch_app",{"app":"arbitrary"})
        with patch("hub.apps.resolve",return_value=Path("/verified/obs")),patch("hub.workflows.resolve",return_value=Path("/verified/obs")),patch("hub.apps.subprocess.Popen") as proc:
            proc.return_value.pid=42
            launched=self.run_action("launch_app",{"app":"obs"})
            self.assertEqual(launched["state"],"completed",launched)
            self.assertEqual(proc.call_args.kwargs["shell"],False)
            self.assertEqual(proc.call_args.args[0],[str(Path("/verified/obs"))])


if __name__=="__main__":unittest.main()
