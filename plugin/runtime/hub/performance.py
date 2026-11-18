"""Measured local encoder checks and explicit-unit planning; no automatic OBS tuning."""
import json
import os
from pathlib import Path
import platform
import subprocess
import time

from hub.core import digest, probe_media
from tools.studio_tools import StudioError, executable, finite, run_process

_hardware_cache=None


def hardware():
    global _hardware_cache
    if _hardware_cache is not None:return _hardware_cache
    result={"os":platform.system(),"os_release":platform.release(),"logical_processors":os.cpu_count(),"gpu":[],"memory_bytes":None,
            "hdr":"not_verified","display_refresh_hz":None,"display_resolution":None}
    if platform.system()=="Windows":
        script="""[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false); $c=Get-CimInstance Win32_ComputerSystem; $g=@(Get-CimInstance Win32_VideoController); @{memory_bytes=$c.TotalPhysicalMemory; gpu=@($g|ForEach-Object {$_.Name}); display_refresh_hz=$g[0].CurrentRefreshRate; display_resolution=@($g[0].CurrentHorizontalResolution,$g[0].CurrentVerticalResolution)} | ConvertTo-Json -Compress"""
        try:
            p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",script],capture_output=True,text=True,encoding="utf-8",timeout=15,check=True)
            result.update(json.loads(p.stdout.lstrip("\ufeff")))
        except (OSError,ValueError,subprocess.SubprocessError):pass
    _hardware_cache=result
    return result


def plan(data):
    streams=data.get("streams",[])
    if not isinstance(streams,list) or not 1<=len(streams)<=3:raise StudioError("Plan one to three outbound streams")
    clean=[]
    for s in streams:
        if not isinstance(s,dict):raise StudioError("Each stream needs explicit video/audio bitrates")
        clean.append({"video_kbps":finite(s.get("video_kbps"),"video kbps",100,50_000),"audio_kbps":finite(s.get("audio_kbps",160),"audio kbps",32,512)})
    total=sum(s["video_kbps"]+s["audio_kbps"] for s in clean)
    upload=None if data.get("measured_upload_mbps") is None else finite(data["measured_upload_mbps"],"measured upload Mbps",.01,100_000)
    fps=finite(data.get("fps",30),"output FPS",1,120)
    seconds=finite(data.get("duration_seconds",3600),"duration seconds",1,43200)
    return {"streams":clean,"direct_outbound_mbps":total/1000,"planned_upload_with_headroom_mbps":total*1.5/1000,
            "headroom_basis":"Internal conservative 1.5x planning rule, not a platform eligibility threshold",
            "measured_upload_mbps":upload,"headroom_met":None if upload is None else upload>=total*1.5/1000,
            "payload_mib":total*1000*seconds/(8*1048576),"frame_count":round(seconds*fps),"frame_interval_ms":1000/fps,
            "actual_simulcasting":"not_configured","unknown":["network_acceptance"] if upload is None else [],
            "hdr":"not_verified; use an explicitly tested end-to-end HDR chain before enabling it",
            "refresh_rate_note":"Display refresh, game FPS and encoded stream FPS are separate settings",
            "published":False,"obs_settings_changed":False}


def prepare(data):
    if data.get("not_live_confirmed") is not True:raise StudioError("Confirm you are not streaming or recording before benchmarking encoders")
    return {"not_live_confirmed":True,"width":1280,"height":720,"fps":30,"seconds":3,"cpu_threads":2,"attempt_gpu":data.get("attempt_gpu") is True}


def benchmark(ws,job_id,data):
    if ws.obs_password_configured():
        from hub.obs import status
        obs=status(ws)
        if obs["stream"].get("outputActive") or obs["recording"].get("outputActive"):raise StudioError("Wait until OBS is not streaming or recording before this encoder check")
    directory=ws.root/"exports"/job_id;directory.mkdir(exist_ok=False)
    advertised=run_process([executable("ffmpeg"),"-hide_banner","-encoders"],15).stdout
    encoders=["libx264"]
    if data["attempt_gpu"] and "h264_amf" in advertised:encoders.append("h264_amf")
    results=[];outputs=[]
    for i,encoder in enumerate(encoders):
        ws.progress(job_id,"Checking "+encoder,i,len(encoders)+1)
        name=encoder+".mp4"
        args=[executable("ffmpeg"),"-nostdin","-v","error","-n","-f","lavfi","-i","testsrc2=size=1280x720:rate=30:duration=3",
              "-an","-c:v",encoder,"-threads","2","-pix_fmt","yuv420p"]
        if encoder=="libx264":args += ["-preset","veryfast","-crf","23"]
        args += [name]
        started=time.monotonic()
        try:
            run_process(args,60,cwd=directory);elapsed=time.monotonic()-started
            info=probe_media(directory/name)
            run_process([executable("ffmpeg"),"-nostdin","-v","error","-xerror","-i",str(directory/name),"-map","0:v:0","-f","null","-"],60)
            if abs(info["duration"]-3)>.1 or (info["width"],info["height"])!=(1280,720):raise StudioError("Encoder check output does not match its workload")
            results.append({"encoder":encoder,"executed":True,"wall_seconds":elapsed,"frames":90,"whole_job_fps":90/elapsed,"sha256":digest(directory/name),"full_decode_verified":True})
            outputs.append(name)
        except (StudioError,OSError,subprocess.SubprocessError):
            (directory/name).unlink(missing_ok=True)
            results.append({"encoder":encoder,"executed":False,"reason":"Advertised encoder did not complete this actual workload"})
    report={"hardware":hardware(),"workload":"3s synthetic 720p30; encode wall time includes process startup","results":results,
            "not_a_game_or_stream_stability_test":True,"comparable_render_eta":None,"obs_settings_changed":False,"provider_calls":0,"published":False}
    (directory/"performance.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    ws.progress(job_id,"Encoder evidence saved",len(encoders)+1,len(encoders)+1)
    return {"report":report,"downloads":outputs+["performance.json"],"files":[{"name":n,"sha256":digest(directory/n)} for n in outputs],"published":False}
