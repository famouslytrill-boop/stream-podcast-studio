# EmberBanter plugin 0.2.0 source checkpoint

Prepared November 16, 2026, America/New_York, on the existing private production-loop branch. This checkpoint extends the v0.3.0 local media toolkit with the owned plugin's full source under `plugin/`. Toolkit and plugin versions are independent.

The previous plugin routed eight production workflows but lacked dedicated economics and brand-development workflows and still bundled older core tooling. This revision adds Growth and Economics and Brand Lab, a deterministic local scenario/rubric calculator, dated primary-source research, a scripted live-show structure, an eight-session exploratory opening test, five exact brand palettes and a responsive concept preview. Reviewed caption/clip helpers now match the existing v0.3.0 toolkit byte-for-byte.

The current EmberBanter badge, active scenes, plugin identity, interface and default prompts are preserved. Alternative names are concepts; handle/domain/trademark availability remains unverified. No monetization account, sponsor agreement, public schedule, publishing action or device acceptance is implied.

Validation: 22 tests passed with zero skips in this Linux executor, including real synthetic FFmpeg caption/clip exports, selected audio, source preservation and seven calculator tests. Ten skill frontmatters, JSON, local Markdown references, manifests, direct CLI imports and helper parity also passed. Independent read-only workflow forward testing covered missing analytics, unsupported name-availability claims and aggregate RPM double-counting; its missing-target finding was fixed and regression-tested. The ZIP uses timestamp clamping for retained archive assets dated before 1980.

DTG was offline during this pass. Prior synthetic Windows results remain historical evidence; actual mic/interface routing, Xbox/party capture, BRB isolation, upload stability and listening review remain pending. No new Windows test or live stream was performed. PR #1 remains a draft; no merge or deployment is part of this checkpoint.

To run the financial checks from repository root:

```bash
python -m unittest discover -s tests -p test_strategy.py
python plugin/skills/emberbanter-growth-economics/scripts/studio_strategy.py economics plugin/assets/examples/economics.example.json
```

The example is hypothetical, not channel income or a quoted platform payout. Missing receipt/cost inputs remain unknown. A missing optional profit target leaves known receipts and costs calculable. Aggregate RPM/CPM aliases are rejected to prevent a common double-counting path; callers must still supply correctly separated source amounts.
