#!/usr/bin/env python3
"""Review and render up to three local clips. Never records, uploads or publishes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

try:
    from .studio_tools import StudioError, executable, finite, local_media, read_json, run_process
except ImportError:
    from studio_tools import StudioError, executable, finite, local_media, read_json, run_process

VERSION = "0.2.0"
RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])$", re.I)


def video_probe(path: Path) -> dict:
    result = run_process([
        executable("ffprobe"), "-v", "error", "-protocol_whitelist", "file,pipe",
        "-show_format", "-show_streams", "-of", "json", "-i", str(path),
    ], 30)
    data = json.loads(result.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    audio = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if video is None or not audio:
        raise StudioError("A recording with video and at least one audio stream is required")
    return {
        "duration_seconds": finite(data.get("format", {}).get("duration"), "duration", 0.25),
        "width": video["width"], "height": video["height"], "video_stream_index": video["index"],
        "sample_aspect_ratio": video.get("sample_aspect_ratio", "1:1"),
        "audio_stream_count": len(audio),
        "audio_channels": [s.get("channels") for s in audio],
    }


def validate_clips(data: dict, media: dict) -> list[dict]:
    clips = data.get("clips") if isinstance(data, dict) else None
    if not isinstance(clips, list) or not 1 <= len(clips) <= 3:
        raise StudioError("Choose one to three clips per manifest")
    validated, ids = [], set()
    for item in clips:
        if not isinstance(item, dict):
            raise StudioError("Each clip must be an object")
        clip_id = item.get("id")
        if not isinstance(clip_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", clip_id):
            raise StudioError("Clip id needs 1-48 lowercase letters, digits, underscores or hyphens")
        if RESERVED.fullmatch(clip_id) or clip_id in ids:
            raise StudioError("Clip ids must be unique and safe on Windows")
        ids.add(clip_id)
        start = finite(item.get("in_seconds"), "in_seconds", 0)
        end = finite(item.get("out_seconds"), "out_seconds", 0)
        if not 0.25 <= end - start <= 180 or end > media["duration_seconds"]:
            raise StudioError("Each cut must be 0.25-180 seconds and inside the recording")
        stream = item.get("audio_stream", 0)
        if type(stream) is not int or not 0 <= stream < media["audio_stream_count"]:
            raise StudioError("audio_stream must identify an existing zero-based audio stream")
        layout = item.get("layout", "fit")
        if layout not in {"fit", "center-crop"}:
            raise StudioError("Choose fit or center-crop layout")
        title = item.get("title", "")
        if not isinstance(title, str) or not title.strip() or len(title) > 150:
            raise StudioError("Each clip needs a descriptive title of 1-150 characters")
        pending = [k for k in ("context_reviewed", "rights_reviewed") if item.get(k) is not True]
        validated.append({
            "id": clip_id, "in_seconds": start, "out_seconds": end,
            "duration_seconds": end - start, "audio_stream": stream,
            "layout": layout, "title": title.strip(), "review_pending": pending,
        })
    return validated


def prepare(manifest) -> tuple[Path, dict, list[dict]]:
    manifest_path = Path(manifest).expanduser().resolve(strict=True)
    data = read_json(manifest_path)
    source = data.get("source") if isinstance(data, dict) else None
    if not isinstance(source, str) or not source.strip() or "://" in source or source.startswith(("\\\\", "//")):
        raise StudioError("source must be a local recording path, relative to the manifest or absolute")
    path = Path(source).expanduser()
    path = local_media(path if path.is_absolute() else manifest_path.parent / path)
    media = video_probe(path)
    if media["sample_aspect_ratio"] not in ("1:1", "0:1", "N/A", None):
        raise StudioError("Convert this source to square pixels before making vertical clips")
    return path, media, validate_clips(data, media)


def render(manifest, output) -> dict:
    source, media, clips = prepare(manifest)
    if any(c["review_pending"] for c in clips):
        raise StudioError("Review actual cut context and rights, then set those confirmations true")
    destination = Path(output).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise StudioError("Output folder already exists; choose a new folder")
    destination.parent.mkdir(parents=True, exist_ok=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix=".ember-clips-", dir=destination.parent) as tmp:
        staging = Path(tmp)
        for clip in clips:
            stage = staging / (clip["id"] + ".mp4")
            if clip["layout"] == "fit":
                filters = ("scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                           "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x101216")
            else:
                filters = "scale=1080:1920:force_original_aspect_ratio=increase:force_divisible_by=2,crop=1080:1920"
            run_process([
                executable("ffmpeg"), "-nostdin", "-hide_banner", "-n", "-threads", "2",
                "-protocol_whitelist", "file,pipe", "-ss", str(clip["in_seconds"]),
                "-i", str(source), "-t", str(clip["duration_seconds"]),
                "-map", f"0:{media['video_stream_index']}", "-map", f"0:a:{clip['audio_stream']}", "-sn", "-dn",
                "-map_metadata", "-1", "-map_chapters", "-1",
                "-vf", filters + ",setsar=1,fps=30", "-filter_threads", "1",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-threads", "2",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                "-movflags", "+faststart", str(stage),
            ], 600)
            actual = video_probe(stage)
            if (actual["width"], actual["height"]) != (1080, 1920):
                raise StudioError("Encoded clip dimensions failed verification")
            if abs(actual["duration_seconds"] - clip["duration_seconds"]) > 0.25:
                raise StudioError("Encoded clip duration failed verification")
            # Decode the full cut to catch corruption; probing alone is insufficient.
            run_process([executable("ffmpeg"), "-nostdin", "-v", "error", "-xerror",
                         "-protocol_whitelist", "file,pipe", "-i", str(stage),
                         "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"], 600)
            checks.append({**clip, "file": stage.name, "encoded": actual, "decode_verified": True})
        result = {
            "tool_version": VERSION, "clips": checks, "published": False,
            "recording_modified": False, "listening_and_picture_review": "required",
            "captions": "not_generated; add corrected captions in your editor",
            "audio": "one explicitly selected stream; no automatic track mix or loudness normalization",
        }
        (staging / "clip-report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        # Exclusive directory and file creation preserve existing outputs on both Windows and Unix.
        destination.mkdir(exist_ok=False)
        for file in staging.iterdir():
            with file.open("rb") as src, (destination / file.name).open("xb") as dst:
                shutil.copyfileobj(src, dst)
    return {"output_folder": str(destination), **result}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "render"):
        child = sub.add_parser(command)
        child.add_argument("manifest")
        if command == "render":
            child.add_argument("output", help="New folder for reviewed local outputs")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            _, media, clips = prepare(args.manifest)
            result = {"media": media, "clips": clips, "rendered": False, "published": False}
        else:
            result = render(args.manifest, args.output)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (StudioError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"Clip preparation stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
