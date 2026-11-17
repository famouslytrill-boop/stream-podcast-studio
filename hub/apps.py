"""Discover and launch named installed tools; never accept executables or shell text."""
import os
from pathlib import Path
import platform
import shutil
import subprocess

from tools.studio_tools import StudioError

APPS = {
    "flstudio": {"name": "FL Studio", "role": "Music production and native project editing", "license": "Existing proprietary installation"},
    "obs": {"name": "OBS", "role": "Gaming, streaming and recording", "license": "GPL-2.0-or-later"},
    "blender": {"name": "Blender", "role": "3D, animation and music-video work", "license": "GPL-2.0-or-later"},
    "shotcut": {"name": "Shotcut", "role": "Nonlinear audio/video editing", "license": "GPL-3.0-or-later"},
    "audacity": {"name": "Audacity", "role": "Podcast and audio editing", "license": "GPL-3.0-or-later"},
    "vscode": {"name": "VS Code", "role": "Engineering workspace", "license": "Installed Microsoft distribution; source Code-OSS is MIT"},
}


def resolve(app_id):
    if app_id not in APPS:
        raise StudioError("Choose a named studio application")
    if platform.system() == "Windows":
        program = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
        paths = {
            "flstudio": sorted((program / "Image-Line").glob("FL Studio*/FL64.exe"), reverse=True),
            "obs": [program / "obs-studio/bin/64bit/obs64.exe"],
            "blender": sorted((program / "Blender Foundation").glob("Blender*/blender.exe"), reverse=True),
            "shotcut": [local / "EmberBanter/apps/shotcut-26.9.27/Shotcut/shotcut.exe", program / "Shotcut/shotcut.exe"],
            "audacity": sorted((local / "EmberBanter/apps/audacity-4.0.2").glob("*/bin/Audacity4.exe"), reverse=True) + [program / "Audacity/Audacity.exe"],
            "vscode": [local / "Programs/Microsoft VS Code/Code.exe"],
        }[app_id]
        return next((p.resolve() for p in paths if p.is_file() and not p.is_symlink()), None)
    commands = {"flstudio": None, "obs": "obs", "blender": "blender", "shotcut": "shotcut", "audacity": "audacity", "vscode": "code"}
    command = commands[app_id]
    path = shutil.which(command) if command else None
    return Path(path).resolve() if path else None


def inventory():
    return [{"id": key, **value, "installed": resolve(key) is not None, "control": "launcher; app-specific deep editing is separate"}
            for key, value in APPS.items()]


def launch(params):
    app_id = params["app"]
    path = resolve(app_id)
    if not path:
        raise StudioError("This application is not installed at a verified location")
    process = subprocess.Popen([str(path)], cwd=path.parent, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
    return {"app": app_id, "launched": True, "pid": process.pid,
            "editing_performed": False, "published": False, "recording_started": False}
