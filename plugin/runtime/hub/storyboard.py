"""Versioned storyboards and a real procedural scene/voice film renderer.

Frame accounting adapts SONARA buildFilmTimeline at main@1693036c4e50b6b4d15db5b4943752cac5552b6d.
"""
import json
import math
from pathlib import Path
import shutil
import textwrap

from hub.core import FORMATS, digest
from hub.creative import complete, checked_sources
from hub.projects import read_document, save_document, title
from hub.speech import synthesize, text, voice
from tools.studio_tools import StudioError, executable, finite, run_process


def prepare(ws,data,review=True):
    if not isinstance(data,dict):raise StudioError("Storyboard needs a structured plan")
    scenes=data.get("scenes")
    if not isinstance(scenes,list) or not 1<=len(scenes)<=8:raise StudioError("Use one to eight storyboard scenes")
    layout=data.get("format","landscape")
    if layout not in {"landscape","vertical"}:raise StudioError("Choose landscape or vertical storyboard video")
    selected=voice(data["voice_id"]) if data.get("voice_id") else None
    rate=data.get("rate",0)
    if type(rate) is not int or not -2<=rate<=2:raise StudioError("Voice rate must be -2 to 2")
    clean=[]
    for scene in scenes:
        if not isinstance(scene,dict):raise StudioError("Each scene needs a title, text and timing")
        narration=scene.get("text","")
        if narration: narration=text(narration,400)
        if not isinstance(narration,str):raise StudioError("Scene text must be plain text")
        seconds=finite(scene.get("seconds",6),"scene seconds",0,60)
        if seconds and seconds<2:raise StudioError("Use 2–60 seconds, or 0 for measured voice timing")
        if seconds==0 and not (selected and narration):raise StudioError("Automatic scene timing needs a selected voice and narration text")
        asset=None
        if scene.get("visual_id"):
            m=ws.get("media",scene["visual_id"])
            if not (m.get("image") or m["video"]):raise StudioError("Scene visual must be imported artwork or footage")
            asset={"id":m["id"],"name":m["name"],"sha256":m["sha256"],"image":m.get("image",False),"duration":m["duration"]}
            if not asset["image"] and (seconds==0 or seconds>asset["duration"]) and scene.get("loop") is not True:
                raise StudioError("Short footage or automatic scene timing needs explicit visual looping")
        clean.append({"title":title(scene.get("title"),80),"text":narration,"seconds":seconds,"visual":asset,"visual_id":asset["id"] if asset else "",
                      "loop":scene.get("loop") is True,"motion":scene.get("motion") is True})
    if sum(s["seconds"] for s in clean)>240:raise StudioError("Keep a storyboard within four minutes")
    if review and data.get("content_reviewed") is not True:raise StudioError("Review all scene text, visuals and permissions before rendering")
    result={"title":title(data.get("title")),"format":layout,"voice_id":selected["id"] if selected else "","voice_name":selected["name"] if selected else "",
            "rate":rate,"scenes":clean,"content_reviewed":data.get("content_reviewed") is True}
    if data.get("document_id"):
        doc=read_document(ws,data["document_id"])
        if data.get("revision")!=doc["revision"]:raise StudioError("Storyboard changed elsewhere. Reload its current revision")
        result.update(document_id=doc["id"],revision=doc["revision"])
    return result


def save(ws,data):
    draft=prepare(ws,{k:v for k,v in data.items() if k not in {"document_id","revision"}},review=False)
    doc=save_document(ws,{"id":data.get("document_id"),"revision":data.get("revision"),"title":"Storyboard: "+draft["title"][:135],
                          "content":json.dumps({"schema":"emberbanter.storyboard.v1","plan":draft},indent=2)})
    return {**draft,"document_id":doc["id"],"revision":doc["revision"]}


def read(ws,document_id):
    doc=read_document(ws,document_id)
    try:data=json.loads(doc["content"])
    except ValueError:raise StudioError("This studio file is not a storyboard") from None
    if data.get("schema")!="emberbanter.storyboard.v1":raise StudioError("This studio file is not a storyboard")
    return {**data["plan"],"document_id":doc["id"],"revision":doc["revision"]}


def render(ws,job_id,data):
    sources=[s["visual"] for s in data["scenes"] if s["visual"]]
    checked_sources(ws,sources)
    directory=ws.root/"exports"/job_id;directory.mkdir(exist_ok=False)
    if shutil.disk_usage(directory).free<500_000_000:raise StudioError("Free at least 500 MB before storyboard rendering")
    width,height=FORMATS[data["format"]]
    font=next((p for p in [Path("C:/Windows/Fonts/segoeui.ttf"),Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if p.is_file()),None)
    if not font:raise StudioError("A supported local title font is required")
    shutil.copyfile(font,directory/"font.ttf")
    timeline=[];cursor_frames=0
    for i,scene in enumerate(data["scenes"]):
        ws.progress(job_id,f"Rendering scene {i+1} of {len(data['scenes'])}",i,len(data["scenes"])+2)
        prefix=f"scene-{i+1:02d}"
        spoken=0
        if data["voice_id"] and scene["text"]:
            spoken=synthesize(scene["text"],voice(data["voice_id"]),data["rate"],directory/(prefix+".wav"))
        seconds=scene["seconds"] or max(3,spoken+.6)
        frames=math.ceil(seconds*30);seconds=frames/30
        if seconds>60 or spoken+.2>seconds:raise StudioError(f"Scene {i+1} narration exceeds its slot. Lengthen it or choose automatic timing")
        if cursor_frames+frames>7200:raise StudioError("Measured storyboard exceeds four minutes")
        heading="\n".join(textwrap.wrap(scene["title"],24 if width<height else 40))
        body="\n".join(textwrap.wrap(scene["text"],42 if width<height else 66))
        (directory/(prefix+"-title.txt")).write_text(heading,encoding="utf-8")
        (directory/(prefix+"-text.txt")).write_text(body,encoding="utf-8")
        args=[executable("ffmpeg"),"-nostdin","-hide_banner","-n","-threads","2"]
        visual=scene["visual"]
        if visual:
            if visual["image"]:args += ["-loop","1","-framerate","30"]
            elif scene["loop"]:args += ["-stream_loop","-1"]
            args += ["-protocol_whitelist","file,pipe","-i",str(ws.media_path(visual["id"]))]
        else:args += ["-f","lavfi","-i",f"color=c=0x101216:s={width}x{height}:r=30:d={seconds}"]
        if spoken:args += ["-protocol_whitelist","file,pipe","-i",prefix+".wav"]
        else:args += ["-f","lavfi","-i","anullsrc=r=48000:cl=stereo"]
        args += ["-loop","1","-framerate","30","-i",str(Path(__file__).parent/"web/brand/badge.png")]
        base=f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=30"
        if visual and visual["image"] and scene["motion"]:
            base += f",zoompan=z='min(pzoom+0.0002,1.04)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={width}x{height}:fps=30"
        base += ",drawbox=x=0:y=0:w=iw:h=ih:color=0x101216@0.65:t=fill[base]"
        title_y=round(height*.29);body_y=round(height*.47)
        filters=[base,"[2:v]scale=90:90[badge]","[base][badge]overlay=x=55:y=45[marked]",
                 f"[marked]drawbox=x=60:y={title_y-30}:w=100:h=6:color=0xFF6A3D:t=fill,"
                 f"drawtext=fontfile=font.ttf:textfile={prefix}-title.txt:expansion=none:fontcolor=0xF4F1E8:fontsize=44:line_spacing=9:x=60:y={title_y},"
                 f"drawtext=fontfile=font.ttf:textfile={prefix}-text.txt:expansion=none:fontcolor=0x8EF2CE:fontsize=26:line_spacing=9:x=60:y={body_y},"
                 f"fade=t=in:d=0.2,fade=t=out:st={max(0,seconds-.2)}:d=0.2[v]",
                 f"[1:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={seconds},asetpts=PTS-STARTPTS[a]"]
        args += ["-filter_complex_threads","1","-filter_complex",";".join(filters),"-map","[v]","-map","[a]","-t",str(seconds),
                 "-c:v","libx264","-threads","2","-preset","veryfast","-crf","21","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-ar","48000","-ac","2","-map_metadata","-1",prefix+".mp4"]
        run_process(args,600,cwd=directory)
        timeline.append({"scene":i+1,"title":scene["title"],"start_frame":cursor_frames,"frame_count":frames,"end_frame":cursor_frames+frames,"spoken_seconds":spoken})
        cursor_frames+=frames
    ws.progress(job_id,"Assembling storyboard film",len(data["scenes"]),len(data["scenes"])+2)
    (directory/"concat.txt").write_text("".join(f"file 'scene-{i+1:02d}.mp4'\n" for i in range(len(timeline))),encoding="ascii")
    run_process([executable("ffmpeg"),"-nostdin","-v","error","-n","-f","concat","-safe","1","-i","concat.txt","-map","0:v:0","-map","0:a:0","-c","copy","-movflags","+faststart","storyboard.mp4"],600,cwd=directory)
    (directory/"shot-list.json").write_text(json.dumps({"fps":30,"frames":cursor_frames,"duration":cursor_frames/30,"scenes":timeline},indent=2),encoding="utf-8")
    (directory/"script.txt").write_text("\n\n".join(s["title"]+"\n"+s["text"] for s in data["scenes"]),encoding="utf-8")
    result=complete(ws,job_id,data,sources,["storyboard.mp4"],cursor_frames/30,(width,height),extras={"engine":"procedural_scene_renderer","narration_engine":"windows_sapi" if data["voice_id"] else None,"provider_calls":0,"timeline":timeline},supplemental=["shot-list.json","script.txt"])
    ws.progress(job_id,"Storyboard film verified",len(data["scenes"])+2,len(data["scenes"])+2)
    return result
