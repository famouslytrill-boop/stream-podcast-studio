# Local recording to reviewed clips

Source toolkit v0.3.0. The installed ChatGPT plugin remains v0.1.0.

The added command uses Python 3.11+ and installed FFmpeg/ffprobe. It creates local video files only. It does not choose highlights, transcribe speech, create accounts, upload posts or start OBS.

1. Preserve the original MKV. Listen to it and note exact in/out seconds for up to three moments.
2. Copy `config/clips.example.json` to a private working manifest. Its example numbers are not real clip times. Set `source` to your file. Relative source paths are relative to the manifest.
3. Use `audio_stream: 0` for the first audio stream, `1` for the second, and so on. Choose a stream containing the intended finished mix. An isolated mic track will not automatically acquire game sound. Mix separate tracks in the editor first when needed.
4. Run the plan and inspect the proposed cuts. Keep the whole game frame with `fit`; use `center-crop` only after verifying that it preserves the action and essential text.
5. Confirm the actual context and content rights in the manifest. Then render into a **new** folder. The tool refuses existing folders and leaves source recordings untouched.
6. Optionally supply a corrected source-timeline SRT using the [caption workflow](CAPTION_EDITING.md). Then watch and listen to every export, verify text on your phone, and upload manually to a verified channel when ready.

From the repository root:

```powershell
python tools/clip_tools.py plan config/my-clips.json
python tools/clip_tools.py render config/my-clips.json outputs/session-001-clips
```

After an optional local package installation, the equivalent command is `emberbanter-clips`.

## Output and limits

- MP4, 1080×1920, 30 fps, H.264 video, stereo AAC at 48 kHz / 160 kbps. These are this toolkit's export choices, not a universal platform requirement.
- One to three cuts, each 0.25–180 seconds, inside the source's reported duration.
- Fit layout uses charcoal padding and preserves the whole picture. Center crop can remove the HUD; review it deliberately.
- Each output is probed for dimensions/duration and fully decoded for error detection. `clip-report.json` records results.
- One selected audio stream only. No automatic mix, loudness correction, transcription or content moderation. Reviewed SRT captions can optionally be burned in with a rebased SRT sidecar.
- Normal square-pixel source required. HDR, unusual channel layouts and mixed-track recordings may need preparation in an editor. No HDR tone mapping is supplied.
- Rendering times out after ten minutes per cut. A timeout is a failed render, not a reason to change the original recording.
- All files finish encoding in temporary staging before final export-folder creation. A filesystem error during final copying can leave an incomplete new folder; inspect it and choose another folder on retry.

Automated tests use synthetic test patterns and tones. They cover cut validation, output protection, review confirmations, both layouts, selected audio and source preservation. They are not tests of Dam's microphone, Xbox, OBS configuration or published channels.

The older `studio_tools.py` retains its 0.1.0 internal version and existing command behavior. Its process helper accepts an optional working directory for fixed local subtitle files. The source package and clip command are 0.3.0.
