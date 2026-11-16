# Caption editing milestone — November 16, 2026

Observed on DTG, America/New_York. Source toolkit v0.3.0; installed ChatGPT plugin remains v0.1.0.

## Prepared and launched

- Official Shotcut **26.9.27** portable build, extracted under `%LOCALAPPDATA%/EmberBanter/apps/shotcut-26.9.27/Shotcut/`.
- Package SHA256 matched the official release asset digest: `1f8c50ce7b125a2f0dcb60777b358e86baf03b8515982612b6adae10a83d93a5`.
- The executable's version and the running Shotcut process path were verified. The normal WinGet request was cancelled after it did not complete while an elevation prompt was present; no system-wide installation success is claimed.
- Added **Edit Clips** to the existing **EmberBanter Studio** desktop folder. It launches the verified portable copy without recording, exporting or publishing.
- Prepared the official `ggml-tiny.en.bin` model under `%LOCALAPPDATA%/EmberBanter/models/`, outside Git. Its SHA256 matched model-host metadata and its SHA1 matched the whisper.cpp model table.

Model SHA256: `921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f`.

## Actual transcription observation

The fixture used Windows' Microsoft David Desktop text-to-speech output written directly to a WAV. No microphone was recorded. It contained a newly written neutral studio-test passage.

| Measure | Observed result |
| --- | ---: |
| Speech duration | 16.596735 seconds |
| Engine run time, including startup | 3.394 seconds |
| Run time / speech duration | 0.2045 |
| Normalized reference words | 38 |
| Normalized word edits | 0 |
| Draft SRT cues | 3 |

Mode: the Shotcut-bundled whisper.cpp CLI, tiny English model, four CPU threads, GPU inference disabled. GPU performance was not benchmarked. Punctuation was ignored by the word comparison; number words were not normalized. These numbers describe one clean synthetic sample and do not estimate real microphone/game/party-chat accuracy or a guaranteed production speed.

Benchmark files and the source fixture remain in the ignored `device-private/caption-benchmark-20261116/` directory. They are engineering evidence, not a released episode or gameplay recording.

## Caption export and regression verification

All **15 tests passed** on Linux/Python 3.12.14 in **5.621 seconds**, and on DTG/Windows/Python 3.14.4 in **5.643 seconds**. They include actual FFmpeg encodes/decodes and pixel checks that distinguish caption-visible frames from uncaptioned padding.

Coverage includes source preservation, cut-relative SRT timing, clipped cue boundaries, malformed/overlapping cues, unsupported control markup, explicit audio-stream choice, both layouts, review gates, output protection and word-error arithmetic.

An end-to-end synthetic demonstration then used the actual model SRT to produce a **16.6-second, 1080×1920 captioned MP4**, a rebased SRT and a successful full decode. It contains three long cues, which the report flags for readability review. A **Synthetic Caption Demo** desktop shortcut points to that local engineering sample. Listening and phone readability review remain pending.

That demonstration exposed a real Windows issue: PowerShell's UTF-8 configuration output included a BOM that the JSON reader rejected. The reader now accepts UTF-8 with or without this marker, and the suite includes a regression check. The same PowerShell-generated manifest then rendered successfully.

## Current workflow

Use [CAPTION_EDITING.md](CAPTION_EDITING.md) for corrected SRT inputs and [CLIP_WORKFLOW.md](CLIP_WORKFLOW.md) for reviewed cuts. The clip exporter burns supplied reviewed captions; transcription is a separate draft-producing command. It does not silently accept model output as production-ready captions.

## Still pending

The actual external microphone/interface, Xbox capture, party routing, BRB silence, network load and five-minute rehearsal are unverified. The last endpoint inventory found only the laptop microphone array and speakers. No public broadcast, account enrollment, published clip or music import occurred in this milestone.

Next physical step: connect the intended mic/interface and headphones to DTG, then make the five-minute rehearsal described in the saved research plan.
