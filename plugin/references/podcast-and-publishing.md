# Podcast production and publishing

Begin with a repeatable 30-45 minute pilot: one clear question, specific stories, natural conversation, one takeaway. A gaming stream recording needs editing to stand alone as audio; remove silent menus and unexplained visual references. No episode is recorded merely because a plan exists.

Draft a hook, three beats, guest follow-ups, fact links and a closing invitation. Record locally with headphones. Tell guests about recording, public distribution and clip reuse before capture. Guest invitations and posting require the owner's request; do not send them merely because this guide describes them.

Edit for understanding before noise processing. Preserve the original recording. Check room noise, breaths, interruptions and stereo centering. A loudness pass cannot fix clipped audio or poor mic placement. The export tool measures the first audio stream; multitrack mixes must be prepared deliberately in the editor.

For the default stereo MP3 delivery, this tool uses 48 kHz / 192 kbps, two-pass normalization targeting -16 LUFS and -1.5 dBTP, then re-measures the encoded file. It refuses nonfinite/silent measurements and output outside a +/-1 LU tolerance or above -1 dBTP. The extra peak margin is an engineering choice. Apple recommends around -16 LKFS +/-1 with true peak no higher than -1 dBFS; confirm destination requirements and listen to the final file. Mono exports use 128 kbps with the same chosen loudness target. This is not a platform acceptance certificate.

Read/clean a transcript before generating chapters, captions or quotes. Use only actual timestamps from supplied media or a trustworthy transcript. If timing is absent, mark clip suggestions as untimed. Don't invent words or imply the software transcribed a file when it did not. Automated local transcription is not installed by this package; use a supported available service/tool or arrange an optional local model separately.

## Release gate

- Confirm the real channel/feed owner, accurate title/description, explicit flag, music/game rights and guest consent.
- Use original or appropriately licensed music. Permission on a live platform need not cover podcast RSS or clips. Check the game's publisher policy and current platform policies when needed.
- Use a real final file, actual byte length/duration, stable unique GUID and stable HTTPS enclosure URL.
- The bundled RSS builder creates local XML only, supports Leisure / Video Games, and rejects example domains unless --draft is explicitly supplied. A production-category change needs verified taxonomy support.
- Public distribution needs public feed/media hosting, valid artwork, functioning HTTP HEAD/byte-range responses, correct enclosure MIME/length, and validation in the destination's dashboard. These external tests are not performed by the builder. A private code repository is not a public podcast host.
- The included badge is a plugin/channel asset; do not assume it meets a podcast platform's cover dimensions.
- Generating XML or release copy does not submit the show to Apple, Spotify, Twitch or YouTube.

Use the owner's chosen live platform first. Track eight actual sessions before adding complexity. A proposed cadence of one or two weekly sessions is a planning option; never announce or schedule dates before the owner confirms them. Store times with America/New_York and a full date; allow for daylight saving time.
