# Creator control acceptance — November 17, 2026

Toolkit 0.7.0. Reviewed account plugin 0.6.0, personal/private, release `pluginrel_6afc1e0e998c81919e6a24886dae5a23`. The 147-file read-back preserved identity, author, prompts, scope and effective local MCP configuration. Twelve skills and 21 packaged tools are present. Local stdio initialize/tools-list/status executed on DTG against the running 0.7.0 hub; no approval tool or mobile bridge is implied.

## Test evidence

- Linux: 78 tests, passed with the actual Windows speech test skipped.
- DTG Windows: all 78 tests passed in 31.056 seconds, including real native speech.
- Actual Chrome, isolated synthetic workspace: narration WAV/MP3, saved two-scene narrated film with imported owner-brand artwork, platform handoff/calendar ZIP, actual CPU/GPU encode probes and a freshly reviewed replay all completed.
- Narration: 6.8945 seconds using Microsoft David Desktop; WAV and MP3 fully decoded, no provider calls.
- Storyboard: 261 picture frames at 30 FPS; 8.721333-second container, 1280×720; full decode, source checks and two measured narration slots. This is procedural media, not diffusion footage.
- Encoder workload: three synthetic seconds / 90 frames / 1280×720 at 30 FPS. libx264 wall time 0.344 seconds; h264_amf 0.407 seconds. Both decoded and hashed. Includes startup; no sustained stream/game/HDR or unrelated render ETA claim.
- UI: no JavaScript exceptions. No horizontal overflow at 390px for Create, Platforms, History, Dashboard, Brand kit and Connections. Physical phone not paired.
- Browser testing found and fixed initial destination-selection loss and new-workflow shortcut routing. Capacity inputs remain aligned with the displayed calculation.
- Replay prepared a new pending exact owner action without executing. Owner review in the isolated synthetic workspace produced a new job with lineage. No OBS mutation, real microphone capture, public publication, calendar event creation or message sending.

Full synthetic proof: [device UI evidence](evidence/creator-control-0.7.0.json). Tests: `tests/test_control.py` plus the existing suite.

## Installed laptop state

Source code commit `9078e6550a578d7cb4df9c8f400d4bac0597f1c6` installed from an isolated 0.7.0 checkout on DTG. Hub healthy on loopback port 8765; default workspace inventory preserved; zero pending actions/active jobs at upgrade. Existing desktop Creator Hub shortcut points to this checkout. SQLite was backed up locally before upgrading. A missing local build backend was handled through pip’s isolated build process against official PyPI; core runtime dependencies remain empty and the existing optional OBS library remains available.

Actual packaged MCP process read live hub 0.7.0, enumerated 21 tools, and exposed no approval tool. This proves laptop stdio behavior, not ChatGPT mobile execution.

## Remaining acceptance boundaries

OBS WebSocket control remains unconfigured in the hub; the prior observed OBS server was disabled. Phone private HTTPS is unconfigured. Actual microphone/interface, Xbox capture/party chat, sync, BRB routing, representative load/network stability, channel ownership and final publication remain unverified. No SONARA services, source, deployments, credentials or repository protections changed. No merge or production deployment performed.
