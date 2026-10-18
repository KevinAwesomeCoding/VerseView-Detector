# Watcher suggestions verification — preview 0.8.0

Overall: **[██████████░░░░░░] 62.5% — 5 of 8 milestones complete**.
This is part of milestone 6, standalone integration/packaging. Live outline,
Discord bot controls and settings sync remain. Physical tests remain deferred.
The original intermittent delivery incident remains unresolved.

## Provenance

Runtime source `cb5b9c31c43ff25fa53aaf1ddfd392d70f1e7e78` is pushed on
`codex/desktop-backend` in the existing repository. No uncommitted code was
included. Unrelated `.DS_Store` remains untracked/excluded.

Exact local app:
`desktop-preview/out/2026-10-18T10-00-16-633Z-cb5b9c31-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
Native input: `desktop-preview/backend-build/20261018T095947Z-darwin-arm64/backend`.
Four reports identify the packaged executable and matching build ID. The native
input was hidden during suggestions/core tests; the bundled frozen engine ran.

Build commands reuse the approved environment, existing spec and packager:

```sh
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/smoke-suggestions.py
```

The app uses approved ad-hoc signing. Inventories, hashes, screenshots, public
events/reports and logs are in its build's `verification/` directory. Local
archive checks/checksum are recorded beside the deliverable.

## Results

| Check | Result and limits |
| --- | --- |
| Units / static checks | PASS: 117 Python tests, 36 Node tests, syntax/offline-page and whitespace checks. |
| Frozen watcher loop | PASS with mocks: synthetic English/Malayalam speech enters the actual watcher, which processes fake model JSON and emits stream-attributed passive advice. No real model/STT/browser was used. |
| Advice vs delivery | PASS: receiving passive suggestions presents nothing. The new callback only records advice. Existing high-confidence automatic WATCHER behavior remains in the engine; an automatic candidate is not labeled accepted merely because it appears. |
| Operator send | PASS with mocks: explicit sends use existing deliver_verse/controller, WATCHER-MANUAL, stream attribution and a new candidate ID. The legacy GUI's intentional manual cooldown bypass is retained; worship, scripture, interrupt, controller and other applicable guards remain. |
| Correlated acceptance | PASS: manual John 3:19/20 requests reached COMMAND_ACCEPTED for their exact candidate IDs and primary/secondary streams. This confirms fake browser-command acceptance, not visible VerseVIEW output. |
| Worship / failed or pending sends | PASS: a focused real-engine regression retains worship suppression. False/queued/pending returns require review; context/history updates follow acceptance. Bookkeeping errors cannot erase acceptance. |
| Stale actions | PASS: session/control/suggestion identity is rechecked in Electron and the host. Renderer input carries an ID, never an arbitrary verse. Refresh, expiry, old sessions, Stop, duplicates and consumed rows reject later actions without retrying delivery. |
| Bounds / privacy | PASS: six rows, 90-second TTL, 400-character explanations and typed language/stream/states. Raw model JSON, full watcher windows, credentials and exceptions are excluded. Expiry/bounds have unit checks. |
| Stop ownership | PASS: new sends stop immediately; an in-flight send becomes outcome-unknown, with diagnostics retaining actual results. Runtime remains Stopping until its owned send worker returns, preventing later-session interference. |
| Packaged UI | PASS after focused fix: expansion persists within a session and resets across sessions; selection cannot leave stale buttons enabled. Both manual sends and 36 layout/theme/width cases passed. The 640-logical-pixel screenshot was inspected. |
| Packaged regressions | PASS: same-artifact warmup, recovery and core companion suites. Four suites and 108 layout cases total (36 suggestions, 36 warmup, 36 recovery). |
| Native CI | PASS: final run 39117499861 passed Windows x64, Mac ARM64 and Intel Mac unit/build/frozen watcher/warmup/recovery/package/extracted-archive checks. Windows graphical behavior remains unverified. |
| Physical speech/STT/models, visible VerseVIEW, live semantic queue, Windows GUI | DEFERRED / UNVERIFIED. |

Packaged COMMAND_ACCEPTED evidence, October 18 UTC:

| Candidate | Reference / stream | Timestamp |
| --- | --- | --- |
| `36d445b35ce74732b6fd88f27bca19bc` | John 3:19 / primary English | 10:00:55.677674 |
| `309125116d4e4b7384bae9e128933f5b` | John 3:20 / secondary Malayalam | 10:00:56.468815 |

Final native run:
[39117499861](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39117499861).
GitHub development artifacts (outer transfer SHA-256, not the inner tar/ZIP):

| Target | Artifact ID | SHA-256 |
| --- | --- | --- |
| Windows x64 | 12133181716 | `c40d4d4e7b4a308834c6f4b05193c2114e699adc649e1d8a0d7f972aa1a598c5` |
| Mac ARM64 | 12133385519 | `18a0f60558b56cb6fb7b13d227948134aeee83ce501464cc0e6217f7c78bbea5` |
| Intel Mac | 12133391198 | `626a19c510448186dbc8328ac29c7915a82b595957037bc7cda1330f9a5ff1c5` |

Metadata was read from GitHub; native runners verified these packages. They
were not downloaded and executed on this Mac. No production release was made.

## Failure and repair

First build `2026-10-18T09-57-29-984Z-724021e3-darwin-arm64` reached synthetic
transcription, normal delivery and bilingual suggestions. The UI test then
timed out before a new manual send: generic DOM patching retained a DETAILS
open attribute across a changed session. The next toggle closed the panel,
hiding Send. This was a panel/session transition defect, not missing STT or a
failed controller command.

The fix preserves expansion only while the details identity is unchanged,
including recovery identities. The packaged regression now asserts a closed
panel in the new session before opening/sending. Rebuilt warmup/recovery/core
checks passed. Original log, screenshot and provenance are retained under
`verification/first-suggestions-failure/`. This does not explain the original
intermittent incident.

## Cleanup and next work

Owned QA apps/children exited; hidden native inputs were restored. Synthetic
source fixtures and disposable QA backend were removed. Final app/native build
and the approved environment remain for reproducibility. Installed app,
production settings, security and display timeouts remain unchanged. No main
push, release or replacement occurred. Next: live outline within milestone 6;
legacy parity and physical milestones 7/8 remain incomplete.
