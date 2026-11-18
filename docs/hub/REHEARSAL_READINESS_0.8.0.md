# Rehearsal readiness — source toolkit 0.8.0 / plugin 0.7.0

November 17, 2026, America/New_York. Based on verified main `7d8ea6eb547517dfc9554c5998705b5f4ee330be`, which merged prior PR #5 and has the same source tree as the preceding milestone. DTG is offline during this pass. **0.8.0 is prepared source; it has not been installed or accepted on the laptop.** Last verified laptop installation remains 0.7.0.

## Connection setup

The hub supports a stored, user-scoped Windows DPAPI credential and a configurable numeric OBS port. The host is always `127.0.0.1`; remote URLs, public listeners, unauthenticated servers and public stream-start requests are not accepted by this adapter.

On Windows, from the new checkout with its intended Python environment:

```powershell
python -m unittest tests.test_setup -v
python -m tools.connect_obs --status
python -m tools.connect_obs --from-obs
```

`--from-obs` reads only the existing standard OBS WebSocket settings on the current Windows account. It requires an enabled server and password authentication, then performs authenticated GetVersion/GetRecordStatus/GetStreamStatus reads before saving. It never enables the server, changes its settings, opens a firewall port or starts recording/streaming. The last device observation had its server disabled; its current state is unknown while offline. Configure OBS and restrict its access locally before importing.

Alternatively, enter the current password in a private prompt:

```powershell
python -m tools.connect_obs --prompt --port 4455
```

Use the actual existing port. There is no password argument and no browser/agent credential-write endpoint. `--status` reports configuration metadata only, not an authenticated connection check. The PowerShell launcher also supports `-SaveOBSConnection` or `-UseExistingOBS`. The original `-ConnectOBS` process-environment path is retained.

The secret is encrypted with Windows CryptProtectData using user scope, no LOCAL_MACHINE flag and no prompt flow. The encrypted envelope is decrypted and checked before committing a profile. Rotating it writes a fresh credential file and atomically replaces settings; a failed update preserves the prior profile. Shared connection settings are locked across writers and preserve the capture-folder configuration. Credentials stay outside Git and HTTP responses. Software already running as the same Windows user is not isolated by this mechanism; restoring on another account/computer may require reconnecting the credential.

Persistent profiles are read when needed, so the normal hub can detect a new profile without an application restart. An already-running hub’s legacy environment password takes precedence; close that legacy launch and use the normal shortcut to switch to the stored profile. Existing recording-folder changes still require restarting the hub to load that folder.

OBS proposals pin a non-secret connection revision. Changing the profile/port invalidates an old approval and is checked again before connecting in the worker. Interrupted sends and acknowledgements are scrubbed, reported as uncertain, and never automatically retried. OBS actions remain excluded from history replay.

The launcher now refuses to silently reuse a different hub version or another service. It starts a new service only after a definite connection-refused result; timeouts do not trigger duplicate servers. It bypasses inherited HTTP proxies for its loopback health check. Let old jobs finish and close the older hub before reopening the new shortcut. No automatic stop or interruption is introduced.

## Connections dashboard

The new setup panel checks this executing host, not an inferred online laptop. It reports:

- Actual FFmpeg/ffprobe availability and optional OBS client dependency.
- Authenticated local OBS status, or an actionable missing-profile/authentication/connection error.
- Actual recording/stream activity and read-time FPS/frame counters when connected.
- Configured, unavailable or missing capture folder.
- Private phone origin configuration, with physical device verification still unknown.
- Manual-only platform handoffs and any prior owner-reported rehearsal.

A missing or non-boolean OBS activity state fails closed; it is never interpreted as idle. An acknowledged mutation with missing follow-up state is reported as uncertain and not retried. A zero or absent frame denominator remains unknown. OBS frame percentages are cumulative counters at the check, not a measurement over a complete rehearsal. No successful health check turns into automatic hardware or public-delivery approval.

A saved capture folder that disappears no longer prevents the entire hub from opening. Its setting is retained, imports stay unavailable and other tools can still run. An invalid explicitly supplied folder still fails validation; no folder is silently substituted.

Download Setup Report produces redacted JSON. It contains no OBS password, pairing key, credential filename or local capture path. Run the check again after correcting a specific cause rather than repeatedly dispatching an ambiguous OBS action.

## Owner rehearsal records

Record locally, stop, import the intended source and watch/listen. In Connections → Your rehearsal observations, choose a gaming or podcast recording and explicitly record each applicable check. No checkbox starts checked. The final personal-review confirmation is required.

Gaming checks cover clear speech, duplicate audio, saved-recording review, participant consent, rights/private details, game picture/sound, sync, intended BRB routing and representative OBS Stats. Podcast uses the five common audio/consent/rights checks. A measured upload value is optional and labeled owner supplied; an empty value is not zero.

Reports are append-only, timestamped and linked to an imported recording/hash. The source checksum is checked when saving. An unchecked item is preserved as unresolved. All checks yield **owner_reported_pass**, explicitly not automatic hardware, physical phone or public-delivery verification. Prior reports remain intact. Starting a new source/type clears the prior review selections.

POST `/api/rehearsals` requires the paired owner browser and CSRF protection. Bearer agent credentials cannot submit it. The two new local MCP tools, `studio_readiness` and `studio_rehearsals`, are read-only. There is no rehearsal-save or approval tool. New setup tools explain the required upgrade when connected to an older hub rather than claiming a missing route worked.

## Verification boundary

The source tests cover credential envelopes/metadata/rotation/rollback, concurrent settings writers, symlink and input rejection, private-port bounds, OBS challenge authentication, bad replies, uncertain sends, reconfiguration invalidating actions, unavailable-folder recovery, append-only reports, source integrity, unknown measurements and owner/agent authorization.

A real TCP WebSocket fixture exercises challenge authentication, all status reads and one owner-reviewed StopRecord against a synthetic protocol server. It does not control the owner’s OBS. DOM event handlers are exercised against an actual isolated HTTP server, covering initially unchecked forms, report attention/pass states, reset on source/type changes, escaping notes, downloads and denied writes. This is functional coverage, not a rendered-browser/mobile-layout check.

Native Windows DPAPI acceptance and real Windows speech are skipped on the Linux executor. A Chromium renderer could not start because the environment denies its process-singleton socket; DTG is also offline. The new panel’s rendered desktop/phone checks and Windows installation remain pending. Existing 0.7.0 browser and Windows evidence is historical, not new 0.8.0 acceptance.

Reproduce the optional DOM checks with `npm ci --prefix tests/ui`, then `python tests/ui/run_setup_dom.py`. Node requirements are pinned in `tests/ui/package.json`; Node/JSDOM are test-only and are not required by the hub runtime. The harness uses its own temporary media/workspace and clears inherited OBS credentials.

GitHub Actions runs the media and hub suite on Linux and the OBS connection tests, including the native DPAPI round trip, on a Windows runner. Both jobs install the package and check its entry points and setup assets. Hosted runner results cover synthetic inputs. The OBS rehearsal, media routing and phone layout still require the owner's devices.

This repository builds a local desktop hub. `vercel.json` disables automatic Git deployments for this repository. A separately scoped public site can have its own project and deployment configuration.

## Primary technical references

- Microsoft CryptProtectData: https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
- Microsoft CryptUnprotectData: https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata
- Official obs-websocket protocol: https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
- Official OBS settings keys: https://github.com/obsproject/obs-websocket/blob/master/src/Config.cpp

EmberBanter, its badge/colors and **Music. Games. Stories.** remain unchanged. Public categories remain **Gaming / Streaming / Podcasts**. No SONARA services, repository protections, production deployment, public broadcast, upload, calendar scheduling or messaging action was performed.
