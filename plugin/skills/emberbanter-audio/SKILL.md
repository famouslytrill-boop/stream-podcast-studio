---
name: emberbanter-audio
description: "Use for EmberBanter microphone noise, gain, echo, clipping, loudness, podcast MP3 exports, stem mixing, MIDI sketches, music editing, audio inspection or reviewing recorded voice quality."
---

# Audio production

Read [technical playbook](../../references/technical-playbook.md), [podcast/audio guidance](../../references/podcast-and-publishing.md) and [local commands](../../references/local-commands.md). Work on an explicitly supplied local recording or selected device. Fix mic placement, room noise and gain before recommending an effects chain.

Preserve the original. Ask for missing file bytes only if available connectors cannot retrieve them. Do not upload media to another service without authorization. Check installed FFmpeg/ffprobe before execution; tool availability in a cloud environment says nothing about the owner's PC.

Run the bundled audio-analyze command. Default analysis covers at most 600 seconds of the first audio stream; label this scope or use --full for a complete first-stream analysis. Silent/nonfinite results fail. Loudness measurement does not establish intelligibility, clipping repair, sync or a good multitrack mix.

For an authorized podcast export, create a new MP3 with the bundled audio-export command. Default: stereo, 48 kHz/192 kbps, two-pass -16 LUFS and -1.5 dBTP target with post-encoding checks. Mono is an explicit option. The source and existing output files are preserved. Treat normalization as delivery processing; don't call it mastering or restoration.

Report actual integrated loudness, true peak, sample/channel format, analyzed scope and saved output. Listen to a representative full production review before declaring release-ready; if listening is unavailable, say so. Never manufacture a sonic judgment from the filename or numeric level alone.


For the v0.5 music mixer or MIDI sketches, read [creative-suite contracts](../../references/creative-suite.md). Discover the executing laptop and real imported stems. Preserve its exact trim, offset, gain and stereo-balance settings; require source-content and permissions review. Target loudness and a decode receipt do not establish mastering quality. MIDI carries note data and its guide tone is not a finished instrument production. Do not claim FLP creation or actual DAW edits from a launcher or MIDI export.

For podcast/video episode assembly, read [broadcast workflows](../../references/broadcast-workflows.md). Use an episode proposal with reviewed source IDs, track choices, segment bounds/order, final-timeline captions and optional fixed voice processing. Audacity 4.0.2 portable was installed/launched on DTG with verified official archive checksum and valid executable signature; no native Audacity editing or scripting API acceptance is established.
