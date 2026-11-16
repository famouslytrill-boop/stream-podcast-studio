# stream-podcast-studio
Private streaming and podcast production workspace, scripts, research, brand concepts and local tools

## Continue here

EmberBanter — **Clock out. Queue up.** Working brand; final brand and handles are not confirmed.

- [Current device evidence and remaining blocker](docs/CURRENT_STATE.md)
- [First 90-minute stream and 35-minute podcast rehearsal](docs/FIRST_SHOW.md)
- [Local recording-to-clips workflow](docs/CLIP_WORKFLOW.md)
- [Verified monetization and growth research](docs/RESEARCH_2026-11-16.md)
- [Existing scene gallery](assets/brand/Preview.html) — open the local checkout's file in a browser; GitHub's HTML viewer is not the scene preview.

Run from this repository on the streaming computer:

```powershell
python tools/studio_tools.py doctor
python tools/open_studio.py
python tools/clip_tools.py --help
```

The launcher selects the system OBS installation checked on DTG, avoiding the older copy found on PATH. It does not record, stream or change OBS settings.

Optional editable install: `python -m pip install -e .` in a project virtual environment. The core tools need no third-party Python packages. Authenticated loopback OBS status additionally needs the optional `obs` extra; set its password privately on that computer.

Tests: `python -m unittest discover -s tests -v`.

Recordings, rendered media, secrets and private device files are excluded from Git. Session and clip CSV templates are intentionally empty. Use actual channel URLs, timestamps and measured results; missing data stays blank.

The source toolkit is v0.2.0. The installed ChatGPT plugin and the carried-forward core CLI are v0.1.0; adding repository tools does not update the installed plugin. No command in this toolkit publishes content or starts a broadcast.
