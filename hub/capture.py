"""Selected finished recordings from one locally configured OBS capture folder."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import time

from hub.core import canonical, digest, identifier
from tools.studio_tools import StudioError

SUFFIXES = {".mkv", ".mp4", ".mov", ".webm", ".wav", ".flac", ".mp3", ".m4a"}


def linked(path):
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def validate_root(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096 or value.startswith(("\\\\", "//")) or "://" in value:
        raise StudioError("Configure one actual local recordings folder on the laptop")
    path = Path(value).expanduser()
    if not path.is_absolute() or any(linked(p) for p in (path, *path.parents)):
        raise StudioError("Recordings folder must be an absolute local folder without links")
    root = path.resolve()
    if root == Path(root.anchor) or root == Path.home().resolve() or not root.is_dir():
        raise StudioError("Select a dedicated existing recordings folder")
    return root


def configured_root(ws):
    value = ws.recordings_root
    if value is None:
        raise StudioError("Set the recordings folder on the laptop with connect_recordings; manual import is also available")
    return validate_root(str(value))


def signature(path):
    stat = path.stat()
    return {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "device": stat.st_dev, "inode": stat.st_ino}


def candidates(ws):
    root = configured_root(ws)
    found, truncated = [], False
    with os.scandir(root) as entries:
        for index, entry in enumerate(entries):
            if index >= 1000:
                truncated = True
                break
            path = Path(entry.path)
            if (path.suffix.lower() not in SUFFIXES or len(path.name) > 180 or any(ord(c) < 32 for c in path.name)
                    or linked(path) or not entry.is_file(follow_symlinks=False)):
                continue
            stat = entry.stat(follow_symlinks=False)
            if getattr(stat, "st_file_attributes", 0) & 0x400 or not 0 < stat.st_size <= 2*1024**3:
                continue
            opaque = hmac.new(ws.pairing_key.encode(), str(root/path.name).encode(), hashlib.sha256).hexdigest()[:32]
            found.append({"id": opaque, "name": path.name, **signature(path),
                          "stable": time.time_ns()-stat.st_mtime_ns >= 5_000_000_000})
    return sorted(found, key=lambda item: item["mtime_ns"], reverse=True), truncated


def scan(ws):
    items, truncated = candidates(ws)
    return {"recordings": [{k:v for k,v in item.items() if k not in {"device", "inode"}} for item in items[:50]],
            "truncated": truncated or len(items) > 50, "recursive": False,
            "basis": "file snapshots only; confirm OBS has finished and review the selected recording"}


def selected(ws, key):
    identifier(key)
    items, _ = candidates(ws)
    item = next((x for x in items if x["id"] == key), None)
    if not item:
        raise StudioError("Recording is missing, linked, unsupported or outside the configured folder")
    if not item["stable"]:
        raise StudioError("This recording changed recently. Stop recording and scan again")
    return item, configured_root(ws)/item["name"]


def prepare(ws, data):
    if data.get("recording_finished_reviewed") is not True:
        raise StudioError("Confirm recording has stopped and review the selected capture before import")
    item, _ = selected(ws, data.get("recording_id"))
    return {"recording": item, "recording_finished_reviewed": True}


def import_capture(ws, job_id, data):
    expected = data["recording"]
    current, path = selected(ws, expected["id"])
    fields = ("name", "bytes", "mtime_ns", "device", "inode")
    if any(current[k] != expected[k] for k in fields):
        raise StudioError("Capture changed after review; scan and review a new snapshot")
    if ws.obs_password_configured():
        from hub.obs import status
        if status()["recording"].get("outputActive"):
            raise StudioError("OBS is recording. Stop it before importing a finished capture")
    ws.progress(job_id, "Checking selected finished capture", 1, 3)
    original_hash = digest(path)
    item = None
    try:
        item = ws.import_media(path, current["name"])
        if item["sha256"] != original_hash or signature(path) != {k:current[k] for k in ("bytes", "mtime_ns", "device", "inode")} or digest(path) != original_hash:
            raise StudioError("Capture changed while copying; no verified import was retained")
    except Exception:
        if item:
            ws.media_path(item["id"]).unlink(missing_ok=True)
            with ws.db() as db:
                db.execute("DELETE FROM media WHERE id=?", (item["id"],))
            ws.log("capture.snapshot_rejected", item["id"])
        raise
    ws.progress(job_id, "Protected copy and source checksum verified", 2, 3)
    directory = ws.root/"exports"/job_id
    directory.mkdir(exist_ok=False)
    receipt = {"job_id":job_id, "media_id":item["id"], "name":item["name"], "source_sha256":original_hash,
               "source_preserved":True, "imported_bytes":item["bytes"], "recording_stopped_basis":"owner confirmation plus file snapshot; OBS status checked when configured",
               "published":False, "downloads":["import-receipt.json"]}
    (directory/"import-receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    ws.progress(job_id, "Capture imported to library", 3, 3)
    return receipt
