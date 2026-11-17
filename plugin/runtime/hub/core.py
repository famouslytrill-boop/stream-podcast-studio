"""Persistent personal workspace, immutable action proposals and a bounded worker."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import threading
import time
import uuid

from tools.captions import parse_srt
from tools.studio_tools import StudioError, finite, executable, run_process

MEDIA_SUFFIXES = {".mp4", ".mkv", ".mov", ".webm", ".wav", ".flac", ".mp3", ".m4a", ".ogg", ".opus"}
FORMATS = {"landscape": (1280, 720), "vertical": (1080, 1920), "podcast": None}
OBS_ACTIONS = {"record_start", "record_stop", "record_pause", "record_resume", "scene", "mute", "volume"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def identifier(value):
    if not isinstance(value, str) or len(value) != 32 or any(c not in "0123456789abcdef" for c in value):
        raise StudioError("Invalid workspace identifier")
    return value


def probe_media(path):
    result = run_process([executable("ffprobe"), "-v", "error", "-protocol_whitelist", "file,pipe",
                          "-show_format", "-show_streams", "-of", "json", "-i", str(path)], 30)
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")), None)
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    if not video and not audio:
        raise StudioError("No playable audio or video found")
    duration = data.get("format", {}).get("duration")
    basis = "container_metadata"
    if duration is None:
        # Browser MediaRecorder WebM often has no duration in its streaming header.
        # Decode one actual stream within a strict time budget; never invent its length.
        index = audio[0]["index"] if audio else video["index"]
        scan = run_process([executable("ffmpeg"), "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe",
                            "-i", str(path), "-map", f"0:{index}", "-t", "43201", "-progress", "pipe:1", "-nostats", "-f", "null", "-"], 60)
        timestamps = re.findall(r"^out_time_us=(\d+)$", scan.stdout, re.M)
        if not timestamps:
            raise StudioError("The recording has no measurable duration")
        duration = max(map(int, timestamps)) / 1_000_000
        basis = "decoded_stream_timestamps"
    return {"duration": finite(duration, "duration", .1, 43200), "duration_basis": basis,
            "video": bool(video), "width": video.get("width") if video else None,
            "height": video.get("height") if video else None,
            "audio_tracks": len(audio), "video_index": video.get("index") if video else None}


class Workspace:
    def __init__(self, path, *, recover=True):
        self.root = Path(path).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.file_lock = (self.root / ".hub-lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.file_lock.seek(0, 2)
                if not self.file_lock.tell():
                    self.file_lock.write(b"1"); self.file_lock.flush()
                self.file_lock.seek(0)
                msvcrt.locking(self.file_lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file_lock.close()
            raise StudioError("This studio workspace is already open. Use its existing server") from None
        for folder in ("media", "exports", "incoming"):
            (self.root / folder).mkdir(exist_ok=True)
        self.db_path = self.root / "studio.sqlite3"
        self.lock = threading.RLock()
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="studio-render")
        self.closed = False
        self.token_path = self.root / ".pairing-key"
        if not self.token_path.exists():
            try:
                with self.token_path.open("x", encoding="ascii") as f:
                    os.chmod(self.token_path, 0o600)
                    f.write(secrets.token_urlsafe(32))
            except FileExistsError:
                pass
        self.pairing_key = self.token_path.read_text(encoding="ascii").strip()
        if len(self.pairing_key) < 40:
            raise StudioError("Invalid private pairing key")
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY, data TEXT NOT NULL, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, data TEXT NOT NULL, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, at REAL NOT NULL, event TEXT NOT NULL, ref TEXT NOT NULL);
            """)
            if recover:
                # A restart never replays recording changes or ambiguous side effects.
                db.execute("UPDATE jobs SET state='interrupted' WHERE state IN ('queued','running')")
                db.execute("UPDATE actions SET state='expired' WHERE state='pending'")

    @contextmanager
    def db(self):
        with self.lock:
            db = sqlite3.connect(self.db_path, timeout=10)
            try:
                with db:
                    yield db
            finally:
                db.close()

    def close(self):
        self.closed = True
        self.worker.shutdown(wait=True)
        if os.name == "nt":
            import msvcrt
            self.file_lock.seek(0)
            msvcrt.locking(self.file_lock.fileno(), msvcrt.LK_UNLCK, 1)
        self.file_lock.close()

    def log(self, event, ref):
        with self.db() as db:
            db.execute("INSERT INTO audit(at,event,ref) VALUES(?,?,?)", (time.time(), event, ref))

    def get(self, table, key):
        assert table in {"media", "sessions", "actions", "jobs"}
        identifier(key)
        with self.db() as db:
            row = db.execute(f"SELECT data{',state' if table in {'actions','jobs'} else ''} FROM {table} WHERE id=?", (key,)).fetchone()
        if not row:
            raise StudioError("Workspace item does not exist")
        result = json.loads(row[0])
        if len(row) > 1:
            result["state"] = row[1]
        return result

    def listing(self, table):
        assert table in {"media", "sessions", "jobs", "actions"}
        with self.db() as db:
            rows = db.execute(f"SELECT id FROM {table} ORDER BY rowid DESC LIMIT 100").fetchall()
        return [self.get(table, r[0]) for r in rows]

    def media_path(self, media_id):
        item = self.get("media", media_id)
        path = self.root / "media" / (item["id"] + item["suffix"])
        if path.is_symlink() or path.resolve().parent != (self.root / "media").resolve() or not path.is_file():
            raise StudioError("Original recording is missing or moved")
        return path

    def import_media(self, source, name):
        name = Path(str(name).replace("\\", "/")).name
        suffix = Path(name).suffix.lower()
        if suffix not in MEDIA_SUFFIXES or len(name) > 180:
            raise StudioError("Choose a supported recording format")
        if shutil.disk_usage(self.root).free < Path(source).stat().st_size + 100_000_000:
            raise StudioError("Not enough workspace disk space for a protected copy")
        media_id = uuid.uuid4().hex
        target = self.root / "media" / (media_id + suffix)
        try:
            with Path(source).open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            info = probe_media(target)
            item = {"id": media_id, "name": name, "suffix": suffix, "bytes": target.stat().st_size,
                    "sha256": digest(target), "created": time.time(), **info}
            with self.db() as db:
                db.execute("INSERT INTO media VALUES(?,?)", (media_id, canonical(item)))
            self.log("recording.imported", media_id)
            return item
        except Exception:
            target.unlink(missing_ok=True)
            raise

    def validate_session(self, data):
        if not isinstance(data, dict):
            raise StudioError("Session must be an object")
        title = data.get("title", "Untitled session")
        if not isinstance(title, str) or not title.strip() or len(title) > 150 or any(ord(c) < 32 for c in title):
            raise StudioError("Choose a session title of 1–150 characters")
        media_id = identifier(data.get("media_id"))
        media = self.get("media", media_id)
        format_name = data.get("format", "landscape")
        if format_name not in FORMATS or (format_name != "podcast" and not media["video"]):
            raise StudioError("This recording needs a compatible export format")
        track = data.get("audio_track", 0)
        if type(track) is not int or track < 0 or track >= max(1, media["audio_tracks"]):
            raise StudioError("Choose an existing audio track")
        if format_name == "podcast" and not media["audio_tracks"]:
            raise StudioError("Podcast export needs an audio track")
        cuts = data.get("cuts", [])
        if not isinstance(cuts, list) or len(cuts) > 12:
            raise StudioError("Use up to 12 cuts per sequence")
        clean, total = [], 0
        for cut in cuts:
            if not isinstance(cut, dict):
                raise StudioError("Each cut must contain a start and end")
            start = finite(cut.get("start"), "start", 0, media["duration"])
            end = finite(cut.get("end"), "end", 0, media["duration"])
            if end - start < .25:
                raise StudioError("Each cut needs at least 0.25 seconds")
            total += end - start
            clean.append({"start": start, "end": end})
        if total > 10800:
            raise StudioError("Sequence exceeds the three-hour export budget")
        captions = data.get("captions", "")
        if not isinstance(captions, str) or len(captions) > 200_000:
            raise StudioError("Caption text must be under 200 KB")
        if captions:
            cues = parse_srt(captions)
            if cues[-1].end_ms > round(media["duration"] * 1000):
                raise StudioError("Caption time exceeds the recording")
        return {"title": title.strip(), "media_id": media_id, "format": format_name, "audio_track": track,
                "cuts": clean, "captions": captions, "fade": data.get("fade") is True,
                "content_reviewed": data.get("content_reviewed") is True,
                "captions_reviewed": data.get("captions_reviewed") is True}

    def save_session(self, data):
        clean = self.validate_session(data)
        session_id = data.get("id") or uuid.uuid4().hex
        identifier(session_id)
        with self.db() as db:
            row = db.execute("SELECT data FROM sessions WHERE id=?", (session_id,)).fetchone()
            previous = json.loads(row[0]) if row else None
            if previous and data.get("revision") != previous["revision"]:
                raise StudioError("This session changed elsewhere. Reload it before saving")
            clean.update(id=session_id, revision=previous["revision"] + 1 if previous else 1, updated=time.time())
            db.execute("INSERT OR REPLACE INTO sessions VALUES(?,?)", (session_id, canonical(clean)))
        self.log("session.saved", session_id)
        return clean

    def propose(self, kind, params):
        if not isinstance(params, dict):
            raise StudioError("Action parameters must be an object")
        if kind == "render":
            session = self.get("sessions", identifier(params.get("session_id")))
            session = {**self.validate_session(session), "id": session["id"], "revision": session["revision"]}
            if not session["cuts"] or not session["content_reviewed"]:
                raise StudioError("Add a cut and review the actual content and rights first")
            if session["captions"] and not session["captions_reviewed"]:
                raise StudioError("Correct and review captions before exporting")
            params = {"session": session, "source_sha256": self.get("media", session["media_id"])["sha256"]}
            seconds = round(sum(c["end"] - c["start"] for c in session["cuts"]), 3)
            summary = f"Export {len(session['cuts'])} cut(s), {seconds:g} seconds, {session['format']}. Create a new private file; preserve the original."
        elif kind == "obs":
            from hub.obs import validate_action
            params = validate_action(params)
            summaries = {"record_start": "Start recording the configured OBS picture and audio on this laptop.",
                         "record_stop": "Stop the current OBS recording and save it using OBS settings.",
                         "record_pause": "Pause the current OBS recording.", "record_resume": "Resume the current OBS recording.",
                         "scene": "Switch the OBS program scene. If already live, viewers will see the change.",
                         "mute": "Change one OBS input's mute state. This also affects a current live broadcast.",
                         "volume": "Change one OBS input's level. This also affects a current live broadcast."}
            summary = summaries[params["action"]]
        elif kind == "bumper":
            title = params.get("title")
            if not isinstance(title, str) or not title.strip() or len(title) > 60 or any(ord(c) < 32 for c in title):
                raise StudioError("Bumper title needs 1–60 printable characters")
            params = {"title": title.strip(), "theme": params.get("theme", "ember")}
            if params["theme"] not in {"ember", "hearth", "vellum"}:
                raise StudioError("Unknown palette")
            summary = "Render a four-second original title bumper and synthesized three-note sound. Creates private files."
        else:
            raise StudioError("This action is not supported; public broadcasting and publishing are not connected")
        action_id = uuid.uuid4().hex
        body = {"id": action_id, "kind": kind, "params": params, "summary": summary,
                "expires": time.time() + 180, "created": time.time()}
        body["plan_sha256"] = hashlib.sha256(canonical(body).encode()).hexdigest()
        with self.db() as db:
            db.execute("INSERT INTO actions VALUES(?,?,?)", (action_id, canonical(body), "pending"))
        self.log("action.proposed", action_id)
        return {**body, "state": "pending"}

    def reject(self, action_id):
        with self.db() as db:
            result = db.execute("UPDATE actions SET state='rejected' WHERE id=? AND state='pending'", (identifier(action_id),))
            if result.rowcount != 1:
                raise StudioError("Action is no longer pending")
        self.log("action.rejected", action_id)

    def approve(self, action_id, plan_sha256):
        # This method is exposed only by the owner web UI, never by the local MCP tools.
        with self.db() as db:
            action = self.get("actions", action_id)
            if action["state"] != "pending" or action["expires"] < time.time():
                raise StudioError("Approval expired or was already used. Review a new proposal")
            if not isinstance(plan_sha256, str) or not secrets.compare_digest(action["plan_sha256"], plan_sha256):
                raise StudioError("Approval does not match the reviewed action")
            if action["kind"] == "render":
                saved = self.get("sessions", action["params"]["session"]["id"])
                if saved["revision"] != action["params"]["session"]["revision"]:
                    raise StudioError("Session changed after the proposal. Review a new export")
            count = db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]
            if count >= 4:
                raise StudioError("Four jobs are already waiting. Let them finish first")
            job_id = uuid.uuid4().hex
            job = {"id": job_id, "action_id": action_id, "kind": action["kind"], "summary": action["summary"], "created": time.time()}
            db.execute("UPDATE actions SET state='consumed' WHERE id=?", (action_id,))
            db.execute("INSERT INTO jobs VALUES(?,?,?)", (job_id, canonical(job), "queued"))
        self.log("action.owner_approved", action_id)
        self.worker.submit(self._run, job, action)
        return {**job, "state": "queued"}

    def _run(self, job, action):
        job_id = job["id"]
        try:
            with self.db() as db:
                db.execute("UPDATE jobs SET state='running' WHERE id=?", (job_id,))
            if action["kind"] == "render":
                from hub.render import render_sequence
                result = render_sequence(self, job_id, action["params"])
            elif action["kind"] == "bumper":
                from hub.render import render_bumper
                result = render_bumper(self, job_id, action["params"])
            else:
                from hub.obs import perform
                result = perform(action["params"])
            job.update(result=result, finished=time.time())
            state = "completed"
        except Exception as error:
            # Do not expose FFmpeg logs, raw metadata, machine paths or passwords.
            job.update(error=str(error) if isinstance(error, StudioError) else "Processing failed. Check local software and recording, then review a new proposal.", finished=time.time())
            state = "failed"
        with self.db() as db:
            db.execute("UPDATE jobs SET data=?,state=? WHERE id=?", (canonical(job), state, job_id))
        self.log("job." + state, job_id)
