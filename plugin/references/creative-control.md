# Creator control — toolkit 0.7.0 / plugin 0.6.0

November 17, 2026, America/New_York. This milestone preserves EmberBanter Studio, the existing badge/palette and **Music. Games. Stories.** Public brand categories are now **Gaming / Streaming / Podcasts**. Editing, music production and music videos remain software capabilities, not brand-kit category labels.

## Implemented contracts

| Path | Behavior and evidence boundary |
| --- | --- |
| Create → Narration | Installed Windows System.Speech voices only. Reviewed plain text, 1–5,000 characters, pace −2…2; private 24 kHz mono WAV plus measured −19 LUFS mono MP3. Both decoded, duration checked, hashes saved. No voice cloning, SSML or remote fallback. Installed language availability is reported rather than invented. |
| Create → Storyboard | 1–8 saved scenes; title, up to 400 text characters, imported image/video or brand title card. 2–60 seconds per scene, max four minutes; 0 uses measured narration plus padding. Integer-frame 30 FPS timeline, landscape 1280×720 or vertical 1080×1920; optional gentle still zoom and fades. Footage audio is replaced by narration/silence. Sources pinned and checked; film decoded, duration/dimensions checked; script, shot list, recipe, receipt and ZIP. This is a procedural short-film engine, not a diffusion video model or full 3D editor. |
| Storyboard documents | Existing immutable UTF-8 revision files and optimistic concurrency. A changed saved revision invalidates a pending proposal. Media and narration availability are revalidated. |
| Platforms | Allowlisted official YouTube/Twitch/Spotify/TikTok/Apple portals. Manual browser handoff; no claimed OAuth, upload, revenue, chat or channel ownership connection. |
| Platform handoff | Reviewed title/topic/description/source links → script scaffold, message draft, metadata, source list, checklist, optional RFC 5545 calendar reminder and ZIP. Timezone required; UTC conversion, UTF-8 octet folding and escaped calendar values. Zero provider API calls/messages/calendar events. The owner imports the reminder file; it does not schedule a platform broadcast. |
| Capacity planner | Explicit video/audio kbps per outbound stream; decimal Mbps sum and MiB payload. Internal conservative 1.5× network headroom, distinct from provider requirements. Missing measured upload stays unknown. Does not configure multistreaming or infer HDR. |
| Encoder check | Owner confirms no live recording/stream. When OBS credentials exist, active OBS production blocks the check. Three-second synthetic 720p30 libx264 plus optional advertised h264_amf attempt; actual elapsed wall time, hashes, dimensions/duration and full decode. Failed GPU attempt remains explicit. Whole-job FPS includes startup and is not a game, real-time stability or HDR acceptance test. |
| History | Persisted job pages of 50 beyond the old 100-item state window. Error-specific repair guidance. Eligible finished file jobs can prepare a new one-use, expiring, exact owner proposal with replay lineage. Changed inputs/capabilities invalidate an exact replay. OBS actions, capture imports and launches never replay. No automatic restart/retry of ambiguous side effects. |
| Local MCP | 21 tools: prior 13 plus installed voices, platforms, paged history, replay proposal, storyboard save/read, capacity plan and hardware evidence. Job status now works by actual persisted job ID. No approval or public go-live tool. A packaged stdio server still requires a capable local host. |

All heavy workflows retain one worker, at most four queued/running jobs, new output directories, private local originals and fresh owner review. Browser drafts and external apps can remain open independently. Two browser tabs do not create two workers or guarantee account API compatibility.

## SONARA reuse — read-only, pinned

Inspected `famouslytrill-boop/sonara-os` main at `1693036c4e50b6b4d15db5b4943752cac5552b6d`.

| Main source | Concrete adaptation here |
| --- | --- |
| `lib/sonara-agent-skill-strategies.cjs` | Bounded planner → exact review → worker → independent verifier. Narrow role/tool permissions, no agent approval, no automatic retry of external side effects. Role contracts describe implemented stages, not a running model swarm. |
| `lib/sonara-formula-library.cjs` | Explicit units and honest missing values. Direct stream Mbps = Σ(video kbps + audio kbps)/1,000; frame interval = 1,000/FPS ms. Synthetic benchmark measurements cannot silently become unrelated render ETAs. |
| `lib/sonara-creative-simulation-kernel.cjs` | Storyboard uses cumulative integer start/end frames; each scene has ceil(seconds × 30) frames and the total is their sum. Actual speech duration must fit its slot before promotion. |
| `.ai/shared/DESIGN_CONTRACT.md` | Readable system typography, consistent 12/16px surfaces, touch layouts and explicit restrained color usage. Existing identity remains intact. |
| Media-kernel architecture | Validation, source provenance, bounded workers, output verification and owner promotion gates. A pure planning module is not represented as a deployed service. |

No SONARA source, secrets, database, ruleset, deployment or production service was changed. User-owned SONARA source is not relabeled as open-source software. Reuse remains in this private repository.

## Service and engine boundaries

FFmpeg/ffprobe provide real media processing. System.Speech provides real installed local voices. OBS remains an independent app with reviewed local control only after authenticated WebSocket setup. Shotcut, Audacity, FL Studio and Blender discovery/launch is separate from native project editing. Existing transcription benchmark remains a tested fixture, not unattended production ASR.

Connected ChatGPT plugins for Higgsfield/fal may offer generation through their own supported actions; no paid generation was invoked and no hub adapter/account/credit check is implied. Runway/HeyGen/Metricool and other catalog options were discovery candidates, not installed or authenticated integrations. A future provider adapter must record input hashes, model/version, consent/rights, cost cap, request ID, accepted state and output verification. Reconcile ambiguous delivery before retrying. Local idempotency keys cannot guarantee exactly-once behavior at an external service.

## Required next acceptance

The useful next real-world step remains a private rehearsal with the actual microphone/interface/Xbox path. Confirm clean audio, one copy of each source, intentional BRB routing, picture/sound sync and representative OBS Stats. Measure upload with the real network. Account eligibility, public delivery, phone HTTPS pairing and sustained game+stream performance require their own evidence. No public broadcast or platform message is part of this milestone.
