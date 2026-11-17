"""Explicit read checks and setup guidance; connection health is not hardware acceptance."""
import importlib.util
import math
import time

from hub import VERSION
from hub.credentials import profile
from hub.obs import OBSConnectionError,status
from tools.studio_tools import StudioError,doctor


def number(value):
    return value if type(value) in {int,float} and math.isfinite(value) and value>=0 else None


def frame_ratio(stats,skipped_key,total_key):
    skipped=number(stats.get(skipped_key));total=number(stats.get(total_key))
    return {"skipped":skipped,"total":total,"percent":100*skipped/total if total and skipped is not None and skipped<=total else None}


def snapshot(ws,*,phone_origin=None):
    checked=time.time();tools=doctor();software={k:v["found"] for k,v in tools["binaries"].items()}
    software["obs_client"]=importlib.util.find_spec("websockets") is not None
    obs={"state":"not_configured","connected":False,"message":"Connect existing authenticated OBS privately on the laptop.","source":"not_configured","port":4455}
    try:
        connection=profile(ws.root)
        obs.update(source=connection["source"],port=connection["port"])
        if connection["configured"]:
            live=status(ws);stats=live.get("stats",{})
            obs.update(state="connected",connected=True,message="Authenticated read check passed. Hardware routing still needs your rehearsal.",
                       version=live.get("version"),recording_active=live["recording"].get("outputActive"),streaming_active=live["stream"].get("outputActive"),
                       stats={"basis":"cumulative_counters_at_check; not a timed rehearsal test","fps":number(stats.get("activeFps")),
                              "cpu_percent":number(stats.get("cpuUsage")),"average_render_ms":number(stats.get("averageFrameRenderTime")),
                              "rendering":frame_ratio(stats,"renderSkippedFrames","renderTotalFrames"),
                              "encoding":frame_ratio(stats,"outputSkippedFrames","outputTotalFrames")})
    except OBSConnectionError as error:obs.update(state=error.code,message=str(error))
    except StudioError:obs.update(state="credential_unavailable",message="The saved OBS profile cannot be used on this account. Reconnect it privately on the laptop.")
    except (OSError,ValueError,KeyError,TypeError):obs.update(state="check_failed",message="OBS did not return a complete diagnostic snapshot. Inspect it locally before retrying.")
    blockers=[]
    for binary in ("ffmpeg","ffprobe"):
        if not software.get(binary):blockers.append({"id":binary,"label":"Install "+binary+" from the intended official package on the executing computer."})
    if not software["obs_client"]:blockers.append({"id":"obs_dependency","label":"Install the optional OBS client dependency before its authenticated read check."})
    if not obs["connected"]:blockers.append({"id":"obs_connection","label":obs["message"]})
    if ws.recordings_root is None:blockers.append({"id":"capture_folder","label":ws.recordings_issue or "Configure the one intended local OBS recordings folder."})
    return {"version":VERSION,"checked_at":checked,"scope":"this executing hub host","software":software,"obs":obs,
            "capture_folder":{"configured":ws.recordings_root is not None,"state":"unavailable" if ws.recordings_issue else "configured" if ws.recordings_root is not None else "not_configured","recursive":False},
            "phone":{"state":"origin_configured_device_unverified" if phone_origin else "not_configured","verified":False},
            "platforms":{"state":"manual_handoff_only","authenticated_upload_adapters":0},
            "blockers":blockers,"latest_rehearsal":next(iter(ws.listing("rehearsals")),None),
            "read_checks_only":True,"hardware_acceptance":"requires_owner_rehearsal","public_delivery_verified":False,"actions_executed":0}
