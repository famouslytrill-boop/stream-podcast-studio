"""Small local MCP stdio adapter; owner approval deliberately has no tool."""
import argparse
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from hub import VERSION

EMPTY = {"type": "object", "properties": {}, "additionalProperties": False}
TOOLS = [
    {"name": "studio_media_math", "description": "Calculate source-qualified frame, payload and optional measured render-time estimates. Missing measured speed stays unknown. No media processing or external calls.", "inputSchema": {"type": "object", "properties": {"duration_seconds": {"type": "number"}, "bitrate_bits_per_second": {"type": "number"}, "frames_per_second": {"type": "number"}, "measured_frames_per_second": {"type": ["number", "null"]}, "overhead_seconds": {"type": "number"}}, "required": ["duration_seconds", "bitrate_bits_per_second"], "additionalProperties": False}, "annotations": {"readOnlyHint": True}},
    {"name": "studio_status", "description": "Read actual local hub software and connection state; does not record or publish.", "inputSchema": EMPTY, "annotations": {"readOnlyHint": True}},
    {"name": "studio_library", "description": "List imported recordings, saved sessions, actions and job results in the personal workspace.", "inputSchema": EMPTY, "annotations": {"readOnlyHint": True}},
    {"name": "studio_session_save", "description": "Save a non-destructive edit session. Get recording identifiers from studio_library. Review flags need the owner's actual content/caption review.", "inputSchema": {"type": "object", "properties": {"session": {"type": "object"}}, "required": ["session"], "additionalProperties": False}, "annotations": {"destructiveHint": False, "openWorldHint": False}},
    {"name": "studio_propose", "description": "Prepare an exact render, bumper or OBS action for the owner to approve in the hub. This does not execute. There is no tool to approve on the owner's behalf.", "inputSchema": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["render", "bumper", "obs"]}, "params": {"type": "object"}}, "required": ["kind", "params"], "additionalProperties": False}, "annotations": {"destructiveHint": False, "openWorldHint": False}},
    {"name": "studio_job_status", "description": "Inspect one actual local job. Completed means its handler finished; inspect the receipt for specific evidence.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string", "pattern": "^[a-f0-9]{32}$"}}, "required": ["id"], "additionalProperties": False}, "annotations": {"readOnlyHint": True}},
]


class Client:
    def __init__(self, workspace, port=8765):
        if not 1024 <= port <= 65535:
            raise ValueError("Invalid local port")
        self.key_path = Path(workspace).expanduser().resolve() / ".pairing-key"
        self.origin = f"http://127.0.0.1:{port}"

    def request(self, route, data=None):
        try:
            key = self.key_path.read_text(encoding="ascii").strip()
            req = Request(self.origin + route, data=json.dumps(data, allow_nan=False).encode() if data is not None else None,
                          headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
            # Do not send local credentials through an inherited HTTP proxy.
            from urllib.request import build_opener, ProxyHandler
            with build_opener(ProxyHandler({})).open(req, timeout=45) as response:
                return json.load(response)
        except HTTPError as error:
            try:
                message = json.load(error).get("error", "Local command failed")
            except Exception:
                message = "Local command failed"
            raise ValueError(message) from None
        except (OSError, URLError):
            raise ValueError("Local studio is unavailable. Start the hub on this laptop and use its own workspace") from None

    def call(self, name, args):
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be an object")
        definition = next((t for t in TOOLS if t["name"] == name), None)
        if not definition:
            raise ValueError("Unknown studio tool")
        schema = definition["inputSchema"]
        if set(args) - set(schema["properties"]) or any(k not in args for k in schema.get("required", [])):
            raise ValueError("Unexpected or missing tool arguments")
        if name == "studio_media_math":
            from hub.planning import media_math
            return media_math(**args)
        if name == "studio_session_save":
            return self.request("/api/sessions", args["session"])
        if name == "studio_propose":
            return self.request("/api/propose", args)
        state = self.request("/api/state")
        if name == "studio_status":
            return {k: v for k, v in state.items() if k not in {"media", "sessions", "jobs", "actions", "csrf"}}
        if name == "studio_library":
            return {k: state[k] for k in ("media", "sessions", "jobs", "actions")}
        result = next((j for j in state["jobs"] if j["id"] == args["id"]), None)
        if not result:
            raise ValueError("Job not found in the current workspace result window")
        return result


def dispatch(message, client):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
    if "id" not in message:
        return None
    base = {"jsonrpc": "2.0", "id": message["id"]}
    method = message.get("method")
    params = message.get("params", {})
    if not isinstance(params, dict):
        return {**base, "error": {"code": -32602, "message": "Parameters must be an object"}}
    if method == "initialize":
        protocol = params.get("protocolVersion")
        if protocol not in {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}:
            protocol = "2025-06-18"
        result = {"protocolVersion": protocol, "capabilities": {"tools": {"listChanged": False}},
                  "serverInfo": {"name": "emberbanter-local-studio", "version": VERSION},
                  "instructions": "Private local production workspace. Propose actions, then ask the owner to review them in the hub. Never approve actions on their behalf."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        try:
            value = client.call(params.get("name"), params.get("arguments", {}))
            result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, allow_nan=False)}], "isError": False}
        except (ValueError, TypeError, KeyError):
            # Client errors are already scrubbed; a bad type must not expose internals.
            error = sys.exc_info()[1]
            result = {"content": [{"type": "text", "text": str(error) if isinstance(error, ValueError) else "Invalid studio arguments"}], "isError": True}
    else:
        return {**base, "error": {"code": -32601, "message": "Method not found"}}
    return {**base, "result": result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path.home() / "Documents" / "EmberBanterHub"))
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    client = Client(args.workspace, args.port)
    while True:
        raw = sys.stdin.buffer.readline(500_001)
        if not raw:
            break
        try:
            if len(raw) > 500_000:
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Message budget exceeded"}}), flush=True)
                break
            message = json.loads(raw)
            response = dispatch(message, client)
        except (ValueError, UnicodeError):
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid JSON message"}}
        if response is not None:
            print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
