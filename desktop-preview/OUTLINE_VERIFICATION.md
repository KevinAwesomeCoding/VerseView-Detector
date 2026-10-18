# Live outline verification — preview 0.9.0

Overall migration: **[██████████░░░░░░] 62.5% — 5 of 8 milestones complete**.
Outline is part of milestone 6. Discord bot controls and settings sync remain.
Physical speech/provider/presentation checks are deferred. The original
intermittent delivery incident remains unresolved.

## Provenance

Runtime source: `b62103e4fba8868b9d677ad304154582392641a0`, committed/pushed to
`codex/desktop-backend` in the existing repository. The build includes no
uncommitted code; unrelated `.DS_Store` remains excluded/untracked.

Exact app:
`desktop-preview/out/2026-10-18T10-22-51-380Z-b62103e4-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
Native input: `desktop-preview/backend-build/20261018T102141Z-darwin-arm64/backend`.
Six packaged reports identify this executable and build ID. The native input
was hidden during outline and core checks; the frozen bundled engine ran.

Commands use the existing spec/packager and approved environment:

```sh
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/smoke-outline.py
```

The separate app uses approved ad-hoc signing. No new dependencies, security
changes, installed-app replacement, main push or production release occurred.
Inventories, source hashes, screenshots, reports and logs are in the build's
`verification/` directory. Local archive checksum/verification is beside the
deliverable and is copied into that evidence directory after completion.

## Results

| Case | Result and limits |
| --- | --- |
| Regression suite | PASS: 122 Python tests, 42 Node tests, JavaScript syntax/offline-page and whitespace checks. |
| Actual frozen outline loop | PASS with mocks: configured outline callbacks, existing transcript thresholds/request routing and model-result publication run in the frozen host. QA accelerates only outline interval/cooldown and supplies fake speech/model/browser services. No real provider was contacted. |
| Stopped/manual editing | PASS: notes can be edited without recognition, starting a model request or opening a display. Editing while Starting/Stopping is unavailable. |
| Stale replies / revisions | PASS: a delayed model reply cannot overwrite a newer operator correction. The actual packaged engine reports the skipped reply and keeps bilingual/plain-text notes. Old operator revisions are rejected. |
| Bounds / privacy | PASS: 4,000 UTF-16 code-unit limit matches the renderer; empty/oversized/invalid model replies retain previous notes. Secret settings, prompt/provider objects and raw exceptions are excluded from the outline projection. HTML-looking notes remain literal text. |
| Routing / Stop | PASS: each dispatch captures clients, failure policy and callbacks. Stop prevents further fallback tiers/publication. The owned runtime remains Stopping while its executor call drains, then keeps the prior notes. No blind presentation retry was added. |
| Packaged dashboard | PASS: dedicated Outline view, readable textarea, source/status, revision-bound Save/Reload, explicit output target controls and accessible Stop; 36 theme/layout/width cases. Narrow screenshot was inspected. |
| Separate display implementation | PASS with injected-window unit tests: explicit opening only, native display IDs/bounds including a monitor left of primary, windowed mode, Escape, latest text on load, missing target rejection and closure on lost feed/session/display. Fixed local page, sandbox, narrow preload, no navigation/popups and plain text output. |
| Actual outline output window / fullscreen routing | UNVERIFIED: no output window was opened. Unit-window routing is not a physical monitor test. Physical/native appearance and actual audience output remain deferred on Mac and Windows. |
| Other packaged regressions | PASS: same-artifact suggestions, warmup, recovery, core companion and settings suites. Six packaged suites, 180 layout cases total. |
| Native CI | PASS: Windows x64, Mac ARM64 and Intel Mac unit/build/frozen outline/watcher/warmup/recovery/package/extracted-archive checks. No Windows graphical execution is claimed. |
| Real microphone/STT/models, visible VerseVIEW and live semantic queue | DEFERRED / UNVERIFIED. |

The first settings-harness invocation lacked `OBSERVER_PYTHON` and stopped
before launching its app/fixture. It was rerun successfully with the approved
environment path; application bytes were unchanged. Both invocation logs are
retained. No application defect was attributed to that harness setup failure.

## Native development artifacts

Run [39118943718](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39118943718)
completed successfully at the runtime source above. GitHub outer transfer
digests (the inner tar/ZIP has its own checksum):

| Target | Artifact ID | SHA-256 |
| --- | --- | --- |
| Windows x64 | 12133348165 | `f800100046e5d8a04d7cee1fd43e2583240acdbb0815823d94b35a1bd6970bbf` |
| Mac ARM64 | 12133234036 | `c0ffb41d5f2b02a25f6622cbb9a18bd60540f78e9d58148e84ac6c78916ec4af` |
| Intel Mac | 12133548151 | `dfd2d2219ec663615b4a8345a170e54c152ee56159b1b156fb7650d44da29b33` |

Metadata was read from GitHub; native runners verified their packages. Remote
artifacts were not downloaded/executed on this Mac.

## Behavior and cleanup

The AI toggle/prompt/routing retain private backend settings. Generation uses
the existing primary sermon buffer and 90-second production cadence. Operator
edits feed the next generation; current in-flight replies carry a revision
guard. Notes survive Stop/Start in the same host but are memory-only: closing
the backend clears them. Recovery does not restore old outline text or reopen
an output window. Output shows these notes separately from VerseVIEW verses,
and opens only on an explicit operator action with a selected current target.

Owned QA apps/children exited. Hidden native inputs were restored; synthetic
sources and the disposable QA backend were removed. Final app/native input and
approved environment remain for reproducibility. Production settings, installed
app, security and display timeouts remain unchanged. The earlier DETAILS/session
defect stays documented separately in suggestions verification; neither it nor
these outline results explains the original delivery incident.
