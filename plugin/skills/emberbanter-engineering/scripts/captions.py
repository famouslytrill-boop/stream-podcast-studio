"""Plain reviewed SRT captions, source-time clipping and fixed local ASS styling."""
from dataclasses import dataclass
import hashlib
import html
from pathlib import Path
import re
import textwrap

try:
    from .studio_tools import StudioError
except ImportError:
    from studio_tools import StudioError


@dataclass(frozen=True)
class Cue:
    start_ms: int
    end_ms: int
    text: str


def timestamp_ms(value: str) -> int:
    match = re.fullmatch(r"(\d{2,3}):([0-5]\d):([0-5]\d)[,.](\d{3})", value)
    if match is None:
        raise StudioError("SRT timestamps need HH:MM:SS,mmm")
    hours, minutes, seconds, millis = map(int, match.groups())
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def parse_srt(text: str) -> list[Cue]:
    if len(text) > 2_000_000:
        raise StudioError("Caption text exceeds 2 MB")
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise StudioError("Caption file has no cues")
    result, ids = [], set()
    for block in re.split(r"\n[ \t]*\n", text):
        lines = block.splitlines()
        if len(lines) < 3 or not re.fullmatch(r"\d+", lines[0].strip()):
            raise StudioError("Each SRT cue needs an index, timing line and caption text")
        index = int(lines[0].strip())
        if index <= 0 or index in ids:
            raise StudioError("SRT cue indices must be positive and unique")
        ids.add(index)
        times = re.fullmatch(r"\s*(\S+)\s+-->\s+(\S+)\s*", lines[1])
        if times is None:
            raise StudioError("SRT timing line must contain one start and end")
        start, end = (timestamp_ms(value) for value in times.groups())
        if end <= start or (result and start < result[-1].end_ms):
            raise StudioError("SRT cues must have positive duration and chronological non-overlapping times")
        caption = "\n".join(line.strip() for line in lines[2:]).strip()
        caption = re.sub(r"</?(?:i|b|u)>", "", caption, flags=re.I)
        caption = html.unescape(caption).replace("\t", " ")
        if (not caption or len(caption) > 500 or re.search(r"<[^>]*>", caption)
                or any(c in caption for c in "\\{}")
                or any(ord(c) < 32 and c != "\n" for c in caption)):
            raise StudioError("Use plain caption text, up to 500 characters per cue; remove unsupported markup/control codes")
        result.append(Cue(start, end, caption))
        if len(result) > 10000:
            raise StudioError("Caption file exceeds 10,000 cues")
    return result


def load_captions(config, parent: Path, duration_seconds: float) -> tuple[list[Cue], dict]:
    if config is None:
        return [], {"enabled": False, "review_pending": []}
    if not isinstance(config, dict) or config.get("timebase") != "source":
        raise StudioError("captions must be an object with timebase set to source")
    name = config.get("file")
    if not isinstance(name, str) or not name.strip() or "://" in name or name.startswith(("\\\\", "//")):
        raise StudioError("Caption file must be a local SRT path")
    path = Path(name).expanduser()
    path = (path if path.is_absolute() else parent / path).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != ".srt" or path.stat().st_size > 2_000_000:
        raise StudioError("Choose a local .srt file no larger than 2 MB")
    raw = path.read_bytes()
    try:
        cues = parse_srt(raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        raise StudioError("Caption file must use UTF-8 text") from None
    if cues[-1].end_ms > round(duration_seconds * 1000):
        raise StudioError("Caption times extend beyond the source recording")
    return cues, {
        "enabled": True, "timebase": "source", "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_cue_count": len(cues), "review_pending": [] if config.get("reviewed") is True else ["captions_reviewed"],
    }


def rebase_cues(cues: list[Cue], start: float, end: float) -> list[Cue]:
    start_ms, end_ms = round(start * 1000), round(end * 1000)
    return [Cue(max(c.start_ms, start_ms) - start_ms, min(c.end_ms, end_ms) - start_ms, c.text)
            for c in cues if c.end_ms > start_ms and c.start_ms < end_ms]


def srt_timestamp(ms: int) -> str:
    seconds, millis = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def srt_text(cues: list[Cue]) -> str:
    return "\n\n".join(f"{i}\n{srt_timestamp(c.start_ms)} --> {srt_timestamp(c.end_ms)}\n{c.text}"
                       for i, c in enumerate(cues, 1)) + "\n"


def ass_timestamp(ms: int, end=False) -> str:
    centiseconds = (ms + (9 if end else 0)) // 10
    seconds, centiseconds = divmod(centiseconds, 100)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"


def ass_text(cues: list[Cue]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,54,&H00E8F1F4,&H00E8F1F4,&H00161210,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,90,150,310,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for c in cues:
        wrapped = []
        for line in c.text.splitlines():
            wrapped.extend(textwrap.wrap(line, width=30, break_long_words=False, break_on_hyphens=False))
        text = "\\N".join(wrapped)
        lines.append(f"Dialogue: 0,{ass_timestamp(c.start_ms)},{ass_timestamp(c.end_ms, True)},Default,,0,0,0,,{text}")
    return header + "\n".join(lines) + "\n"
