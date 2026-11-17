"""Deterministic stem mixing and artwork/footage-to-music-video workflows."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import zipfile

from hub.core import FORMATS, digest
from hub.projects import title
from hub.render import finish
from tools.studio_tools import StudioError, executable, finite, measure, export_audio, run_process


def asset(ws, key, *, audio=False, visual=False):
    meta = ws.get("media", key)
    if audio and not meta["audio_tracks"]:
        raise StudioError("Choose a source with an actual audio track")
    if visual and not (meta.get("image") or meta["video"]):
        raise StudioError("Choose imported artwork or video footage")
    return meta


def prepare_mix(ws, data):
    tracks = data.get("tracks")
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= 8:
        raise StudioError("Choose one to eight audio stems")
    clean, duration = [], 0
    for track in tracks:
        if not isinstance(track, dict):
            raise StudioError("Each stem needs a source and settings")
        meta = asset(ws, track.get("media_id"), audio=True)
        start = finite(track.get("start", 0), "trim start", 0, meta["duration"])
        end = finite(track.get("end", meta["duration"]), "trim end", 0, meta["duration"])
        offset = finite(track.get("offset", 0), "offset seconds", 0, 3600)
        if end-start < .25:
            raise StudioError("Each stem needs at least 0.25 seconds")
        audio_track = track.get("audio_track", 0)
        if type(audio_track) is not int or not 0 <= audio_track < meta["audio_tracks"]:
            raise StudioError("Choose an existing source audio track")
        clean.append({"media_id": meta["id"], "sha256": meta["sha256"], "name": meta["name"],
                      "start": start, "end": end, "offset": offset, "audio_track": audio_track,
                      "gain_db": finite(track.get("gain_db", 0), "gain dB", -60, 6),
                      "pan": finite(track.get("pan", 0), "stereo balance", -1, 1)})
        duration = max(duration, offset + end-start)
    if duration > 3600:
        raise StudioError("Keep this music mix within the one-hour processing budget")
    if data.get("rights_reviewed") is not True:
        raise StudioError("Review the actual stems and their permissions before mixing")
    return {"title": title(data.get("title")), "tracks": clean, "duration": duration,
            "target_lufs": finite(data.get("target_lufs", -14), "target LUFS", -24, -14),
            "rights_reviewed": True, "quality": "deterministic level/balance mix; listening review remains required"}


def prepare_video(ws, data):
    sound = asset(ws, data.get("audio_id"), audio=True)
    visual = asset(ws, data.get("visual_id"), visual=True)
    start = finite(data.get("start", 0), "audio start", 0, sound["duration"])
    end = finite(data.get("end", sound["duration"]), "audio end", 0, sound["duration"])
    duration = end-start
    if not .25 <= duration <= 600:
        raise StudioError("Music-video preview length must be 0.25–600 seconds")
    layout = data.get("format", "landscape")
    if layout not in {"landscape", "vertical"}:
        raise StudioError("Choose landscape or vertical video")
    loop = data.get("loop_visual") is True
    if not visual.get("image") and visual["duration"] + .01 < duration and not loop:
        raise StudioError("Footage is shorter than the song cut. Explicitly allow looping or shorten the cut")
    foreground = None
    if data.get("foreground_id"):
        foreground = asset(ws, data["foreground_id"], visual=True)
        if not foreground["video"]:
            raise StudioError("Green-screen foreground needs a video clip")
        if foreground["duration"] + .01 < duration and not loop:
            raise StudioError("Foreground is too short; approve looping or shorten the cut")
    if data.get("rights_reviewed") is not True:
        raise StudioError("Review the song, footage/artwork and participant permissions first")
    return {"title": title(data.get("title"), 60), "audio": sound, "visual": visual, "foreground": foreground,
            "start": start, "end": end, "duration": duration, "format": layout, "loop_visual": loop,
            "waveform": data.get("waveform") is not False, "motion": data.get("motion") is True,
            "key_color": "0000FF" if data.get("key_color") == "blue" else "00FF00",
            "similarity": finite(data.get("similarity", .15), "chroma similarity", .01, .5),
            "blend": finite(data.get("blend", .08), "chroma blend", 0, .5), "rights_reviewed": True}


def checked_sources(ws, sources):
    for source in sources:
        if digest(ws.media_path(source["id"])) != source["sha256"]:
            raise StudioError("A source checksum changed; re-import and review that source")


def complete(ws, job_id, data, sources, outputs, duration, dimensions=None, extras=None, supplemental=None):
    checked_sources(ws, sources)
    result = finish(ws, job_id, outputs, expected_duration=duration, expected_size=dimensions)
    checked_sources(ws, sources)
    result.update(source_preserved=True, sources=[{"id": s["id"], "sha256": s["sha256"]} for s in sources],
                  workflow="deterministic", **(extras or {}))
    directory = ws.root / "exports" / job_id
    (directory / "recipe.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    result["downloads"].append("recipe.json")
    result["downloads"] += supplemental or []
    (directory / "receipt.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if sum((directory/name).stat().st_size for name in result["downloads"]) < 500_000_000:
        with zipfile.ZipFile(directory/"delivery.zip", "x", zipfile.ZIP_DEFLATED, strict_timestamps=False) as package:
            for name in result["downloads"]:
                package.write(directory/name, name)
        result["downloads"].append("delivery.zip")
    ws.progress(job_id, "Verified delivery", 4, 4)
    return result


def mix(ws, job_id, data):
    sources = [ws.get("media", track["media_id"]) for track in data["tracks"]]
    checked_sources(ws, sources)
    ws.progress(job_id, "Sources verified", 1, 4)
    directory = ws.root / "exports" / job_id
    directory.mkdir(exist_ok=False)
    if shutil.disk_usage(directory).free < data["duration"] * 48_000 * 2 * 12 + 200_000_000:
        raise StudioError("Not enough free disk space for the mix and verified outputs")
    args = [executable("ffmpeg"), "-nostdin", "-hide_banner", "-n", "-threads", "2"]
    filters, inputs = [], []
    for i, track in enumerate(data["tracks"]):
        args += ["-protocol_whitelist", "file,pipe", "-i", str(ws.media_path(track["media_id"]))]
        left, right = 1-max(0, track["pan"]), 1+min(0, track["pan"])
        filters.append(f"[{i}:a:{track['audio_track']}]atrim=start={track['start']}:end={track['end']},asetpts=PTS-STARTPTS,"
                       f"aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={track['gain_db']}dB,"
                       f"pan=stereo|c0={left}*c0|c1={right}*c1,adelay={round(track['offset']*1000)}:all=1[t{i}]")
        inputs.append(f"[t{i}]")
    filters.append("".join(inputs) + f"amix=inputs={len(inputs)}:duration=longest:normalize=0[mix]")
    args += ["-filter_complex_threads", "1", "-filter_complex", ";".join(filters), "-map", "[mix]", "-ar", "48000", "-ac", "2",
             "-c:a", "pcm_f32le", "-map_metadata", "-1", "mix-float.wav"]
    run_process(args, 3600, cwd=directory)
    ws.progress(job_id, "Stems mixed; measuring loudness", 2, 4)
    measured = measure(directory/"mix-float.wav", seconds=None, channels=2, lufs=data["target_lufs"])
    levels = measured["levels"]
    normalization = (f"loudnorm=I={data['target_lufs']}:TP=-1.5:LRA=11:linear=true:"
                     f"measured_I={levels['input_i']}:measured_TP={levels['input_tp']}:measured_LRA={levels['input_lra']}:"
                     f"measured_thresh={levels['input_thresh']}:offset={levels['target_offset']}")
    run_process([executable("ffmpeg"), "-nostdin", "-hide_banner", "-n", "-protocol_whitelist", "file,pipe", "-i", "mix-float.wav",
                 "-map", "0:a:0", "-af", normalization, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", "mix.wav"], 3600, cwd=directory)
    quality = export_audio(directory/"mix.wav", directory/"mix.mp3", channels=2, lufs=data["target_lufs"])
    (directory/"loudness.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    ws.progress(job_id, "WAV and MP3 rendered; decoding outputs", 3, 4)
    result = complete(ws, job_id, data, sources, ["mix.wav", "mix.mp3"], data["duration"],
                      extras={"target_lufs": data["target_lufs"], "stereo_balance": "linear left/right balance; not spatial mixing"}, supplemental=["loudness.json"])
    return result


def music_video(ws, job_id, data):
    sources = [data["audio"], data["visual"]] + ([data["foreground"]] if data["foreground"] else [])
    checked_sources(ws, sources)
    ws.progress(job_id, "Song and visual sources verified", 1, 4)
    directory = ws.root / "exports" / job_id
    directory.mkdir(exist_ok=False)
    width, height = FORMATS[data["format"]]
    args = [executable("ffmpeg"), "-nostdin", "-hide_banner", "-n", "-threads", "2"]
    if data["visual"].get("image"):
        args += ["-loop", "1", "-framerate", "30"]
    elif data["loop_visual"]:
        args += ["-stream_loop", "-1"]
    args += ["-protocol_whitelist", "file,pipe", "-i", str(ws.media_path(data["visual"]["id"])),
             "-protocol_whitelist", "file,pipe", "-i", str(ws.media_path(data["audio"]["id"]))]
    base = (f"[0:v:0]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=30")
    if data["motion"] and data["visual"].get("image"):
        base += f",zoompan=z='min(pzoom+0.0002,1.04)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={width}x{height}:fps=30"
    filters, current = [base + "[base]"], "base"
    if data["foreground"]:
        if data["loop_visual"]:
            args += ["-stream_loop", "-1"]
        args += ["-protocol_whitelist", "file,pipe", "-i", str(ws.media_path(data["foreground"]["id"]))]
        filters.append(f"[2:v:0]scale={width}:{height}:force_original_aspect_ratio=decrease,format=rgba,"
                       f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x00000000,setsar=1,fps=30,"
                       f"chromakey=0x{data['key_color']}:{data['similarity']}:{data['blend']},format=rgba[foreground]")
        filters.append("[base][foreground]overlay=shortest=1[keyed]")
        current = "keyed"
    sound = f"[1:a:0]atrim=start={data['start']}:end={data['end']},asetpts=PTS-STARTPTS,aresample=48000"
    if data["waveform"]:
        filters.append(sound + ",asplit=2[song][waveaudio]")
        wave_height = 90 if data["format"] == "landscape" else 130
        filters.append(f"[waveaudio]showwaves=s={width-160}x{wave_height}:mode=line:colors=0x8EF2CE:rate=30,format=rgba[wave]")
        filters.append(f"[{current}][wave]overlay=x=80:y=H-h-70:shortest=1[withwave]")
        current = "withwave"
    else:
        filters.append(sound + "[song]")
    font = next((p for p in (Path("C:/Windows/Fonts/segoeui.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")) if p.exists()), None)
    if not font:
        raise StudioError("A supported local title font is required")
    shutil.copyfile(font, directory/"font.ttf")
    (directory/"title.txt").write_text(data["title"], encoding="utf-8")
    filters.append(f"[{current}]drawtext=fontfile=font.ttf:textfile=title.txt:expansion=none:fontsize=42:"
                   "fontcolor=0xF4F1E8:box=1:boxcolor=0x101216@0.8:boxborderw=16:x=80:y=70,"
                   "fade=t=in:d=0.2[final]")
    args += ["-filter_complex_threads", "1", "-filter_complex", ";".join(filters), "-map", "[final]", "-map", "[song]",
             "-t", str(data["duration"]), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-threads", "2",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-map_metadata", "-1", "-movflags", "+faststart", "music-video.mp4"]
    ws.progress(job_id, "Rendering song and visual composition", 2, 4)
    run_process(args, 3600, cwd=directory)
    (directory/"font.ttf").unlink()
    ws.progress(job_id, "Render finished; verifying full decode", 3, 4)
    return complete(ws, job_id, data, sources, ["music-video.mp4"], data["duration"], (width, height),
                    {"green_screen_applied": data["foreground"] is not None, "waveform_from_actual_audio": data["waveform"]})
