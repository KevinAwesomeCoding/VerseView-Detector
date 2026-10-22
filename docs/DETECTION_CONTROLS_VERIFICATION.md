# Group 1: connection visibility and detection controls

October 21, 2026. Current source implementation: 0.15.2, based on main at
62c990b2 with uncommitted Group 1 changes. No commit/push, release publication or
installed-app replacement was performed. Earlier investigation/plan edits and
unrelated `.DS_Store` files were preserved.

## Changes

- The existing five-attempt remote startup loop now publishes typed attempt,
  retry, success, failure and cancellation events. Each attempt has a timestamp;
  public failure categories distinguish browser startup, remote page access and
  missing controls without exposing URLs, driver exceptions or credentials.
- Normal Live shows remote progress, a bounded expandable connection history and
  an explicit Retry connection action after terminal failure. Retry uses the
  ordinary guarded Start flow; it does not create an automatic retry cycle or
  bypass saved-session/sync/start guards. Backend-feed loss is labelled separately.
- A chapter-only candidate now updates context without presenting, even when a
  restored/session high-water verse exists. It cannot silently become that verse.
- Settings now exposes confidence threshold (50–100%), manual confirmation,
  hear-twice verification, Verse Interrupt, Spoken Numeral Mode and Smart Amen.
  The Python/Electron allowlists validate types/ranges; edits remain stopped-only,
  revision-checked and applied on next Start. Unrelated fields/credentials survive
  saves, including unrelated legacy GUI drafts. Failed disk saves roll back widgets.
- Descriptions distinguish low-confidence approval from fast-path automatic
  detection and explain the normal hear-twice path. Disabling manual confirmation
  does not authorize low-confidence sends. Existing recognition/provider behavior,
  duplicate, worship, queue and delivery checks remain in force.
- A focused Smart Amen test reproduced rejection of the standalone phrase
  `Let us pray.` because its start offset was before the percentage cutoff.
  Checking the phrase end fixes that case. Delayed callbacks also check timer
  identity, delivery epoch, shutdown and enabled state; cancelled callbacks cannot
  clear a later presentation merely because the timer function was already queued.

## Exact separate artifact

Final build ID: `2026-10-22T02-43-05-678Z-62c990b2-darwin-arm64`.

App location (repository-relative):

`desktop-preview/out/2026-10-22T02-43-05-678Z-62c990b2-darwin-arm64/VerseView Detector-darwin-arm64/VerseView Detector.app`

The sibling `provenance.json` records the base revision, branch, dirty working-tree
listing, packaged frontend hashes and backend source hashes. The frozen backend
was built at `desktop-preview/backend-build/20261022T023836Z-darwin-arm64/backend`.
All recorded backend source hashes were compared to the current source and matched.
The existing scripts were used with the already approved temporary Python and
installed local Node dependencies:

```text
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
/usr/local/bin/node desktop-preview/scripts/package-native.cjs
/usr/local/bin/node desktop-preview/scripts/verify-latest.cjs
```

No dependency installation or security change occurred. Existing ad-hoc test
signing was retained. The installed `/Applications/VerseView Detector.app` was
not replaced or modified.

## Verification and limits

| Check | Result | Evidence / scope |
| --- | --- | --- |
| Full Python suite | PASS | 217 tests, including recorded phrase sequence with restored high-water 18, shorthand option/duplicate guard, five failures, early success, cancellation, Smart Amen and settings rollback/persistence. |
| Desktop unit suite | PASS | 82 tests, including typed detection fields, finite threshold limits and private/bounded connection-event decoding. |
| Syntax, offline page policy and whitespace | PASS | Existing check script and `git diff --check`. |
| Final package inventory/signature | PASS | Existing verification checks 54 packaged files and confirms production engine included; Mac strict ad-hoc signature checks pass. |
| Frozen backend / real settings store | PASS with mocked external services | `tests/detection-backend-ui.cjs`: actual packaged Electron executable and owned frozen backend; all six fields save/read back and survive app/backend restart; unknown fields retained; Start/Stop and new production connection telemetry traverse actual IPC/feed/UI. Browser, microphone and STT are QA substitutes. |
| Settings UI and failure display | PASS with synthetic devices/events | `tests/settings-ui.cjs`: all six fields save; invalid input blocked; failed save/external conflict/stale/running cases preserved; 36 size/layout/theme combinations fit; normal consumer mode exposes detection controls and five-attempt failure/retry history; an incoming transcript does not collapse that history. |
| Computer Use | PASS for earlier same-change test package | Attached to the separate 02:39:16 packaged app, verified its exact `app.asar` URL, version 0.15.2 and detection controls. Final 02:43:05 package adds clearer failed-state/low-confidence descriptions and is independently exercised by the two packaged harnesses. |
| Real microphone/STT and visible VerseVIEW | UNVERIFIED for this change | No real audio capture/provider request/presentation was performed. Mocked controller acceptance is not visible output. |
| Windows/Intel native build and physical operation | UNVERIFIED for this change | Source paths are shared; this build is Apple Silicon only. No CI push was requested/performed in this chunk. |

Local reports/screenshots are under `desktop-preview/test-results/`:
`python-checks.txt`, `settings-ui-checks.json`, `consumer-detection-settings.png`,
`consumer-remote-failure.png`, and `detection-group1/native-results.json` plus its
settings screenshot. Native reports record `app.isPackaged`, executable path,
frozen backend identity and explicit mocked microphone/STT/presentation scope.

An older settings harness still selected a removed theme dropdown. Its selector
was updated to the current theme buttons; it was rerun against the final artifact.
Synthetic QA profiles and temporary source/settings fixtures were cleaned by the
harnesses; failed-run synthetic profiles were also removed. No user keys, settings,
saved sessions, microphone selection or live presentation settings were changed.

## Handoff

Group 1 is implemented and locally verified within the limits above. Group 2 is
next: consolidate Live controls, move Saved sessions to workspace navigation,
move reference entry below transcripts and improve nearby verse-tool access.
Do not count this as completion of Groups 2–8 or full release/platform acceptance.
The current-session wrong-verse mechanism is supported by recorded evidence; the
original earlier intermittent incident remains unresolved.
