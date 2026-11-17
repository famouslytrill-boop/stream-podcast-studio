# stream-podcast-studio
Personal music, gaming, streaming, podcast and music-video studio with local tools and reviewed deterministic workflows.

## Continue here

EmberBanter — **Clock out. Queue up.** Chosen studio identity. Handles and domains are not confirmed.

- [Creative suite, shell, automation and exact brand kit](docs/hub/CREATIVE_SUITE_2026-11-17.md)
- [Current device evidence and remaining blocker](docs/CURRENT_STATE.md)
- [First 90-minute stream and 35-minute podcast rehearsal](docs/FIRST_SHOW.md)
- [Local recording-to-clips workflow](docs/CLIP_WORKFLOW.md)
- [Reviewed captions and transcription benchmark](docs/CAPTION_EDITING.md)
- [Caption milestone: on-device results](docs/CAPTION_HANDOFF_2026-11-16.md)
- [Verified monetization and growth research](docs/RESEARCH_2026-11-16.md)
- [Existing scene gallery](assets/brand/Preview.html) — open the local checkout's file in a browser; GitHub's HTML viewer is not the scene preview.

Run from this repository on the streaming computer:

```powershell
python tools/studio_tools.py doctor
python tools/open_studio.py
python tools/open_editor.py
python tools/clip_tools.py --help
```

The launcher selects the system OBS installation checked on DTG, avoiding the older copy found on PATH. It does not record, stream or change OBS settings.

Optional editable install: `python -m pip install -e .` in a project virtual environment. The core tools need no third-party Python packages. Authenticated loopback OBS status additionally needs the optional `obs` extra; set its password privately on that computer.

Tests: `python -m unittest discover -s tests -v`.

Recordings, rendered media, secrets and private device files are excluded from Git. Session and clip CSV templates are intentionally empty. Use actual channel URLs, timestamps and measured results; missing data stays blank.

The source toolkit is v0.5.0. It can burn reviewed source-timeline SRT captions into clips while preserving the original files. The owned ChatGPT plugin's v0.4.0 source is now included under [plugin/](plugin/), with dedicated brand and economics workflows, scenario arithmetic, the selected EmberBanter brand kit and archived alternatives and the current media helpers. See the [plugin release evidence](docs/PLUGIN_0.2.0_RELEASE.md). An installed plugin release is verified separately through the backend; checking out this repository alone does not install it. No command in this toolkit publishes content or starts a broadcast.

## Personal Creator Hub

Use `python -m hub.server --open` for the private laptop application. Read the [quick start](docs/hub/QUICK_START.md), [architecture and capability boundaries](docs/hub/ARCHITECTURE.md), and [selected design kit](docs/hub/CREATIVE_SUITE_2026-11-17.md#brand-package). The hub adds a dashboard, scoped interactive shell, projects and actual versioned text files, eight-stem mixing, MIDI sketches, waveform/chroma-key music videos, fixed automation, studio diagnostics, app launch proposals, brand templates and 12 local MCP tools. Existing reviewed cuts, captions and microphone takes remain. A real phone needs private HTTPS pairing; ChatGPT mobile needs a separately connected hosted bridge. Neither is silently activated.
