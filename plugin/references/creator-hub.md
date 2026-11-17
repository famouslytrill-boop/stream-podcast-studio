# Open the personal studio

On DTG, use **Creator Hub** inside the existing **EmberBanter Studio** desktop folder. It starts the local service if necessary and privately pairs the laptop browser. It does not record or stream automatically. Keep the laptop awake while processing.

1. Import a recording or choose one from Library.
2. Set start/end for each moment; add, reorder, duplicate or remove cuts.
3. Paste corrected SRT using original recording timestamps; choose landscape, vertical or podcast format.
4. Review actual content/rights and caption accuracy; save the session.
5. Review the exact export, approve it, and inspect its actual state in Exports.
6. Download the file and receipt. Watch/listen before distribution.

The current sequence uses one source and one selected audio track. Existing Shotcut is available for broader manual editing; installation is not a remote editing API.

Connections → Record microphone records a browser take after its microphone permission prompt. Stop and save. If import fails, save the temporary take to that device or retry before closing the tab.

## Another computer

With Python 3.11+, FFmpeg and ffprobe, from the source folder:

```bash
python -m hub.server --open
```

Core needs no Python web dependency or Node build. OBS additionally needs the existing `websockets==16.0` optional extra. Use official software and a virtual environment.

To enable OBS control on Windows, first close the hub console, then run `scripts/start-hub.ps1 -ConnectOBS` in a permitted PowerShell session. It prompts privately for the existing OBS WebSocket password and passes it in the child environment. Keep authentication enabled; use loopback port 4455. Do not paste the password into chat/Git. The script changes no OBS authentication settings.

## Phone

Phone-sized rendering is tested; Dam's physical phone is not paired. A private HTTPS route must first be configured. After verifying an owner-controlled private reverse proxy, start with its actual hostname:

```bash
python -m hub.server --public-origin https://YOUR-VERIFIED-PRIVATE-HOST --open
```

The example is not a deployed URL. Open your verified address on the phone; enter the key from the laptop's Connections → Show private pairing key. Do not expose OBS or use an unauthenticated public tunnel. An offline shell cannot control the laptop.

## Local agent tools

The account plugin includes a portable local stdio configuration/runtime for a compatible local MCP host. This does not install a hosted server in ChatGPT mobile. A source checkout can run the equivalent:

```bash
python -m hub.mcp
```

Use the running server's workspace/port. Six tools inspect, save edits, calculate media estimates and propose actions. Approve pending actions in Connections in the owner web UI. No agent approval tool is provided. No platform account, broadcast or publication is activated by installation.

Architecture and limitations are in the source repository docs/hub/ARCHITECTURE.md. The packaged runtime is runtime/serve_hub.py (UI) and runtime/serve_mcp.py (stdio); resolve real paths on the executing computer.
