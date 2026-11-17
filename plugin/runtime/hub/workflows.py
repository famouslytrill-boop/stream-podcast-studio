"""Named deterministic planner, executor and verifier roles; no model or CI service."""
import ast
import json
from pathlib import Path
import time

from hub.apps import APPS, inventory, launch, resolve
from hub.core import digest
from tools.studio_tools import StudioError, doctor

RECIPES = [
    {"id": "music_mix", "name": "Finish a music mix", "steps": ["Verify stems", "Trim, align and mix", "Measure and render", "Decode and package"]},
    {"id": "music_video", "name": "Build a music video", "steps": ["Verify song and visuals", "Compose artwork/footage and optional chroma key", "Render", "Decode and package"]},
    {"id": "midi", "name": "Make a MIDI sketch", "steps": ["Plan tempo and note grid", "Write MIDI and guide", "Verify files"]},
    {"id": "engineering", "name": "Run studio checks", "steps": ["Inspect local tools", "Validate source and contracts", "Rebuild a workspace report"]},
]


def prepare(ws, kind, data):
    if kind == "music_mix":
        from hub.creative import prepare_mix
        clean = prepare_mix(ws, data)
        return clean, f"Mix {len(clean['tracks'])} stem(s), {clean['duration']:g}s, target {clean['target_lufs']:g} LUFS. Export new WAV/MP3 and verify; preserve all originals."
    if kind == "music_video":
        from hub.creative import prepare_video
        clean = prepare_video(ws, data)
        return clean, f"Render {clean['duration']:g}s {clean['format']} music video from the selected song and visual assets. Chroma key: {'on' if clean['foreground'] else 'off'}. No publication."
    if kind == "midi":
        from hub.midi import prepare as midi_prepare
        clean = midi_prepare(data)
        return clean, f"Create an original {clean['bars']}-bar {clean['key']} MIDI sketch at {clean['bpm']:g} BPM and a simple guide tone."
    if kind == "engineering":
        return {"recipe": "local_contract_check", "network": False, "source_writes": False}, "Run local syntax, manifest and workspace checks. Rebuild a diagnostic report. No source rewrite, deployment, package installation or GitHub checks."
    if kind == "launch_app":
        app = data.get("app")
        if app not in APPS or resolve(app) is None:
            raise StudioError("The requested studio application is not installed at a verified location")
        return {"app": app}, f"Open {APPS[app]['name']} on this laptop. Opening the app does not prove an edit or recording occurred."
    raise StudioError("Unknown deterministic workflow")


def engineering(ws, job_id):
    directory = ws.root/"exports"/job_id
    directory.mkdir(exist_ok=False)
    ws.progress(job_id, "Inspecting local tools", 1, 3)
    software = doctor()
    root = Path(__file__).parent
    checks = []
    for path in sorted(root.glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
            checks.append({"name": "syntax:"+path.name, "passed": True})
        except SyntaxError:
            checks.append({"name": "syntax:"+path.name, "passed": False})
    manifest = json.loads((root/"web/manifest.webmanifest").read_text())
    for icon in manifest["icons"]:
        checks.append({"name": "manifest:"+icon["src"], "passed": (root/"web"/icon["src"].lstrip("/")).is_file()})
    checks.append({"name": "unique_workflow_ids", "passed": len({r["id"] for r in RECIPES}) == len(RECIPES)})
    ws.progress(job_id, "Source and manifest contracts checked", 2, 3)
    # Repair only the derived diagnostic artifact; never alter source or user media.
    report = {"checks": checks, "passed": all(c["passed"] for c in checks),
              "software": {k:v["found"] for k,v in software["binaries"].items()}, "apps": inventory(),
              "projects": len(ws.listing("projects")), "documents": len(ws.listing("documents")),
              "network_calls": 0, "source_files_changed": 0, "model_calls": 0, "github_checks_started": False,
              "autonomy": "fixed deterministic steps; no self-modifying model agent", "created": time.time()}
    file = directory/"engineering-report.json"
    file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ws.progress(job_id, "Diagnostic report rebuilt", 3, 3)
    return {"report": report, "downloads": [file.name], "files": [{"name":file.name,"sha256":digest(file)}], "published": False}


def execute(ws, job_id, kind, data):
    if kind == "music_mix":
        from hub.creative import mix
        return mix(ws, job_id, data)
    if kind == "music_video":
        from hub.creative import music_video
        return music_video(ws, job_id, data)
    if kind == "midi":
        from hub.midi import render
        return render(ws, job_id, data)
    if kind == "engineering":
        return engineering(ws, job_id)
    if kind == "launch_app":
        return launch(data)
    raise StudioError("Unknown workflow executor")
