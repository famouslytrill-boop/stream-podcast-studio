"""Real, bounded FFmpeg sequence and bumper exports, with decode receipts."""
from __future__ import annotations
import array
import json
import math
from pathlib import Path
import shutil
import sys
import wave

from hub.core import FORMATS, canonical, digest, probe_media
from tools.captions import Cue, ass_text, parse_srt, rebase_cues, srt_text
from tools.studio_tools import StudioError, executable, export_audio, run_process


def finish(workspace, job_id, outputs, source_hash=None, expected_duration=None, expected_size=None):
    directory = workspace.root / "exports" / job_id
    files = []
    for name in outputs:
        file = directory / name
        info = probe_media(file)
        run_process([executable("ffmpeg"), "-nostdin", "-v", "error", "-xerror", "-protocol_whitelist", "file,pipe",
                     "-i", str(file), "-map", "0:v?", "-map", "0:a?", "-f", "null", "-"], 3600)
        if expected_duration is not None and abs(info["duration"] - expected_duration) > .25:
            raise StudioError("Export duration did not match the reviewed sequence")
        if expected_size and (info["width"], info["height"]) != expected_size:
            raise StudioError("Export frame size did not match the reviewed format")
        files.append({"name": name, "bytes": file.stat().st_size, "sha256": digest(file),
                      "media": info, "full_decode_verified": True})
    receipt = {"job_id": job_id, "files": files, "source_sha256": source_hash,
               "source_preserved": bool(source_hash), "published": False,
               "picture_and_listening_review": "required", "rights": "owner_confirmation_only",
               "worker_execution": "local_ffmpeg_executed", "malware_scan": "not_performed"}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return {**receipt, "downloads": outputs + ["receipt.json"] + (["captions.srt"] if (directory / "captions.srt").exists() else [])}


def render_sequence(workspace, job_id, params):
    session = params["session"]
    source = workspace.media_path(session["media_id"])
    if digest(source) != params["source_sha256"]:
        raise StudioError("Source checksum changed. Import and review the intended recording again")
    media = workspace.get("media", session["media_id"])
    directory = workspace.root / "exports" / job_id
    directory.mkdir(exist_ok=False)
    total = sum(c["end"] - c["start"] for c in session["cuts"])
    if shutil.disk_usage(directory).free < 200_000_000 + total * 1_500_000:
        raise StudioError("Not enough free disk space for this export budget")
    audio_only = session["format"] == "podcast"
    width, height = FORMATS[session["format"]] or (0, 0)
    audio = media["audio_tracks"] > 0
    filters, labels = [], []
    for i, cut in enumerate(session["cuts"]):
        trim = f"start={cut['start']}:end={cut['end']}"
        if not audio_only:
            filters.append(f"[0:{media['video_index']}]trim={trim},setpts=PTS-STARTPTS,"
                           f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                           f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x101216,setsar=1,fps=30[v{i}]")
            labels.append(f"[v{i}]")
        if audio:
            filters.append(f"[0:a:{session['audio_track']}]atrim={trim},asetpts=PTS-STARTPTS,"
                           f"aresample=48000,aformat=channel_layouts=stereo[a{i}]")
            labels.append(f"[a{i}]")
    target = "[outa]" if audio_only else "[outv]" + ("[outa]" if audio else "")
    filters.append("".join(labels) + f"concat=n={len(session['cuts'])}:v={0 if audio_only else 1}:a={1 if audio else 0}" + target)
    video_target = "outv"
    cues = []
    if session["captions"]:
        cursor = 0
        source_cues = parse_srt(session["captions"])
        for cut in session["cuts"]:
            cues += [Cue(c.start_ms + cursor, c.end_ms + cursor, c.text) for c in rebase_cues(source_cues, cut["start"], cut["end"])]
            cursor += round((cut["end"] - cut["start"]) * 1000)
        if not cues:
            raise StudioError("No captions overlap the selected sequence")
        (directory / "captions.srt").write_text(srt_text(cues), encoding="utf-8")
        if not audio_only:
            # Existing tested plain-text ASS writer; no client filter strings are accepted.
            (directory / "captions.ass").write_text(ass_text(cues), encoding="utf-8")
            filters.append("[outv]ass=filename=captions.ass[captioned]")
            video_target = "captioned"
    if session["fade"] and not audio_only:
        fade = min(.15, total / 4)
        filters.append(f"[{video_target}]fade=t=in:st=0:d={fade},fade=t=out:st={total-fade}:d={fade}[faded]")
        video_target = "faded"
    args = [executable("ffmpeg"), "-nostdin", "-hide_banner", "-n", "-threads", "2", "-protocol_whitelist", "file,pipe",
            "-i", str(source), "-filter_complex_threads", "1", "-filter_complex", ";".join(filters)]
    if audio_only:
        args += ["-map", "[outa]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", "sequence.wav"]
        run_process(args, 3600, cwd=directory)
        audio_receipt = export_audio(directory / "sequence.wav", directory / "final.mp3")
        (directory / "audio-measurement.json").write_text(json.dumps(audio_receipt, indent=2), encoding="utf-8")
        (directory / "sequence.wav").unlink()
        output = "final.mp3"
    else:
        args += ["-map", f"[{video_target}]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-threads", "2", "-pix_fmt", "yuv420p"]
        if audio:
            args += ["-map", "[outa]", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]
        args += ["-sn", "-dn", "-map_metadata", "-1", "-map_chapters", "-1", "-movflags", "+faststart", "final.mp4"]
        run_process(args, 3600, cwd=directory)
        output = "final.mp4"
    if digest(source) != params["source_sha256"]:
        raise StudioError("Source changed during the export; review a fresh import")
    (directory / "session.json").write_text(json.dumps(session, indent=2), encoding="utf-8")
    return finish(workspace, job_id, [output], params["source_sha256"], total, None if audio_only else (width, height))


def stinger(path):
    rate = 48000
    samples = array.array("h")
    notes = [(0, .28, 329.6276), (.22, .30, 391.9954), (.45, .65, 493.8833)]
    for i in range(int(rate * 1.4)):
        t, value = i / rate, 0
        for start, duration, frequency in notes:
            u = t - start
            if 0 <= u < duration:
                envelope = min(1, u / .01) * (1 - u / duration) ** 2
                value += .16 * envelope * math.sin(2 * math.pi * frequency * u)
        samples.append(round(max(-.8, min(.8, value)) * 32767))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate); out.writeframes(samples.tobytes())


def render_bumper(workspace, job_id, params):
    directory = workspace.root / "exports" / job_id
    directory.mkdir(exist_ok=False)
    stinger(directory / "original-stinger.wav")
    (directory / "title.txt").write_text(params["title"], encoding="utf-8")
    bg, accent = {"ember": ("101216", "FF6A3D"), "hearth": ("15171B", "FFB076"), "vellum": ("151321", "B5A0F7")}[params["theme"]]
    font = next((p for p in [Path("C:/Windows/Fonts/segoeui.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if p.exists()), None)
    if not font:
        raise StudioError("No supported local title font found")
    shutil.copyfile(font, directory / "font.ttf")
    filters = (f"drawbox=x=100:y=225:w=80:h=5:color=0x{accent}:t=fill,"
               f"drawtext=fontfile=font.ttf:textfile=title.txt:expansion=none:fontsize=58:fontcolor=0xF4F1E8:x=100:y=270,"
               "fade=t=in:d=0.25,fade=t=out:st=3.65:d=0.35")
    run_process([executable("ffmpeg"), "-nostdin", "-hide_banner", "-n", "-f", "lavfi", "-i", f"color=c=0x{bg}:s=1280x720:r=30:d=4",
                 "-i", "original-stinger.wav", "-filter_threads", "1", "-vf", filters, "-af", "apad", "-t", "4",
                 "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-threads", "2",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-b:a", "160k", "-movflags", "+faststart", "bumper.mp4"], 120, cwd=directory)
    (directory / "font.ttf").unlink()
    return finish(workspace, job_id, ["bumper.mp4", "original-stinger.wav"])
