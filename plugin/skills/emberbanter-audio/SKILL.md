---
name: emberbanter-audio
description: "Use for EmberBanter microphone noise, gain, echo, clipping, loudness, podcast MP3 exports, audio inspection or reviewing recorded voice quality."
---

# Audio production

Read [technical playbook](../../references/technical-playbook.md), [podcast/audio guidance](../../references/podcast-and-publishing.md) and [local commands](../../references/local-commands.md). Work on an explicitly supplied local recording or selected device. Fix mic placement, room noise and gain before recommending an effects chain.

Preserve the original. Ask for missing file bytes only if available connectors cannot retrieve them. Do not upload media to another service without authorization. Check installed FFmpeg/ffprobe before execution; tool availability in a cloud environment says nothing about the owner's PC.

Run the bundled audio-analyze command. Default analysis covers at most 600 seconds of the first audio stream; label this scope or use --full for a complete first-stream analysis. Silent/nonfinite results fail. Loudness measurement does not establish intelligibility, clipping repair, sync or a good multitrack mix.

For an authorized podcast export, create a new MP3 with the bundled audio-export command. Default: stereo, 48 kHz/192 kbps, two-pass -16 LUFS and -1.5 dBTP target with post-encoding checks. Mono is an explicit option. The source and existing output files are preserved. Treat normalization as delivery processing; don't call it mastering or restoration.

Report actual integrated loudness, true peak, sample/channel format, analyzed scope and saved output. Listen to a representative full production review before declaring release-ready; if listening is unavailable, say so. Never manufacture a sonic judgment from the filename or numeric level alone.

