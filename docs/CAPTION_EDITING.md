# Caption editing and local export

Source toolkit v0.3.0. This extends the original clip workflow with optional reviewed SRT captions. The installed ChatGPT plugin remains v0.1.0.

## From recording to captioned clip

1. Keep the original recording. Use a copy or project in your editor and select the intended finished audio mix.
2. In Shotcut, use the Subtitles panel's Speech to Text feature to prepare a draft. A model download may be needed. Correct actual words, names, slang, speaker meaning and timing.
3. Export a UTF-8 SRT on the **full source recording's timeline**. Preserve the original SRT; the clip tool creates separate rebased copies.
4. Copy `config/clips-captioned.example.json` into your private working area. Set the actual source, corrected SRT path and real cut points. Both paths are relative to the manifest, unless absolute.
5. Leave `captions.timebase` set to `source`. Confirm `captions.reviewed` only after checking the actual transcript and timing. The existing context/rights confirmations for the cuts also apply.
6. Run plan, then render into a new folder. Watch and listen to each final clip on the phone before publishing.

```powershell
python tools/clip_tools.py plan config/my-captioned-clips.json
python tools/clip_tools.py render config/my-captioned-clips.json outputs/session-001-captioned
```

Only add the captions object when you want captioned outputs. Existing manifests without it retain uncaptioned behavior. The example SRT text and times are synthetic placeholders.

## What the exporter now does

- Validates UTF-8 SRT, source duration, positive timing, unique indices and chronological non-overlapping cues.
- Carries only intersecting cues into each cut, clamps them to its boundaries and shifts their start to the clip timeline.
- Writes a per-clip SRT and burns fixed-styled captions into the vertical MP4 through FFmpeg/libass. It does not invent, transcribe or rewrite words.
- Preserves the original recording and caption source. It refuses existing output folders and unreviewed captions.
- Uses a 1080×1920 caption canvas, bone-colored Arial text with a dark outline and bottom/right margins. The layout is a starting design that still needs phone and game-HUD review. Font fallback can vary by computer.
- Keeps millisecond precision in the SRT copy; the ASS renderer rounds boundaries outward to centiseconds, a maximum timing expansion under 10 ms at each boundary.
- Counts long cues in the report so they can be split or shortened in the editor. A successful render does not prove the text is comfortable to read.

Limitations: SRT cues must be on the source timeline and non-overlapping. Basic bold/italic/underline tags are removed to give a consistent plain-text style. Other markup, ASS override braces/backslashes and control codes are rejected. Deliberately adjust any cue cut mid-sentence; temporal intersection alone does not preserve meaning. No word-by-word animation or automatic translation is supplied.

## Reproducible transcription benchmark

The optional `tools/transcription_benchmark.py` measures a trusted local whisper.cpp command against an actual reference transcript. It accepts a short local WAV, a local model with a trusted SHA256 digest, a text reference and a new output folder.

```powershell
python tools/transcription_benchmark.py --whisper-exe PATH_TO_TRUSTED_ENGINE --model PATH_TO_MODEL --model-sha256 TRUSTED_MODEL_DIGEST --audio PATH_TO_WAV --reference PATH_TO_REFERENCE --output outputs/transcription-trial
```

Add `--synthetic` for a deliberately synthesized test fixture. The command uses four CPU threads with GPU disabled, writes draft TXT/SRT plus a benchmark report, and preserves the input WAV. It never records or uploads. Inputs are limited to a WAV under 64 MB and ten minutes, and a reference under 100 KB.

The report measures run time divided by audio duration and normalized English word error rate. It counts insertions, deletions and substitutions; punctuation is ignored, number words are not converted, and error rate can exceed 100%. Engine startup is included. A clean synthetic voice is easier than real game/party audio; its result cannot certify Dam's microphone, normal speaking style, game names, speaker separation or real-world accuracy.

Use the actual on-device handoff for installed application paths and benchmark observations. Models and personal recordings belong outside source control. Public account connections and publishing remain separate operations.

## Primary implementation sources

- [Shotcut official downloads](https://shotcut.org/download/) and [release notes](https://shotcut.org/download/releasenotes/), checked November 16, 2026.
- [FFmpeg ASS filter](https://ffmpeg.org/ffmpeg-filters.html#ass) and [Aegisub ASS text/timing rules](https://aegisub.org/docs/latest/ass_tags/).
- [whisper.cpp CLI documentation](https://github.com/ggml-org/whisper.cpp/blob/master/examples/cli/README.md) and [model provenance](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md).
