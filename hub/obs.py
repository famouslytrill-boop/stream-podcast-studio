"""Authenticated, loopback-only OBS adapter. No streaming or arbitrary requests."""
import json
import os
import secrets

from tools.studio_tools import StudioError, finite, obs_auth

SIMPLE = {"record_start": "StartRecord", "record_stop": "StopRecord", "record_pause": "PauseRecord", "record_resume": "ResumeRecord"}
READS = ("GetVersion", "GetStats", "GetStreamStatus", "GetRecordStatus", "GetSceneList", "GetInputList")


def label(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200 or any(ord(c) < 32 for c in value):
        raise StudioError("Select an actual OBS scene or input")
    return value


def validate_action(params):
    action = params.get("action")
    if action in SIMPLE:
        if action == "record_start" and params.get("recording_consent") is not True:
            raise StudioError("Confirm that everyone being recorded has agreed before starting")
        return {"action": action, **({"recording_consent": True} if action == "record_start" else {})}
    if action == "scene":
        return {"action": action, "scene": label(params.get("scene"))}
    if action == "mute":
        if type(params.get("muted")) is not bool:
            raise StudioError("Choose a specific mute state")
        return {"action": action, "input": label(params.get("input")), "muted": params["muted"]}
    if action == "volume":
        return {"action": action, "input": label(params.get("input")), "db": finite(params.get("db"), "level dB", -60, 0)}
    raise StudioError("Unsupported OBS control. Go-live and service settings are not exposed")


class OBS:
    def __enter__(self):
        password = os.environ.get("EMBERBANTER_OBS_PASSWORD")
        if not password:
            raise StudioError("OBS connection needs its password set privately on the laptop")
        try:
            from websockets.sync.client import connect
            self.ws = connect("ws://127.0.0.1:4455", proxy=None, open_timeout=3, close_timeout=2, max_size=1048576)
            hello = json.loads(self.ws.recv(timeout=3))
            auth = hello.get("d", {}).get("authentication")
            if hello.get("op") != 0 or not isinstance(auth, dict):
                raise StudioError("Enable OBS WebSocket password authentication")
            proof = obs_auth(password, auth["salt"], auth["challenge"])
            self.ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1, "eventSubscriptions": 0, "authentication": proof}}))
            if json.loads(self.ws.recv(timeout=3)).get("op") != 2:
                raise StudioError("OBS did not acknowledge authentication")
            return self
        except Exception:
            if hasattr(self, "ws"):
                self.ws.close()
            raise StudioError("Cannot connect to authenticated local OBS. Check OBS and its WebSocket settings") from None

    def __exit__(self, *args):
        self.ws.close()

    def request(self, name, data=None):
        if name not in set(READS) | set(SIMPLE.values()) | {"SetCurrentProgramScene", "SetInputMute", "SetInputVolume"}:
            raise StudioError("OBS request is outside the studio allowlist")
        request_id = secrets.token_hex(16)
        self.ws.send(json.dumps({"op": 6, "d": {"requestType": name, "requestId": request_id, "requestData": data or {}}}))
        try:
            reply = json.loads(self.ws.recv(timeout=5))
            body = reply.get("d", {})
            if (reply.get("op") != 7 or body.get("requestId") != request_id or body.get("requestType") != name
                    or body.get("requestStatus", {}).get("result") is not True):
                raise StudioError("OBS did not complete the requested action")
            return body.get("responseData", {})
        except StudioError:
            raise
        except Exception:
            # A mutation may have reached OBS: no automatic retry.
            raise StudioError("OBS response was interrupted. Check OBS before proposing another action") from None


def status():
    with OBS() as obs:
        data = {name: obs.request(name) for name in READS}
    return {"connected": True, "recording": data["GetRecordStatus"], "stream": data["GetStreamStatus"],
            "scenes": [s["sceneName"] for s in data["GetSceneList"].get("scenes", [])],
            "scene": data["GetSceneList"].get("currentProgramSceneName"),
            "inputs": [i["inputName"] for i in data["GetInputList"].get("inputs", [])],
            "version": data["GetVersion"].get("obsVersion"), "stats": data["GetStats"]}


def perform(params):
    params = validate_action(params)
    action = params["action"]
    with OBS() as obs:
        if action in SIMPLE:
            result = obs.request(SIMPLE[action])
        elif action == "scene":
            names = [s["sceneName"] for s in obs.request("GetSceneList").get("scenes", [])]
            if params["scene"] not in names:
                raise StudioError("That scene no longer exists in OBS")
            result = obs.request("SetCurrentProgramScene", {"sceneName": params["scene"]})
        else:
            names = [i["inputName"] for i in obs.request("GetInputList").get("inputs", [])]
            if params["input"] not in names:
                raise StudioError("That input no longer exists in OBS")
            result = obs.request("SetInputMute" if action == "mute" else "SetInputVolume",
                                 {"inputName": params["input"], **({"inputMuted": params["muted"]} if action == "mute" else {"inputVolumeDb": params["db"]})})
        after = obs.request("GetRecordStatus")
    # The saved path is private machine data; return only the basename.
    if "outputPath" in result:
        from pathlib import PureWindowsPath
        result = {"saved_name": PureWindowsPath(result["outputPath"]).name}
    return {"action": action, "acknowledged": True, "recording": after, "details": result,
            "broadcast_started_by_hub": False, "hardware_acceptance": "not_tested"}
