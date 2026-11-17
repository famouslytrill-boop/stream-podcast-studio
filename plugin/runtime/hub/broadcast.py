"""Non-destructive multi-source episodes and packet-verified OBS editing copies."""
import json
from pathlib import Path
import shutil

from hub.core import FORMATS, digest
from hub.creative import checked_sources, complete
from hub.projects import title
from tools.captions import ass_text, parse_srt, srt_text
from tools.studio_tools import StudioError, executable, export_audio, finite, measure, run_process


def prepare_episode(ws, data):
    clips = data.get("clips")
    if not isinstance(clips, list) or not 1 <= len(clips) <= 12:
        raise StudioError("Arrange one to twelve episode segments")
    layout = data.get("format", "podcast")
    if layout not in FORMATS:
        raise StudioError("Choose podcast, landscape or vertical")
    clean, duration = [], 0
    for clip in clips:
        if not isinstance(clip, dict):
            raise StudioError("Each segment needs an imported recording and timing")
        source = ws.get("media", clip.get("media_id"))
        if not source["audio_tracks"] or (layout != "podcast" and not source["video"]):
            raise StudioError("Every segment needs audio; video episodes also need video in every segment")
        track = clip.get("audio_track", 0)
        if type(track) is not int or not 0 <= track < source["audio_tracks"]:
            raise StudioError("Choose an existing segment audio track")
        start = finite(clip.get("start", 0), "segment start", 0, source["duration"])
        end = finite(clip.get("end", source["duration"]), "segment end", 0, source["duration"])
        if end-start < .25:
            raise StudioError("Every episode segment needs at least 0.25 seconds")
        duration += end-start
        clean.append({"media_id":source["id"], "sha256":source["sha256"], "name":source["name"],
                      "label":title(clip.get("label", source["name"]), 100), "start":start, "end":end,
                      "audio_track":track, "gain_db":finite(clip.get("gain_db", 0), "segment gain", -30, 6)})
    if duration > 3600:
        raise StudioError("Keep an episode within the one-hour local processing budget")
    captions = data.get("captions", "")
    if not isinstance(captions, str) or len(captions) > 200_000:
        raise StudioError("Episode captions must be under 200 KB")
    if captions:
        cues = parse_srt(captions)
        if cues[-1].end_ms > round(duration*1000):
            raise StudioError("Use final episode timestamps; caption timing exceeds the arranged episode")
        if data.get("captions_reviewed") is not True:
            raise StudioError("Correct and review the final episode captions")
    if data.get("content_reviewed") is not True:
        raise StudioError("Review each recording, participant permissions and the episode order first")
    return {"title":title(data.get("title")), "clips":clean, "format":layout, "duration":duration,
            "target_lufs":finite(data.get("target_lufs", -16), "target LUFS", -24, -14),
            "speech_cleanup":data.get("speech_cleanup") is True, "captions":captions,
            "content_reviewed":True, "captions_reviewed":data.get("captions_reviewed") is True}


def normalize_wav(source, destination, lufs):
    analysis = measure(source, seconds=None, channels=2, lufs=lufs)
    v = analysis["levels"]
    filt = (f"loudnorm=I={lufs}:TP=-1.5:LRA=11:linear=true:measured_I={v['input_i']}:measured_TP={v['input_tp']}:"
            f"measured_LRA={v['input_lra']}:measured_thresh={v['input_thresh']}:offset={v['target_offset']}")
    run_process([executable("ffmpeg"),"-nostdin","-v","error","-n","-protocol_whitelist","file,pipe","-i",str(source),
                 "-map","0:a:0","-af",filt,"-ar","48000","-ac","2","-c:a","pcm_s24le",str(destination)],3600)


def episode(ws, job_id, data):
    sources = [ws.get("media", c["media_id"]) for c in data["clips"]]
    for clip, source in zip(data["clips"], sources):
        if source["sha256"] != clip["sha256"]:
            raise StudioError("Segment provenance changed after review")
    checked_sources(ws, sources)
    ws.progress(job_id, "Episode sources verified", 1, 5)
    directory = ws.root/"exports"/job_id
    directory.mkdir(exist_ok=False)
    if shutil.disk_usage(directory).free < 200_000_000 + data["duration"]*1_800_000:
        raise StudioError("Not enough disk space for the episode and delivery package")
    video = data["format"] != "podcast"
    size = FORMATS[data["format"]]
    args = [executable("ffmpeg"),"-nostdin","-hide_banner","-n","-threads","2"]
    filters, labels, chapters = [], [], []
    cursor = 0
    for i, (clip, source) in enumerate(zip(data["clips"], sources)):
        args += ["-protocol_whitelist","file,pipe","-i",str(ws.media_path(source["id"]))]
        trim = f"start={clip['start']}:end={clip['end']}"
        if video:
            w,h = size
            filters.append(f"[{i}:{source['video_index']}]trim={trim},setpts=PTS-STARTPTS,scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                           f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x101216,setsar=1,fps=30[v{i}]")
            labels.append(f"[v{i}]")
        filters.append(f"[{i}:a:{clip['audio_track']}]atrim={trim},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={clip['gain_db']}dB[a{i}]")
        labels.append(f"[a{i}]")
        end = cursor+clip["end"]-clip["start"]
        chapters.append({"title":clip["label"], "start_ms":round(cursor*1000), "end_ms":round(end*1000), "source_id":source["id"]})
        cursor = end
    targets = ("[joinedv]" if video else "")+"[joineda]"
    filters.append("".join(labels)+f"concat=n={len(sources)}:v={int(video)}:a=1"+targets)
    audio = "joineda"
    if data["speech_cleanup"]:
        filters.append("[joineda]highpass=f=80,lowpass=f=16000,acompressor=threshold=0.125:ratio=2:attack=10:release=180[voice]")
        audio = "voice"
    visual = "joinedv"
    if data["captions"]:
        cues = parse_srt(data["captions"])
        (directory/"captions.srt").write_text(srt_text(cues),encoding="utf-8")
        if video:
            (directory/"captions.ass").write_text(ass_text(cues),encoding="utf-8")
            filters.append("[joinedv]ass=filename=captions.ass[captioned]")
            visual = "captioned"
    args += ["-filter_complex_threads","1","-filter_complex",";".join(filters)]
    if video:
        args += ["-map",f"[{visual}]","-an","-c:v","libx264","-preset","veryfast","-crf","21","-threads","2","-pix_fmt","yuv420p","-map_metadata","-1","picture.mp4"]
    args += ["-map",f"[{audio}]","-vn","-ar","48000","-ac","2","-c:a","pcm_f32le","-map_metadata","-1","assembled.wav"]
    ws.progress(job_id, "Assembling reviewed segments", 2, 5)
    run_process(args,3600,cwd=directory)
    ws.progress(job_id, "Measuring and finishing episode audio", 3, 5)
    normalize_wav(directory/"assembled.wav", directory/"podcast.wav", data["target_lufs"])
    audio_receipt = export_audio(directory/"podcast.wav", directory/"podcast.mp3",channels=2,lufs=data["target_lufs"])
    (directory/"audio-measurement.json").write_text(json.dumps(audio_receipt,indent=2),encoding="utf-8")
    (directory/"chapters.json").write_text(json.dumps(chapters,indent=2),encoding="utf-8")
    lines = [";FFMETADATA1"]
    for chapter in chapters:
        safe = chapter["title"].replace("\\","\\\\").replace("=","\\=").replace(";","\\;").replace("#","\\#")
        lines += ["[CHAPTER]","TIMEBASE=1/1000",f"START={chapter['start_ms']}",f"END={chapter['end_ms']}","title="+safe]
    (directory/"chapters.ffmeta").write_text("\n".join(lines)+"\n",encoding="utf-8")
    outputs = ["podcast.wav","podcast.mp3"]
    if video:
        run_process([executable("ffmpeg"),"-nostdin","-v","error","-n","-i","picture.mp4","-i","podcast.wav","-f","ffmetadata","-i","chapters.ffmeta",
                     "-map","0:v:0","-map","1:a:0","-map_metadata","2","-map_chapters","2","-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart","episode.mp4"],3600,cwd=directory)
        outputs.insert(0,"episode.mp4")
        (directory/"picture.mp4").unlink()
    (directory/"assembled.wav").unlink()
    ws.progress(job_id, "Verifying episode and companion files", 4, 5)
    result = complete(ws,job_id,data,sources,outputs,data["duration"],extras={"speech_cleanup_applied":data["speech_cleanup"],"chapters":chapters},
                      supplemental=["audio-measurement.json","chapters.json","chapters.ffmeta"])
    # Each output's dimensions are independently checked; audio has no video frame.
    if video and tuple((result["files"][0]["media"][k] for k in ("width","height"))) != size:
        raise StudioError("Episode dimensions do not match the reviewed format")
    ws.progress(job_id, "Episode delivery verified", 5, 5)
    return result


def stream_info(path):
    r = run_process([executable("ffprobe"),"-v","error","-protocol_whitelist","file,pipe","-show_streams","-of","json",str(path)],30)
    return json.loads(r.stdout)["streams"]


def prepare_edit_copy(ws, data):
    source = ws.get("media", data.get("media_id"))
    if not source["video"] or source["duration"] > 3600:
        raise StudioError("Choose a video recording within the one-hour remux budget")
    streams = stream_info(ws.media_path(source["id"]))
    video = next(s for s in streams if s["index"] == source["video_index"])
    audio = [s for s in streams if s["codec_type"] == "audio"]
    if video["codec_name"] not in {"h264","hevc","av1"} or any(s["codec_name"] not in {"aac","alac","mp3"} for s in audio):
        raise StudioError("This lossless MP4 path supports H.264/HEVC/AV1 with AAC/ALAC/MP3. Use an episode render for other codecs")
    if data.get("content_reviewed") is not True:
        raise StudioError("Review the selected recording before creating its editing copy")
    return {"media_id":source["id"],"name":source["name"],"sha256":source["sha256"],"video_index":source["video_index"],
            "duration":source["duration"],"video_codec":video["codec_name"],"audio_codecs":[s["codec_name"] for s in audio],"content_reviewed":True}


def packet_hashes(path, index=0):
    r = run_process([executable("ffmpeg"),"-nostdin","-v","error","-protocol_whitelist","file,pipe","-i",str(path),
                     "-map",f"0:{index}","-map","0:a?","-c","copy","-f","streamhash","-hash","sha256","-"],3600)
    return [line.strip() for line in r.stdout.splitlines() if line and not line.startswith("#")]


def edit_copy(ws, job_id, data):
    source = ws.get("media",data["media_id"])
    if source["sha256"] != data["sha256"]:
        raise StudioError("Recording provenance changed after review")
    checked_sources(ws,[source])
    original = ws.media_path(source["id"])
    directory = ws.root/"exports"/job_id
    directory.mkdir(exist_ok=False)
    if shutil.disk_usage(directory).free < source["bytes"]*2+100_000_000:
        raise StudioError("Not enough free space for the editing copy and delivery package")
    ws.progress(job_id,"Checking compressed stream hashes",1,4)
    before = packet_hashes(original,data["video_index"])
    run_process([executable("ffmpeg"),"-nostdin","-v","error","-n","-protocol_whitelist","file,pipe","-i",str(original),
                 "-map",f"0:{data['video_index']}","-map","0:a?","-c","copy","-map_metadata","-1","-map_chapters","-1","-movflags","+faststart","editing-copy.mp4"],3600,cwd=directory)
    ws.progress(job_id,"Editing copy written; comparing packets",2,4)
    after = packet_hashes(directory/"editing-copy.mp4")
    if before != after:
        raise StudioError("Compressed stream verification differs; this copy is not marked verified")
    ws.progress(job_id,"Compressed streams preserved; decoding output",3,4)
    return complete(ws,job_id,data,[source],["editing-copy.mp4"],data["duration"],
                    extras={"transcoded":False,"compressed_stream_hashes_match":True,"audio_tracks_preserved":len(data["audio_codecs"]),"discarded":"subtitles, data, chapters and source metadata"})
