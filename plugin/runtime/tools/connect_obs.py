"""Connect existing authenticated OBS locally; never enable its server or print a secret."""
import argparse
import getpass
import json
from pathlib import Path
import platform

from hub.credentials import password,port,profile,save
from hub.obs import OBS
from tools.studio_tools import StudioError


def existing_obs(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>16384:
        raise StudioError("Open OBS WebSocket settings locally; an existing settings file was not found")
    try:data=json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError,OSError):raise StudioError("OBS settings could not be read. Use the private password prompt instead") from None
    if not isinstance(data,dict):raise StudioError("OBS WebSocket settings need a valid object")
    if data.get("auth_required") is not True:raise StudioError("Keep OBS WebSocket password authentication enabled before connecting")
    if data.get("server_enabled") is not True:raise StudioError("OBS WebSocket server is disabled. Configure it locally with authentication and private network access first; this helper does not enable it")
    return {"password":password(data.get("server_password")),"port":port(data.get("server_port"))}


def connect(root,settings):
    if platform.system()!="Windows":raise StudioError("Persistent OBS connection setup uses Windows user protection. On this host, set a private process environment password instead")
    with OBS(settings=settings) as obs:
        version=obs.request("GetVersion").get("obsVersion")
        recording=obs.request("GetRecordStatus").get("outputActive")
        streaming=obs.request("GetStreamStatus").get("outputActive")
    result=save(root,settings["password"],settings["port"])
    return {**result,"authenticated_read_check":True,"obs_version":version,"recording_active":recording,"streaming_active":streaming,
            "obs_settings_changed":False,"recording_started":False,"broadcast_started":False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace",default=str(Path.home()/"Documents/EmberBanterHub"))
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--from-obs",action="store_true",help="Use existing enabled/authenticated OBS settings on this Windows account")
    mode.add_argument("--prompt",action="store_true",help="Read the password privately; never pass it as an argument")
    mode.add_argument("--status",action="store_true",help="Show saved profile metadata without decrypting or contacting OBS")
    parser.add_argument("--port",type=int,default=4455,help="Existing loopback OBS port for the private prompt")
    args=parser.parse_args(argv)
    try:
        if args.status:
            result={k:v for k,v in profile(Path(args.workspace)).items() if k in {"configured","source","port"}}
            result["authenticated_read_check"]=False
        else:
            if platform.system()!="Windows":raise StudioError("Persistent OBS connection setup is available on Windows; no device settings were changed")
            settings=existing_obs(Path.home()/"AppData/Roaming/obs-studio/plugin_config/obs-websocket/config.json") if args.from_obs else {"password":password(getpass.getpass("Existing OBS WebSocket password (private): ")),"port":port(args.port)}
            result=connect(Path(args.workspace).expanduser().resolve(),settings)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (StudioError,OSError):
        import sys
        error=sys.exc_info()[1]
        print(json.dumps({"configured":False,"error":str(error) if isinstance(error,StudioError) else "Connection setup could not be saved. Inspect the local workspace; the OBS server was not changed"}));return 2


if __name__=="__main__":raise SystemExit(main())
