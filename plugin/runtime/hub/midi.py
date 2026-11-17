"""Original deterministic 1–8 bar MIDI sketches and a clearly labeled guide tone."""
import array
import json
import math
import struct
import sys
import wave

from hub.projects import title
from tools.studio_tools import StudioError, finite

KEYS = {"A minor": (57, [0, 2, 3, 5, 7, 8, 10], [0, 5, 3, 6]), "D minor": (50, [0, 2, 3, 5, 7, 8, 10], [0, 5, 3, 6]),
        "E minor": (52, [0, 2, 3, 5, 7, 8, 10], [0, 6, 2, 3]), "C major": (60, [0, 2, 4, 5, 7, 9, 11], [0, 3, 5, 4])}


def prepare(data):
    bars = data.get("bars", 4)
    if type(bars) is not int or not 1 <= bars <= 8:
        raise StudioError("Choose 1–8 bars")
    key = data.get("key", "A minor")
    if key not in KEYS:
        raise StudioError("Choose A minor, D minor, E minor or C major")
    return {"title": title(data.get("title")), "bars": bars, "key": key,
            "bpm": finite(data.get("bpm", 100), "BPM", 30, 240)}


def vlq(value):
    out = [value & 127]
    value >>= 7
    while value:
        out.insert(0, (value & 127) | 128); value >>= 7
    return bytes(out)


def track(events, end_tick=0):
    data, last = bytearray(), 0
    for tick, event in sorted(events, key=lambda e: (e[0], e[1][0] & 0xf0 != 0x80)):
        data += vlq(tick-last) + event
        last = tick
    data += vlq(max(0, end_tick-last)) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + data


def make_notes(params):
    root, scale, progression = KEYS[params["key"]]
    notes = []
    for bar in range(params["bars"]):
        degree = progression[bar % len(progression)]
        shift = scale[degree]
        for interval in (0, 2, 4):
            index = degree+interval
            notes.append({"channel": 0, "note": root+scale[index%7]+12*(index//7), "beat": bar*4, "length": 3.5, "velocity": 68})
        for beat in (0, 2):
            notes.append({"channel": 1, "note": root+shift-12, "beat": bar*4+beat, "length": 1.5, "velocity": 82})
            notes.append({"channel": 9, "note": 36, "beat": bar*4+beat, "length": .2, "velocity": 90})
        for beat in (1, 3):
            notes.append({"channel": 9, "note": 38, "beat": bar*4+beat, "length": .15, "velocity": 78})
        for eighth in range(8):
            notes.append({"channel": 9, "note": 42, "beat": bar*4+eighth*.5, "length": .07, "velocity": 48 if eighth%2 else 58})
    return notes


def render(ws, job_id, params):
    directory = ws.root/"exports"/job_id
    directory.mkdir(exist_ok=False)
    ws.progress(job_id, "Planning tempo and note grid", 1, 3)
    notes = make_notes(params)
    tempo = round(60_000_000/params["bpm"])
    end_tick = params["bars"]*4*480
    chunks = [track([(0, b"\xff\x51\x03"+tempo.to_bytes(3, "big")), (0, b"\xff\x58\x04\x04\x02\x18\x08")], end_tick)]
    for channel in (0, 1, 9):
        events = []
        for note in notes:
            if note["channel"] == channel:
                events += [(round(note["beat"]*480), bytes([0x90+channel, note["note"], note["velocity"]])),
                           (round((note["beat"]+note["length"])*480), bytes([0x80+channel, note["note"], 0]))]
        chunks.append(track(events, end_tick))
    raw = b"MThd"+struct.pack(">IHHH", 6, 1, len(chunks), 480)+b"".join(chunks)
    (directory/"sketch.mid").write_bytes(raw)
    duration = params["bars"]*4*60/params["bpm"]
    rate, samples = 24000, array.array("h")
    melodic = [n for n in notes if n["channel"] != 9]
    for i in range(round(duration*rate)):
        t, value = i/rate, 0.
        beat = t*params["bpm"]/60
        for n in melodic:
            age = (beat-n["beat"])*60/params["bpm"]
            length = n["length"]*60/params["bpm"]
            if 0 <= age < length:
                frequency = 440*2**((n["note"]-69)/12)
                envelope = min(1, age/.015)*max(0, 1-age/length)
                value += .055*envelope*math.sin(2*math.pi*frequency*age)
        samples.append(round(max(-.7, min(.7, value))*32767))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(directory/"guide.wav"), "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate); out.writeframes(samples.tobytes())
    (directory/"notes.json").write_text(json.dumps({**params, "notes": notes, "guide": "Simple synthesized timing/pitch guide, not a finished production"}, indent=2))
    ws.progress(job_id, "MIDI and guide created; verifying files", 2, 3)
    from hub.render import finish
    from hub.core import digest
    result = finish(ws, job_id, ["guide.wav"], expected_duration=duration)
    result["files"].append({"name": "sketch.mid", "bytes": len(raw), "sha256": digest(directory/"sketch.mid"),
                            "format": "SMF1", "ticks_per_beat": 480, "tracks": 4, "audio": False})
    result["downloads"] += ["sketch.mid", "notes.json"]
    result["composition"] = {**params, "guide_only": True, "daw_import_tested": False}
    (directory/"receipt.json").write_text(json.dumps(result, indent=2))
    ws.progress(job_id, "Sketch files verified", 3, 3)
    return result
