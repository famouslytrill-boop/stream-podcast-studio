#!/usr/bin/env python3
"""Local production checks; no streaming, publishing, uploads, or shell execution."""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlsplit
import ipaddress
import xml.etree.ElementTree as ET

VERSION = "0.1.0"
ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM = "http://www.w3.org/2005/Atom"
CONFIRMATIONS = (
    "channel_confirmed", "audio_clean", "no_duplicate_audio", "guest_consent",
    "brb_silent", "recording_reviewed", "obs_stats_checked", "rights_checked",
)
OBS_REQUESTS = ("GetVersion", "GetStats", "GetStreamStatus", "GetRecordStatus")
MEDIA_SUFFIXES = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".mp4", ".mkv", ".mov", ".webm"}


class StudioError(ValueError):
    """An actionable production check failure."""


def finite(value, label: str, minimum=None, maximum=None) -> float:
    if isinstance(value, bool):
        raise StudioError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise StudioError(f"{label} must be a finite number") from None
    if not math.isfinite(result):
        raise StudioError(f"{label} must be a finite number")
    if minimum is not None and result < minimum:
        raise StudioError(f"{label} must be at least {minimum}")
    if maximum is not None and result > maximum:
        raise StudioError(f"{label} must be no more than {maximum}")
    return result


def positive_int(value, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise StudioError(f"{label} must be a positive integer")
    return value


def text_value(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StudioError(f"{label} must be nonempty text")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in value):
        raise StudioError(f"{label} contains a control character")
    return value.strip()


def read_json(path) -> object:
    p = Path(path)
    if p.stat().st_size > 2_000_000:
        raise StudioError("Configuration exceeds 2 MB")
    return json.loads(p.read_text(encoding="utf-8"))


def write_new(path, data: str | bytes):
    """Exclusive creation: never replace an existing file, including a symlink."""
    p = Path(path).absolute()
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "xb" if isinstance(data, bytes) else "x"
    kwargs = {} if isinstance(data, bytes) else {"encoding": "utf-8"}
    with p.open(mode, **kwargs) as output:
        output.write(data)
    return str(p)


def doctor() -> dict:
    binaries = {}
    for label, candidates in {
        "ffmpeg": ["ffmpeg"], "ffprobe": ["ffprobe"],
        "obs": ["obs64", "obs", "obs-studio"], "audacity": ["audacity"],
        "git": ["git"],
    }.items():
        found = next((shutil.which(c) for c in candidates if shutil.which(c)), None)
        if not found and platform.system() == "Windows":
            relative = {"obs": "obs-studio/bin/64bit/obs64.exe", "audacity": "Audacity/Audacity.exe"}.get(label)
            if relative:
                for env in ("ProgramFiles", "ProgramFiles(x86)"):
                    candidate = Path(os.environ.get(env, "")) / relative
                    if candidate.is_file():
                        found = str(candidate)
                        break
        binaries[label] = {"found": bool(found), "path": found}
    try:
        websocket_version = importlib.metadata.version("websockets")
    except importlib.metadata.PackageNotFoundError:
        websocket_version = None
    return {
        "tool_version": VERSION, "environment": "the computer executing this command",
        "os": platform.system(), "python": platform.python_version(),
        "free_disk_gib": round(shutil.disk_usage(Path.cwd()).free / 1024**3, 1),
        "binaries": binaries, "obs_client_version": websocket_version,
        "hardware_audio_video_and_upload": "not_tested", "stream_started": False,
        "note": "PATH detection may miss GUI apps; this is not a hardware or live-stream acceptance test.",
    }


def preflight(profile: dict) -> dict:
    if not isinstance(profile, dict):
        raise StudioError("Profile must be an object")
    blocked, unverified = [], []
    video = finite(profile.get("video_kbps"), "video_kbps", 500, 100000)
    audio = finite(profile.get("audio_kbps"), "audio_kbps", 32, 512)
    minimum = round((video + audio) / 1000 * 1.5, 3)
    uplink = profile.get("measured_upload_mbps")
    if uplink is None:
        unverified.append("measured_upload_mbps")
    elif finite(uplink, "measured_upload_mbps", 0) < minimum:
        blocked.append(f"upload below {minimum} Mbps working headroom target")
    confirmations = profile.get("operator_confirmations", {})
    if not isinstance(confirmations, dict):
        raise StudioError("operator_confirmations must be an object")
    for key in CONFIRMATIONS:
        value = confirmations.get(key)
        if value is False:
            blocked.append(key)
        elif value is not True:
            unverified.append(key)
    return {
        "status": "READY_FOR_MANUAL_TEST" if not blocked and not unverified else "NOT_READY",
        "blocked": blocked, "unverified": unverified,
        "working_upload_target_mbps": minimum,
        "basis": "1.5 times combined video and audio bitrate; a planning margin, not a platform requirement",
        "evidence": "operator confirmations plus supplied upload measurement; no hardware was probed",
        "stream_started": False,
    }


def plan(kind: str, minutes: int, topic: str) -> str:
    if kind not in {"stream", "podcast"}:
        raise StudioError("kind must be stream or podcast")
    if type(minutes) is not int or not 15 <= minutes <= 240:
        raise StudioError("minutes must be an integer from 15 to 240")
    topic = text_value(topic, "topic")
    if kind == "stream":
        segments = [("Welcome + tonight's challenge", 5), ("Gameplay + chat between rounds", minutes - 12),
                    ("Best moment + final round", 5), ("Next confirmed session + close", 2)]
    else:
        segments = [("Hook + specific question", 2), ("Context + fact check", 4),
                    ("Main conversation + concrete stories", minutes - 10),
                    ("Listener takeaway", 3), ("One invitation + close", 1)]
    lines = [f"# EmberBanter {kind} plan", "", f"Topic: {topic}",
             f"Length: {minutes} minutes. Suggested rundown; not a published schedule.", "",
             "| Minutes | Segment |", "| --- | --- |"]
    cursor = 0
    for title, length in segments:
        lines.append(f"| {cursor}-{cursor + length} | {title} |")
        cursor += length
    lines += ["", "Before recording: headphones, private notifications hidden, guest recording consent, rights check,",
              "short test recording reviewed, and one useful question for viewers.", "",
              "After recording: mark real clip timestamps; correct transcript names; review before publishing.", ""]
    return "\n".join(lines)


def local_media(path) -> Path:
    p = Path(path).expanduser().resolve(strict=True)
    if not p.is_file() or p.suffix.lower() not in MEDIA_SUFFIXES:
        raise StudioError("Choose a local media file; playlists and network URLs are not supported")
    return p


def executable(name: str) -> str:
    result = shutil.which(name)
    if not result:
        raise StudioError(f"{name} is not installed or is absent from PATH")
    return result


def run_process(args: list[str], timeout: float = 300) -> subprocess.CompletedProcess:
    result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout, shell=False)
    if result.returncode:
        # FFmpeg may include sensitive metadata or URLs in its logs. Do not echo it.
        raise StudioError(f"{Path(args[0]).name} failed (exit {result.returncode}); inspect the media locally")
    return result


def probe(path) -> dict:
    p = local_media(path)
    result = run_process([executable("ffprobe"), "-v", "error", "-protocol_whitelist", "file,pipe",
                          "-show_format", "-show_streams", "-of", "json", "-i", str(p)], 30)
    payload = json.loads(result.stdout)
    audio = next((s for s in payload.get("streams", []) if s.get("codec_type") == "audio"), None)
    if audio is None:
        raise StudioError("No audio stream found")
    duration = finite(payload.get("format", {}).get("duration", audio.get("duration")), "media duration", 0.001)
    return {"duration_seconds": duration, "channels": audio.get("channels"),
            "sample_rate": audio.get("sample_rate"), "codec": audio.get("codec_name")}


def loudness_stats(stderr: str) -> dict:
    for candidate in reversed(re.findall(r"\{[^{}]*\}", stderr, re.S)):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if "input_i" in data:
            return {key: finite(data.get(key), key) for key in
                    ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    raise StudioError("No finite loudness measurement; the input may be silent or too short")


def measure(path, seconds: float | None = 600, channels: int | None = None, lufs: float = -16) -> dict:
    p = local_media(path)
    info = probe(p)
    lufs = finite(lufs, "target_lufs", -24, -14)
    args = [executable("ffmpeg"), "-nostdin", "-hide_banner", "-protocol_whitelist", "file,pipe", "-i", str(p)]
    if seconds is not None:
        seconds = finite(seconds, "seconds", 3, 86400)
        args += ["-t", str(seconds)]
    filters = []
    if channels is not None:
        if channels not in (1, 2):
            raise StudioError("channels must be 1 or 2")
        filters.append(f"aformat=channel_layouts={'mono' if channels == 1 else 'stereo'}")
    filters.append(f"loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json")
    args += ["-map", "0:a:0", "-vn", "-af", ",".join(filters), "-f", "null", "-"]
    measured_seconds = min(info["duration_seconds"], seconds) if seconds else info["duration_seconds"]
    result = run_process(args, max(60, min(3600, info["duration_seconds"] * 2 + 30)))
    return {"media": info, "measured_seconds": round(measured_seconds, 3),
            "full_file": seconds is None or seconds >= info["duration_seconds"],
            "levels": loudness_stats(result.stderr), "target_lufs": lufs,
            "scope": "first audio stream; human listening, sync and clipping review remain necessary"}


def export_audio(path, output, channels: int = 2, lufs: float = -16) -> dict:
    p = local_media(path)
    destination = Path(output).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise StudioError("Output already exists; choose a new filename")
    if destination.suffix.lower() != ".mp3":
        raise StudioError("Podcast export requires a .mp3 output filename")
    lufs = finite(lufs, "lufs", -24, -14)
    measurements = measure(p, seconds=None, channels=channels, lufs=lufs)
    levels = measurements["levels"]
    channel_filter = f"aformat=channel_layouts={'mono' if channels == 1 else 'stereo'}"
    normalized = (f"loudnorm=I={lufs}:TP=-1.5:LRA=11:linear=true:"
                  f"measured_I={levels['input_i']}:measured_TP={levels['input_tp']}:"
                  f"measured_LRA={levels['input_lra']}:measured_thresh={levels['input_thresh']}:"
                  f"offset={levels['target_offset']}:print_format=json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Isolate temporary work; verify encoded audio before exclusively creating the final file.
    with tempfile.TemporaryDirectory(prefix=".emberbanter-", dir=destination.parent) as tmp:
        stage = Path(tmp) / "podcast.mp3"
        run_process([executable("ffmpeg"), "-nostdin", "-hide_banner", "-n", "-protocol_whitelist", "file,pipe",
                     "-i", str(p), "-map", "0:a:0", "-vn", "-map_metadata", "-1", "-af", channel_filter + "," + normalized,
                     "-ar", "48000", "-ac", str(channels), "-c:a", "libmp3lame", "-b:a", "128k" if channels == 1 else "192k",
                     str(stage)], max(60, min(3600, measurements["media"]["duration_seconds"] * 2 + 30)))
        verified = measure(stage, seconds=None)
        actual = verified["levels"]
        if abs(actual["input_i"] - lufs) > 1 or actual["input_tp"] > -1:
            raise StudioError("Encoded output misses loudness/peak targets; final output was not created")
        # The exclusive final open also refuses a file that appeared during processing.
        with destination.open("xb") as final, stage.open("rb") as source:
            shutil.copyfileobj(source, final)
    return {"output": str(destination), "channels": channels, "sample_rate": 48000,
            "target_lufs": lufs, "target_true_peak_dbtp": -1.5, "measured_output": verified,
            "listening_review": "required", "published": False}


def https_url(value, label: str, draft: bool = False) -> str:
    url = text_value(value, label)
    if any(c.isspace() for c in url) or not url.isascii():
        raise StudioError(f"{label} needs an ASCII HTTPS URL without whitespace")
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.scheme != "https" or not host or parts.username or parts.password or parts.fragment or parts.query:
        raise StudioError(f"{label} needs a stable HTTPS URL without credentials, query or fragment")
    if host == "localhost" or host.endswith(".localhost") or "." not in host:
        raise StudioError(f"{label} must not use a local hostname")
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise StudioError(f"{label} must not use a private IP address")
    except ValueError as err:
        if isinstance(err, StudioError):
            raise
    reserved = ("example.com", "example.org", "example.net", "example", "test", "invalid", "local")
    if not draft and any(host == x or host.endswith("." + x) for x in reserved):
        raise StudioError(f"{label} is a placeholder; use --draft only for examples")
    return url


def build_feed(show: dict, episodes: list, draft: bool = False) -> bytes:
    if not isinstance(show, dict) or not isinstance(episodes, list) or not episodes:
        raise StudioError("A show object and at least one episode are required")
    ET.register_namespace("itunes", ITUNES)
    ET.register_namespace("atom", ATOM)
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    for key in ("title", "description", "language"):
        ET.SubElement(channel, key).text = text_value(show.get(key), key)
    ET.SubElement(channel, "link").text = https_url(show.get("website_url"), "website_url", draft)
    ET.SubElement(channel, f"{{{ATOM}}}link", {"href": https_url(show.get("feed_url"), "feed_url", draft),
                                               "rel": "self", "type": "application/rss+xml"})
    ET.SubElement(channel, f"{{{ITUNES}}}author").text = text_value(show.get("author"), "author")
    ET.SubElement(channel, f"{{{ITUNES}}}image", {"href": https_url(show.get("artwork_url"), "artwork_url", draft)})
    if type(show.get("explicit")) is not bool:
        raise StudioError("show.explicit must be a boolean")
    ET.SubElement(channel, f"{{{ITUNES}}}explicit").text = str(show["explicit"]).lower()
    ET.SubElement(channel, f"{{{ITUNES}}}type").text = "episodic"
    # One deliberately supported taxonomy pair; other categories require a verified update.
    category = ET.SubElement(channel, f"{{{ITUNES}}}category", {"text": "Leisure"})
    ET.SubElement(category, f"{{{ITUNES}}}category", {"text": "Video Games"})
    guids, enclosures = set(), set()
    for episode in episodes:
        if not isinstance(episode, dict):
            raise StudioError("Each episode must be an object")
        guid = text_value(episode.get("guid"), "episode.guid")
        enclosure = https_url(episode.get("audio_url"), "episode.audio_url", draft)
        if guid in guids or enclosure in enclosures:
            raise StudioError("Episode GUIDs and enclosure URLs must be unique")
        guids.add(guid)
        enclosures.add(enclosure)
        mime = episode.get("mime_type")
        if mime not in {"audio/mpeg", "audio/mp4"}:
            raise StudioError("Supported enclosure MIME types are audio/mpeg and audio/mp4")
        length = positive_int(episode.get("length_bytes"), "length_bytes")
        duration = positive_int(episode.get("duration_seconds"), "duration_seconds")
        if type(episode.get("explicit")) is not bool:
            raise StudioError("episode.explicit must be a boolean")
        try:
            date = datetime.fromisoformat(episode["published_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError, TypeError, AttributeError):
            raise StudioError("published_at needs an ISO date/time with a timezone") from None
        if date.tzinfo is None or date.utcoffset() is None:
            raise StudioError("published_at must include a timezone")
        item = ET.SubElement(channel, "item")
        for key in ("title", "description"):
            ET.SubElement(item, key).text = text_value(episode.get(key), f"episode.{key}")
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = guid
        ET.SubElement(item, "pubDate").text = format_datetime(date.astimezone(timezone.utc))
        ET.SubElement(item, "enclosure", {"url": enclosure, "length": str(length), "type": mime})
        ET.SubElement(item, f"{{{ITUNES}}}duration").text = str(duration)
        ET.SubElement(item, f"{{{ITUNES}}}explicit").text = str(episode["explicit"]).lower()
    ET.indent(rss, space="  ")
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True)


def obs_auth(password: str, salt: str, challenge: str) -> str:
    secret = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
    return base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()


async def obs_status(port: int = 4455) -> dict:
    if type(port) is not int or not 1 <= port <= 65535:
        raise StudioError("port must be an integer from 1 to 65535")
    password = os.environ.get("EMBERBANTER_OBS_PASSWORD")
    if not password:
        raise StudioError("Set EMBERBANTER_OBS_PASSWORD privately on the OBS computer; do not paste it into chat")
    try:
        from websockets.asyncio.client import connect
    except ImportError:
        raise StudioError("Install this project's obs extra for localhost OBS checks") from None
    try:
        async with connect(f"ws://127.0.0.1:{port}", proxy=None, open_timeout=3, close_timeout=2, max_size=1_048_576) as ws:
            hello = json.loads(await asyncio.wait_for(ws.recv(), 3))
            auth = hello.get("d", {}).get("authentication")
            if hello.get("op") != 0 or not isinstance(auth, dict):
                raise StudioError("OBS must require WebSocket authentication; enable it in OBS Tools")
            identify = {"rpcVersion": 1, "eventSubscriptions": 0,
                        "authentication": obs_auth(password, text_value(auth.get("salt"), "salt"), text_value(auth.get("challenge"), "challenge"))}
            await ws.send(json.dumps({"op": 1, "d": identify}))
            if json.loads(await asyncio.wait_for(ws.recv(), 3)).get("op") != 2:
                raise StudioError("OBS identification was not acknowledged")
            results = {}
            for index, request in enumerate(OBS_REQUESTS):
                request_id = f"emberbanter-{index}"
                await ws.send(json.dumps({"op": 6, "d": {"requestType": request, "requestId": request_id}}))
                reply = json.loads(await asyncio.wait_for(ws.recv(), 3))
                data = reply.get("d", {})
                if reply.get("op") != 7 or data.get("requestId") != request_id or data.get("requestType") != request:
                    raise StudioError("Unexpected OBS response")
                if data.get("requestStatus", {}).get("result") is not True:
                    raise StudioError(f"OBS {request} failed")
                results[request] = data.get("responseData", {})
            return {"scope": "authenticated localhost snapshot; no state changes requested", "results": results,
                    "acceptance": "not a live audio/video test", "mutation_requests_sent": 0}
    except StudioError:
        raise
    except Exception:
        raise StudioError("Cannot read local OBS status; check OBS, port, authentication and the local client version") from None


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--version", action="version", version=VERSION)
    subs = root.add_subparsers(dest="command", required=True)
    subs.add_parser("doctor", help="Inspect software on the computer running this command")
    p = subs.add_parser("preflight", help="Check supplied operator confirmations; never go live")
    p.add_argument("profile")
    p = subs.add_parser("plan", help="Generate an unpublished show rundown")
    p.add_argument("--kind", choices=["stream", "podcast"], required=True)
    p.add_argument("--minutes", type=int, default=45)
    p.add_argument("--topic", required=True)
    p.add_argument("--output")
    p = subs.add_parser("audio-analyze", help="Measure local media; defaults to its first ten minutes")
    p.add_argument("input")
    p.add_argument("--seconds", type=float, default=600)
    p.add_argument("--full", action="store_true")
    p = subs.add_parser("audio-export", help="Two-pass podcast MP3 export with post-encode measurement")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--channels", type=int, choices=[1, 2], default=2)
    p.add_argument("--lufs", type=float, default=-16)
    p = subs.add_parser("rss", help="Generate local XML; external hosting/submission is never performed")
    p.add_argument("--show", required=True)
    p.add_argument("--episodes", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--draft", action="store_true", help="Allow reserved example domains; output is a demonstration")
    p = subs.add_parser("obs-status", help="Only four read requests to authenticated OBS on 127.0.0.1")
    p.add_argument("--port", type=int, default=4455)
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor()
        elif args.command == "preflight":
            result = preflight(read_json(args.profile))
        elif args.command == "plan":
            result = plan(args.kind, args.minutes, args.topic)
            if args.output:
                print(json.dumps({"output": write_new(args.output, result), "published": False}))
            else:
                print(result)
            return 0
        elif args.command == "audio-analyze":
            result = measure(args.input, None if args.full else args.seconds)
        elif args.command == "audio-export":
            result = export_audio(args.input, args.output, args.channels, args.lufs)
        elif args.command == "rss":
            feed = build_feed(read_json(args.show), read_json(args.episodes), args.draft)
            result = {"output": write_new(args.output, feed), "draft": args.draft, "published": False,
                      "external_checks": "not_run: media bytes/duration, artwork, HEAD/range requests, public hosting and platform validation"}
        elif args.command == "obs-status":
            result = asyncio.run(obs_status(args.port))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if result.get("status") == "NOT_READY" else 0
    except (StudioError, OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({"error": str(error), "published": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
