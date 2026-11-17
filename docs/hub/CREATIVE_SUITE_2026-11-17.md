# EmberBanter creative suite — v0.5.0

November 17, 2026, America/New_York. Dam selected **EmberBanter Studio** for the entire personal creator hub. Descriptor: **Music. Games. Stories.** Tagline: **Clock out. Queue up.** Earlier alternative names remain historical concepts.

## Delivered workflows

| Area | Working implementation | Boundary |
| --- | --- | --- |
| Dashboard | Five project types, real recent projects, actual installed-tool inventory, workflow entry points and an interactive command shell | Projects organize work; creating one does not create a DAW or game recording |
| Music | Up to eight imported stems; per-stem trim, gain, stereo balance and timeline offset; two-pass loudness processing; 24-bit stereo 48 kHz WAV, MP3, recipe, measurements and delivery ZIP | Level/balance mixing; no instrument hosting, spectral restoration, vocal tuning or subjective mastering claim |
| Composition | Deterministic original 1–8 bar MIDI sketch, four diatonic keys, BPM, chord/bass/drum tracks, notes JSON and guide WAV | MIDI carries notes; the guide is a simple synthesized tone. FLP generation and real FL Studio import acceptance remain separate |
| Music video | Song + artwork or footage; optional actual audio waveform, gentle artwork motion, video chroma key; landscape/vertical MP4 | Not a full multi-camera timeline or an automatically generated cinematic music video |
| Gaming / streaming / podcast | Existing reviewed cut sequence, captions, video/MP3 delivery, browser microphone recovery and bounded OBS recording/scene/mixer controls | Hardware capture, OBS live mutation and public distribution still require actual acceptance/connections |
| Text files | Real lyrics/script/notes files, readback and optimistic revisions; every save creates a new file | Scoped studio documents, not unrestricted OS file access |
| Studio shell | `help`, `status`, `apps`, `projects`, `project`, `files`, `new`, `read`, `write`, `workflows`, `check`, `open`, `run` | A studio command language. Arbitrary OS commands, executable paths and filter strings are rejected |
| Application launch | Verified installed FL Studio, OBS, Blender, Shotcut and VS Code on DTG; reviewed argument-free launches | Discovery passed; app launch is unit tested with a process mock. Opening an editor is not proof of an edit |
| Automation | Fixed planner → executor → verifier roles, exact proposals, actual stage progress and output receipts | No hosted model, always-on agent or autonomous source rewrite is connected |
| Engineering | Local tool inventory, Python syntax/manifest/recipe checks, regenerated diagnostic report | Read the report's `passed` field. Completing a check job does not mean every check passed |
| Brand kit | Editable layouts and rendered production templates served/downloaded by the app | No claimed handle/domain/trademark ownership or platform-account setup |

The existing loopback service, host/origin checks, cookie/CSRF authority, owner-only approval, one-use three-minute proposals, one worker, four-job queue bound, protected imports, checksum receipts and restart-without-replay remain in force. A workflow executes its approved fixed steps without asking again at every step. No agent endpoint can approve itself.

## Shell and API contract

Example studio commands:

```text
help
project music After-work session
new Verse and hook
files
read DISCOVERED_DOCUMENT_ID
write DISCOVERED_DOCUMENT_ID CURRENT_REVISION New text for the next revision
apps
open flstudio
workflows
check
run midi {"title":"Ember sketch","key":"A minor","bpm":100,"bars":4}
```

Use real IDs/revisions from `files`; placeholders are not executable values. `open`, `check` and `run` prepare a review. Actual file edits return the saved revision; previous files remain preserved. Outside modifications to the current document are detected rather than silently overwritten.

Local MCP has **12 tools**: `studio_status`, `studio_library`, `studio_session_save`, `studio_propose`, `studio_job_status`, `studio_media_math`, `studio_shell`, `studio_project_save`, `studio_document_read`, `studio_document_write`, `studio_workflows` and `studio_import`. Import streams an explicitly selected local path from the executing computer to the running loopback service. The browser cannot supply arbitrary OS paths.

HTTP additions are `/api/projects`, `/api/documents`, `/api/document?id=…`, `/api/shell` and `/api/brand-kit`, behind the existing authority checks. The stdio configuration/runtime is included in account plugin v0.4.0. A saved plugin does not create an executable tool connection in ChatGPT mobile. A private HTTPS phone route and a hosted authenticated device bridge are separate unfinished integrations.

## Algorithms and measured evidence

Stem gain is `10^(gain_dB/20)`. Left/right balance factors are `1-max(0,p)` and `1+min(0,p)`, for `p` in [-1,1]. Trimmed sources are resampled to 48 kHz, delayed by the supplied offset, summed in floating point and loudness-measured before two-pass delivery processing. This is stereo balance, not constant-power spatial panning. Silence/nonfinite loudness fails through the existing normalization checks.

Mix length is `max(offset_i + end_i - start_i)`, capped at one hour. Music-video length is `audio_end - audio_start`, capped at ten minutes. Short visual material requires explicit looping. Waveforms use the chosen audio samples; they are not random decorative meters. Chroma-key settings are validated numbers with fixed supported colors. Source checksums are verified before and after processing; files are decoded before a successful receipt.

MIDI uses 480 ticks per quarter note and 4/4 bars. Beat seconds are `60/BPM`; bar seconds are `240/BPM`. Notes come from a fixed diatonic progression and event ordering; no learned-composition model or commercial-song imitation is involved. This creates a starting sketch, not a completed record.

Linux: **55 tests passed**. DTG Windows: **55 tests passed**. Actual Windows Chrome UI: created three project types; created/read/wrote a real document revision; imported two audio stems and artwork; approved and completed a real mix, MIDI sketch, music video and engineering report; downloaded the 3,422,773-byte brand ZIP. No browser exceptions or horizontal overflow at 390×844 across eight checked views. Studio's existing sequence has prior separate mobile evidence. A preview-selection bug found by this run was fixed and the workflow rerun successfully.

Synthetic fixtures only. No physical microphone, Xbox, party audio, public stream or upload was used. Visual inspection compared the desktop implementation with the generated dashboard direction: navigation order, headings, split project/shell workspace, palette, panel geometry and tool rows. Actual connected inventory replaces mockup logos with readable monograms; real projects replace the empty-state example. Desktop and phone layout are intentionally responsive, not a pixel-perfect raster copy.

## Brand package

| Token / master | Specification |
| --- | --- |
| Charcoal / surface | #101216 / #191D22 |
| Ember / mint / bone | #FF6A3D / #8EF2CE / #F4F1E8 |
| Typography | Bold system sans; Segoe UI/system UI body; monospace command/timecode text |
| Scenes | Starting, BRB and Ending: 1920×1080 JPEG + editable SVG |
| Overlays | Transparent lower third 1920×1080; clip frame 1080×1920; PNG + SVG |
| Podcast | 3000×3000 PNG + SVG; “The Cooldown” is editable series-template wording |
| Channel / thumbnail | 2560×1440 banner; 1280×720 thumbnail template; JPEG + SVG |
| Motion / sound | Local OBS browser scene; original synthesized E4–G4–B4 WAV cue; no autoplay |

The existing EB badge is retained and used in the app, icons and templates. Its original is a raster master; embedding it in an editable SVG does not turn the badge into vector artwork. Background imagery is generated; typography/layouts and color values are code-authored. `tools/build_brand.py` rebuilds editable layouts and the sound cue; rendered derivatives use the existing build environment's Sharp and system fonts. Sharp is not required to run the laptop hub. Keep linked badge/background files beside SVG sources when editing.

## Research and engineering choices

| Technology | Primary evidence | Decision |
| --- | --- | --- |
| FFmpeg | [Official filters](https://ffmpeg.org/ffmpeg-filters.html): amix, adelay, pan, loudnorm, showwaves, zoompan and chromakey | Use installed FFmpeg for deterministic new outputs and full decoding. This release exercises real mixing/composition. FFmpeg build licensing depends on enabled components; no binary is redistributed here |
| FL Studio | [Audio/MIDI exports](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fformats_save_export.htm) distinguishes audio, note data and native project saving | Reuse Dam's installed DAW with stem/MIDI interchange. Do not label it open source or claim full native editing |
| Blender | [License](https://www.blender.org/about/license/), [command-line documentation](https://docs.blender.org/manual/en/latest/advanced/command_line/) | Installed open-source animation tool; reviewed launcher now. A verified background-render adapter is a next integration, not delivered by discovery |
| Audacity | [Official scripting manual](https://manual.audacityteam.org/man/scripting.html) documents named-pipe control and its security limits | Do not expose or enable its script pipe as a web service. Audacity was not detected in checked install paths. Current automated audio work uses FFmpeg |
| MCP | [Versioned tools specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) | Keep the tested versioned stdio contract; explicit 12-tool inventory, narrow inputs and separate review |
| SONARA | Read-only source inspection at `1693036c4e50b6b4d15db5b4943752cac5552b6d`; paths listed in ARCHITECTURE.md | Adapt governed workflows, tokens, provenance receipts and formula discipline. No deployment code or credentials copied; SONARA unchanged |

The Blender license and command-line search results were available from official indexed sources; a prior direct manual fetch failed. They establish an integration direction, not tested automation. Existing versions on DTG were checked independently.

## Next engineering sequence

1. Private HTTPS pairing and physical Android acceptance, followed by microphone/interface/Xbox/party routing and sync rehearsal.
2. A bounded Blender adapter: fixed packaged scene/script, immutable asset inputs, declared render budget, separate process exit handling, frame/decode receipts. No arbitrary Python uploads.
3. DAW interchange round trip: import MIDI/stems in Dam's actual FL Studio, retain native FLP, render through its supported workflow and compare duration/channel evidence.
4. Isolated engineering worktree jobs: explicit repository/commit scope, patch artifacts, relevant local checks, failure logs and independent review. No unattended merge/deploy or self-approved patch application. Current engineering jobs only inspect/rebuild diagnostics.
5. Hosted device identity/revocation, then provider OAuth/private drafts and separate exact-publication review. Add model providers only with explicit limits and cost approval; current workflows make zero model/API-provider calls.

These are dependency-ordered development tasks, not a claim that the complete creator operating system is finished.
