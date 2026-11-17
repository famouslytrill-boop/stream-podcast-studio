Current prepared 0.8.0 extension: [persistent private OBS setup, diagnostics and owner rehearsal reports](rehearsal-readiness.md). Laptop upgrade/native acceptance pending while DTG is offline. Existing instructions below remain applicable where not extended.

# Local tools

The canonical executable is bundled at skills/emberbanter-engineering/scripts/studio_tools.py, relative to the plugin root. Resolve the actual installed path; don't assume a sandbox path persists on the owner's computer. Python 3.11+ is needed. The source repository also installs the command `emberbanter` into its virtual environment.

```bash
emberbanter doctor
emberbanter preflight config/live-profile.example.json
emberbanter plan --kind stream --minutes 90 --topic "After-work horror night"
emberbanter plan --kind podcast --minutes 35 --topic "When horror games stop being scary"
emberbanter audio-analyze recordings/test.wav --full
emberbanter audio-export recordings/edited-master.wav outputs/episode-001.mp3
emberbanter rss --show config/show.example.json --episodes config/episodes.example.json --output outputs/demo-feed.xml --draft
emberbanter obs-status
```

From the plugin without installing the CLI, replace `emberbanter` with `python3 "<resolved engineering skill directory>/scripts/studio_tools.py"` (on Windows use the discovered Python command). Resolve source-repository config paths separately or create equivalent local JSON from the requirements; the account ZIP has its own small example configurations in assets/examples/.

`doctor` checks the current executing environment, not another connected device. `preflight` exits 2 while confirmations or upload are missing and never goes live. `plan --output` and `rss --output` use exclusive creation. Analysis defaults to the first 600 seconds; use --full for the full first audio stream. Export preserves source media, requires a new MP3 path, normalizes and verifies the encoded file, then leaves listening review pending. Multi-hour media may exceed the bounded processing timeout; split/edit locally rather than increasing limits automatically.

OBS diagnostics need the optional `websockets==16.0` package and a privately set `EMBERBANTER_OBS_PASSWORD` environment variable on the executing OBS computer. The tool never reads a .env file automatically. Never ask for that password in chat, pass it as a CLI argument, commit it or expose network ports.

The legacy commands above do not upload, post, submit feeds, buy hardware, contact guests or start a broadcast. Chat skills orchestrate the user's existing tools; the package does not add hosted MCP tools. Check what runtime is actually available before promising execution on mobile.

## Bundled caption and clip tools (source toolkit v0.3.0)

Resolve the actual installed engineering skill path. The first command reviews the real recording without writing exports; the second requires corrected captions and explicit context/rights review flags in the manifest.

```bash
python3 "<engineering>/scripts/clip_tools.py" plan "<actual-manifest.json>"
python3 "<engineering>/scripts/clip_tools.py" render "<actual-manifest.json>" "<new-output-folder>"
python3 "<engineering>/scripts/transcription_benchmark.py" --help
```

See assets/examples/clips-captioned.example.json and captions.example.srt for synthetic structure only. Manifest media paths resolve relative to the manifest. Review the actual recording and SRT words/timing before changing review flags. Export uses 1080×1920 fit or center-crop, selects an explicit audio stream, rebases subtitle times, verifies decoding and preserves the source. A missing local model/binary cannot be solved by pretending an automatic transcription service exists. No model or owner recording is bundled.

## Scenario arithmetic and subjective clip rubric

```bash
python3 "<growth skill>/scripts/studio_strategy.py" economics "<plugin>/assets/examples/economics.example.json"
python3 "<growth skill>/scripts/studio_strategy.py" clip-score "<plugin>/assets/examples/clip-rubric.example.json"
```

The first example is visibly hypothetical, not an account forecast; receipt/cost inputs must be supplied. Missing/null receipt or cost inputs return incomplete, not zero revenue. The profit target is optional: without it, known receipts and costs still calculate while target fields remain unknown. The score is editing judgment, not a ranking algorithm or viral probability. Neither command creates a file, accesses the network or publishes.

## Personal creator hub

See [creator-hub.md](creator-hub.md). From a real source checkout use `python -m hub.server --open`; from this plugin use the resolved `runtime/serve_hub.py` path. The separate hub imports media, records browser takes and performs exact owner-reviewed OBS recording/scene/mixer writes. `studio_tools.py` remains read-only. Local MCP offers twenty-three tools and no approval tool; it requires a compatible local host. Neither runtime connects publishing or starts a public stream.
