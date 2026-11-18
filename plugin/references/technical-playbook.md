Current prepared 0.8.0 extension: [persistent private OBS setup, diagnostics and owner rehearsal reports](rehearsal-readiness.md). Laptop upgrade/native acceptance pending while DTG is offline. Existing instructions below remain applicable where not extended.

# Streaming setup and acceptance

Use the existing gear first. Inventory OS/CPU/GPU/RAM, mic/interface models, Xbox model, headset/capture card and measured sustained upload. On the selected computer run the bundled doctor before recommending installs. Its missing GUI-app PATH result may need a normal installation-directory check.

## Baseline stack

| Technology | Purpose | Status in the plugin |
| --- | --- | --- |
| OBS Studio | Capture, mix, local recording and live encoding | Setup workflow and existing HTML scenes; requires device installation |
| Built-in obs-websocket | Optional local diagnostics | Authenticated loopback read-only client; no extra OBS plugin needed for OBS 28+ |
| Audacity | Manual podcast editing | Setup/edit workflow; no remote control integration claimed |
| FFmpeg + ffprobe | Media inspection and podcast exports | Executed by the bundled local Python tool when installed |
| Python 3.11+ | Local production tool | Core uses standard library; OBS client additionally uses websockets 16.0 |
| Git | Source history | Repository setup and versioned code |

Paid editors, capture cards, VST bundles and transcription model downloads are optional decisions. Install software from official sources or established package registries. Keep operating-system and license prompts visible; do not bypass protections. The Windows installer in the source repository has a plan mode and reports failures. Installing FFmpeg CLI does not necessarily install Audacity's separate optional FFmpeg import library.

## Picture and audio routing

For a compatible Xbox/PC, test official Xbox Remote Play in its own window, then OBS Window Capture. Verify the current Xbox support page for the actual model. Ethernet is a practical preference. A capture card is an alternative after a real Remote Play test. Native console broadcasting does not automatically add the PC interface microphone or OBS layouts.

Mic -> interface -> PC -> a single OBS audio input source. Capture application audio once. Avoid adding the same sound through both application capture and global desktop capture. Use headphones. A PC interface microphone does not automatically reach Xbox teammates; test a supported party-chat route or separate console headset. Confirm guests know their voices will be broadcast and recorded.

Start with the existing cautious Twitch profile: 1280x720 at 30 fps, H.264 CBR 3000 kbps, 2-second keyframes, 48 kHz AAC 160 kbps. Run OBS Auto-Configuration Wizard and check current platform guidance. Do not apply Twitch settings to YouTube without checking YouTube's separate guidance. Upload headroom of 1.5 times combined audio/video bitrate is this tool's planning rule, not a platform rule or a guarantee.

Use MKV for local OBS recording; remux a copy when an editor needs MP4. Check separate mic and game audio recording tracks deliberately. Keep global sources from leaking into BRB. Normal speech around -12 to -6 dBFS peaks is a working starting target, not a delivery loudness specification. Fix placement and input gain before suppression/compression/limiting.

## Device acceptance

1. Record five minutes of speech, laughter, gameplay and any guest voice.
2. Listen with headphones: centered voice, no distortion/echo/double capture, game below speech and usable sync.
3. Switch to BRB and verify all intended audio is silent in the saved file.
4. Inspect OBS Stats under representative movement/load. A single status snapshot cannot prove stable performance.
5. Review the recording on the phone. Run a deliberate live test only when authorized; Twitch streams are public.
6. Record exactly which confirmations and upload measurement passed. Unknown stays unknown.

Keep OBS WebSocket authentication enabled. The client connects only to 127.0.0.1, uses an environment password and sends GetVersion/GetStats/GetStreamStatus/GetRecordStatus. Do not open firewall/router ports or expose it to the internet. This account plugin has no always-on bridge to the owner's computer.
