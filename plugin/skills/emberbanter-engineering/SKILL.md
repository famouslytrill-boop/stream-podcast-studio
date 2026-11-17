---
name: emberbanter-engineering
description: "Use for EmberBanter source repository work, installing production software, diagnosing local dependencies, executing bundled tools, testing the package or reading OBS status."
---

# Studio engineering

Read [brand/state](../../references/brand-and-state.md), [technical playbook](../../references/technical-playbook.md) and [command reference](../../references/local-commands.md).

Core tools are [studio_tools.py](scripts/studio_tools.py), [clip_tools.py](scripts/clip_tools.py), [captions.py](scripts/captions.py) and [transcription_benchmark.py](scripts/transcription_benchmark.py), copied from the verified v0.3.0 source toolkit. Resolve real local paths and invoke with Python 3.11+. Core commands use the standard library; media operations need FFmpeg/ffprobe, OBS diagnostics require websockets==16.0, and transcription needs a separately verified local whisper.cpp binary/model. Do not assume source-repository examples exist in the installed plugin; equivalent [examples](../../assets/examples/live-profile.example.json) are included.

Use doctor first and identify the executing machine. Follow existing repository AGENTS.md, inspect Git state and protect unrelated edits. Keep this source in its own private repository. Never reuse SONARA deployment credentials or change SONARA systems.

The source repository's Windows script prepares/installs OBS, Audacity, FFmpeg, Git and Python through WinGet and installs this local CLI. Verify the exact package ID and on-device install result. Script availability is not proof of execution. If the PC is offline, complete code/package work and report device installation pending.

Preflight accepts explicit operator confirmations and a real upload measurement. READY_FOR_MANUAL_TEST means only those supplied checks passed; it does not start a stream or prove hardware acceptance. RSS generation creates local XML. Audio processing writes new outputs. No CLI command publishes or goes live.

OBS status is an authenticated loopback-only snapshot. Set EMBERBANTER_OBS_PASSWORD privately on the executing device; never request it in chat or store it in Git. The client sends only GetVersion, GetStats, GetStreamStatus and GetRecordStatus. Do not weaken WebSocket authentication or expose ports.

Test meaningful failure cases and real FFmpeg exports as appropriate. Clips require reviewed context/rights and corrected captions, preserve the source and use a new output folder. The benchmark measures supplied local speech; a synthetic speech pass is not real microphone accuracy. A simulated OBS pass is protocol coverage, not a test of the owner's live OBS. Before completing repository work, validate the archive, commit source and push to the verified private remote. If remote authentication is blocked, retain a durable source checkpoint and report that boundary accurately.


For the personal recording/editing control hub, use [creator hub](../emberbanter-creator-hub/SKILL.md). Legacy studio_tools.py remains read-only for OBS; the separate hub supports reviewed recording/scene/mixer writes. Local stdio tools and paired-phone PWA access require actual runtime connections.

For deterministic studio checks and the interactive shell, read [creative-suite contracts](../../references/creative-suite.md). Fixed local roles are planner, executor and verifier. The current engineering job inspects syntax/manifests/tools and rebuilds a report; it cannot apply patches, merge or deploy. If the user asks for further source engineering, work in the verified repository using ordinary scoped engineering tools, preserve unrelated edits and report actual checks. Do not run arbitrary OS text through studio_shell or treat the host plugin as an always-on engineering runtime.
