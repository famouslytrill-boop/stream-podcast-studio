"""Versioned projects and real text files within the personal workspace."""
from pathlib import Path
import time
import uuid

from hub.core import canonical, digest, identifier
from tools.studio_tools import StudioError, finite

KINDS = ("music", "music_video", "gaming", "streaming", "podcast")


def title(value, maximum=150):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise StudioError(f"Use a title of 1–{maximum} printable characters")
    return value.strip()


def save_project(ws, data):
    if not isinstance(data, dict) or data.get("kind") not in KINDS:
        raise StudioError("Choose music, music_video, gaming, streaming or podcast")
    project_id = identifier(data.get("id") or uuid.uuid4().hex)
    assets = data.get("assets", [])
    if not isinstance(assets, list) or len(assets) > 64:
        raise StudioError("A project can link up to 64 imported assets")
    for asset in assets:
        ws.get("media", identifier(asset))
    bpm = data.get("bpm")
    key = data.get("key", "")
    if not isinstance(key, str) or len(key) > 30:
        raise StudioError("Key must be a short supplied label")
    clean = {"id": project_id, "title": title(data.get("title")), "kind": data["kind"],
             "assets": list(dict.fromkeys(assets)), "bpm": None if bpm is None else finite(bpm, "bpm", 30, 300),
             "key": key, "musical_metadata_basis": "owner_supplied", "updated": time.time()}
    with ws.db() as db:
        row = db.execute("SELECT data FROM projects WHERE id=?", (project_id,)).fetchone()
        if row:
            import json
            old = json.loads(row[0])
            if data.get("revision") != old["revision"]:
                raise StudioError("Project changed elsewhere. Reload before saving")
            clean["revision"] = old["revision"] + 1
        else:
            clean["revision"] = 1
        db.execute("INSERT OR REPLACE INTO projects VALUES(?,?)", (project_id, canonical(clean)))
    ws.log("project.saved", project_id)
    return clean


def read_document(ws, document_id):
    meta = ws.get("documents", identifier(document_id))
    path = ws.root / "documents" / meta["file"]
    if path.is_symlink() or not path.is_file() or path.resolve().parent != (ws.root / "documents").resolve():
        raise StudioError("Document file is missing or moved")
    if path.stat().st_size > 400_000 or digest(path) != meta["sha256"]:
        raise StudioError("Document changed outside the hub. Preserve it and import a new document revision")
    return {**meta, "content": path.read_text(encoding="utf-8")}


def save_document(ws, data):
    if not isinstance(data, dict):
        raise StudioError("Document needs title and content")
    content = data.get("content")
    if not isinstance(content, str) or len(content.encode("utf-8")) > 400_000 or "\x00" in content:
        raise StudioError("Studio text files must be UTF-8 text under 400 KB")
    document_id = identifier(data.get("id") or uuid.uuid4().hex)
    project_id = data.get("project_id")
    if project_id:
        ws.get("projects", identifier(project_id))
    with ws.db() as db:
        row = db.execute("SELECT id FROM documents WHERE id=?", (document_id,)).fetchone()
        previous = read_document(ws, document_id) if row else None
        if previous and data.get("revision") != previous["revision"]:
            raise StudioError("Document changed elsewhere. Reload before writing")
        revision = previous["revision"] + 1 if previous else 1
        filename = f"{document_id}-v{revision}.md"
        file = ws.root / "documents" / filename
        with file.open("x", encoding="utf-8", newline="") as out:
            out.write(content)
        clean = {"id": document_id, "title": title(data.get("title")), "project_id": project_id,
                 "revision": revision, "file": filename, "sha256": digest(file), "updated": time.time()}
        db.execute("INSERT OR REPLACE INTO documents VALUES(?,?)", (document_id, canonical(clean)))
    ws.log("document.revision_written", document_id)
    return {**clean, "content": content}
