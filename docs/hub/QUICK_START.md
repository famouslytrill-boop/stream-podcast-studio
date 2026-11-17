# Creator control 0.7.0 additions

Open **Create** for installed local narration voices and saved scene plans. Use **Platforms** for official portal links, private handoff files and upload/encoder checks. **History** shows actual jobs and repair guidance; **Review replay** always requires a fresh exact owner approval. The public kit labels Gaming, Streaming and Podcasts only. Existing setup follows.

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

Use the running server's workspace/port. Thirteen tools inspect, save edits/projects/documents, import selected local media, run the studio command language, calculate media estimates and propose actions. Approve pending actions in Connections in the owner web UI. No agent approval tool is provided. No platform account, broadcast or publication is activated by installation.

## Music, music video and shell

Use Dashboard to create a Music, Music video, Gaming, Streaming or Podcast project. Music imports stems and exports a reviewed WAV/MP3 mix or a MIDI sketch. Music video pairs a chosen song with artwork/footage and optional waveform/chroma key. Library writes versioned lyrics/scripts/notes. Dashboard shell `help` lists its actual scoped commands; `apps` lists detected editors. Automation reviews a fixed workflow or studio checks. Brand kit downloads the selected EmberBanter masters. Read [creative-suite details](CREATIVE_SUITE_2026-11-17.md).

## OBS capture and episodes

Use **Capture inbox** to scan the configured recordings folder after OBS finishes saving. Review one snapshot, approve its protected import, then Build episode. **Episodes** arranges multiple recordings and chapter labels, selected audio tracks and final-timeline captions. Review the new MP4/WAV/MP3 delivery. Capture inbox also offers a verified MP4 editing copy without re-encoding and launcher buttons for Shotcut/Audacity. See [broadcast workflow contracts](BROADCAST_0.6.0.md).
