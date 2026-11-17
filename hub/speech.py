"""Offline narration through actually installed Windows voices; no cloned identity."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import time

from hub.core import probe_media
from hub.render import finish
from hub.projects import title
from tools.studio_tools import StudioError, export_audio, run_process

_voice_cache = (0, [])
CATALOG = """[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; try { @($s.GetInstalledVoices() | Where-Object {$_.Enabled} | ForEach-Object { @{name=$_.VoiceInfo.Name; language=$_.VoiceInfo.Culture.Name} }) | ConvertTo-Json -Compress } finally {$s.Dispose()}"""


def voices(refresh=False):
    global _voice_cache
    if not refresh and time.monotonic()-_voice_cache[0] < 300:
        return _voice_cache[1]
    items = []
    if platform.system() == "Windows" and shutil.which("powershell.exe"):
        try:
            result = subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",CATALOG],capture_output=True,text=True,encoding="utf-8",timeout=15,check=True)
            raw = json.loads(result.stdout.lstrip("\ufeff"))
            for item in raw if isinstance(raw,list) else [raw]:
                if isinstance(item,dict) and isinstance(item.get("name"),str) and 0<len(item["name"])<200:
                    items.append({"id":hashlib.sha256(item["name"].encode()).hexdigest()[:16],"name":item["name"],"language":item.get("language","unknown"),"engine":"windows_sapi"})
        except (ValueError,OSError,subprocess.SubprocessError):
            pass
    _voice_cache = (time.monotonic(), items)
    return items


def text(value, maximum=5000):
    if not isinstance(value,str) or not value.strip() or len(value)>maximum or any(ord(c)<32 and c not in "\n\r\t" for c in value):
        raise StudioError(f"Supply reviewed plain narration text of 1–{maximum} characters")
    return value.strip()


def voice(key):
    found = next((v for v in voices() if v["id"]==key),None)
    if not found:
        raise StudioError("Choose an actually installed narration voice on this computer")
    return found


def prepare(data):
    selected = voice(data.get("voice_id"))
    rate = data.get("rate",0)
    if type(rate) is not int or not -2<=rate<=2:
        raise StudioError("Narration rate must be an integer from -2 to 2")
    if data.get("content_reviewed") is not True:
        raise StudioError("Review the narration text and permission to use it first")
    return {"title":title(data.get("title")),"text":text(data.get("text")),"voice_id":selected["id"],"voice_name":selected["name"],"engine":"windows_sapi","rate":rate,"content_reviewed":True}


def synthesize(content, selected, rate, target):
    if platform.system()!="Windows":
        raise StudioError("Local Windows narration is unavailable on this executing computer")
    if voice(selected["id"])["name"] != selected["name"]:
        raise StudioError("Installed narration voice changed; review again")
    target=Path(target)
    if target.exists():
        raise StudioError("Narration output already exists")
    config=target.with_suffix(".speech.json")
    config.write_text(json.dumps({"text":content,"voice":selected["name"],"rate":rate,"output":str(target.resolve())}),encoding="utf-8")
    try:
        run_process(["powershell.exe","-NoProfile","-NonInteractive","-File",str(Path(__file__).with_name("native_speech.ps1")),"-RequestFile",str(config.resolve())],120)
    except (OSError,subprocess.SubprocessError,StudioError):
        raise StudioError("Local narration failed. Check the installed voice and permitted PowerShell execution; no remote fallback was used") from None
    finally:
        config.unlink(missing_ok=True)
    info=probe_media(target)
    if not info["audio_tracks"] or info["duration"]>1800:
        raise StudioError("Narration duration exceeds its local processing budget")
    return info["duration"]


def render(ws,job_id,data):
    directory=ws.root/"exports"/job_id;directory.mkdir(exist_ok=False)
    if shutil.disk_usage(directory).free<100_000_000:raise StudioError("Free at least 100 MB before narration")
    ws.progress(job_id,"Synthesizing reviewed text with a local voice",1,3)
    duration=synthesize(data["text"],voice(data["voice_id"]),data["rate"],directory/"narration.wav")
    ws.progress(job_id,"Measuring and encoding narration",2,3)
    measurement=export_audio(directory/"narration.wav",directory/"narration.mp3",channels=1,lufs=-19)
    (directory/"script.txt").write_text(data["text"],encoding="utf-8")
    (directory/"audio-measurement.json").write_text(json.dumps(measurement,indent=2),encoding="utf-8")
    result=finish(ws,job_id,["narration.wav","narration.mp3"],expected_duration=duration)
    result.update(engine="windows_sapi",voice=data["voice_name"],voice_cloning=False,provider_calls=0,generated_narration=True)
    result["downloads"] += ["script.txt","audio-measurement.json"]
    (directory/"receipt.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    ws.progress(job_id,"Narration files verified",3,3)
    return result
