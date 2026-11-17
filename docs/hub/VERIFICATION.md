# Creator hub verification

Scope: toolkit v0.4.0, account plugin source v0.3.0. Evidence collected on DTG and the Linux build executor. Synthetic fixtures were used throughout; no owner microphone/Xbox recording or OBS mutation was performed.

- Linux: **43 tests passed**. Includes the existing caption, clip and economics suite plus hub imports, media math, real exports, source preservation, HTTP authority, concurrency lock, caption order, malformed media, revision conflicts and one-use approval tests.
- DTG: **21 hub/math tests passed** on the actual Windows laptop using its existing Python virtual environment and FFmpeg.
- DTG Chrome: pairing, source import, real video playback, two cuts in a changed order, corrected captions, exact-action review, approval and completed real export passed. A fake browser microphone device also verified a captured WebM take, preservation after deliberately blocked import, and successful retry. No physical microphone access was requested.
- Service health: v0.4.0 responds on laptop loopback. Manifest and 192/512px PNG/SVG icon routes return 200. The Creator Hub desktop shortcut exists and launches the local service/browser.
- Packaging: local wheel builds without network/dependency downloads; includes the Python runtime, frontend and icon assets. Account plugin manifest, YAML/frontmatter and packaged runtime are checked separately; a successful account update does not prove tool availability in a particular host.

## Visual fidelity

The generated primary-screen concept was inspected at `/workspace/scratch/0253898cd723/generated_images/exec-0608a601-bb27-4eae-9b56-e2e075b929b0.png`. The final DTG Chrome screenshots were transferred back and inspected directly with the image viewer. Native desktop viewport: **1487×1058**; mobile emulation: **390×844**, with a full-page continuation capture. No horizontal mobile overflow was observed.

The cloud browser could not reach the executor's loopback service. The executor's local Chromium process was also unavailable under its process restrictions. Visual and interactive verification therefore used DTG's installed Chrome in a temporary headless profile, with DevTools inspection against only this local app. It did not reuse the owner's normal browser profile.

Compared: sidebar/navigation order, heading hierarchy, charcoal/orange/mint palette, media frame and film icon, inspector fields, sequence/caption regions, footer actions, panel spacing, keyboard focus and 44px touch controls. Fixed the desktop frame height, inspector type sizing and brand-kit alignment. The implementation was faithfully checked against the primary concept for this layout and workflow.

Above-the-fold copy matches the concept's requested wording. Intentional differences: actual connected state reads “Connected”; orange controls use dark lettering for contrast; native form controls preserve platform behavior; mobile stacks the editor into a readable vertical workflow. The simplified EB web glyph is code-native and does not replace the existing packaged channel badge. These differences are explicit; pixel-perfect identity with a generated raster mockup is not claimed. No material clipped content or horizontal overflow remained in the checked screens.

## Limits

Physical Android pairing, private HTTPS, actual mic/interface/Xbox/party audio, BRB silence, real upload stability, OBS authenticated mutation and platform publishing remain unverified or unconfigured. Offline shell caching is not an offline media worker. Output decode checks do not establish editorial quality, commercial rights or microphone quality. Current editor supports one source, one selected audio stream and cut sequencing; multitrack/keyframe/chroma-key composition remains a next extension.
