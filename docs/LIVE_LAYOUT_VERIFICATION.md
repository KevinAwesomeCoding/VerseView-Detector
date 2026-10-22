# Group 2: Live controls and navigation

October 21, 2026. Implemented in a separate 0.15.3 test app. Base branch/revision:
main, 62c990b2, plus the existing uncommitted Group 1 and new Group 2 changes.
The installed app, real settings/keys and saved sessions were not modified.

## Delivered

1. One wrapping header groups Start/Stop, Emergency Stop & Save, Worship, Always
   on top and Save session. Clear output retains its distinct action. Save/error
   feedback stays near these controls; redundant Worship labels were removed.
   The header remains reachable while scrolling.
2. Saved sessions is now a workspace navigation action with save/recovery status.
   Studio uses the sidebar; Focus/narrow windows use their visible navigation.
   The existing modal still previews dated bilingual records and stages Resume
   without starting recognition. A recovery prompt with Choose session sits
   beside Start when Resume/Start new must be resolved.
3. Bible reference entry is immediately below the speech panes, with Preview
   reference beside it. Preview/text and explicit Send reuse the existing guarded
   backend commands. Reference input was removed from the tools popup. Drafts,
   input caret and a collapsed preview survive incoming updates; new selections
   can open their own preview. Stop/stale state still disables delivery.
4. Verse tools retains Context, History and Chapter. The nearby Chapter shortcut
   opens that tab with the acknowledged book/chapter prefilled; opening it alone
   neither fetches Bible text nor presents. Browse chapter remains explicit.
   The complete verse-number grid is Group 3, not part of this delivery.

Full interface refreshes now restore focus for operator controls and manual
reference fields, including caret position. Popup close can find the visible
Saved sessions launcher after resizing hides its original sidebar launcher.
Tests wait for the native asynchronous close/focus result, rather than asserting
before the close event has run. Existing transcript display and smooth Jump to
live behavior were retained.

## Exact artifact and build

Final build: `2026-10-22T03-04-12-170Z-62c990b2-darwin-arm64`.

Repository-relative app:

`desktop-preview/out/2026-10-22T03-04-12-170Z-62c990b2-darwin-arm64/VerseView Detector-darwin-arm64/VerseView Detector.app`

The sibling `provenance.json` records the dirty source state and packaged hashes.
Version is 0.15.3. This frontend-only group reuses the frozen backend at
`desktop-preview/backend-build/20261022T023836Z-darwin-arm64/backend`; all recorded
backend source hashes were checked against current source and matched.

The existing `node desktop-preview/scripts/package-native.cjs` and
`node desktop-preview/scripts/verify-latest.cjs` workflows were used with the
already approved local dependencies and ad-hoc signing. No dependencies were
installed, security settings changed, release published or Git push performed.

Runtime files changed for this group: `desktop-preview/src/operator.js`,
`verse-tools.js`, `observer.js`, `dashboard.js`, `desktop.css`, `verse-tools.css`,
plus package version manifests. Added `tests/live-layout-ui.cjs`; adapted the
existing operator/verse UI harnesses to relocated controls and isolated QA tags.
Earlier Group 1/investigation edits and unrelated `.DS_Store` files were preserved.

## Verification

| Check | Result and scope |
| --- | --- |
| Desktop unit tests | PASS, 82 tests. |
| Syntax, offline CSP and whitespace | PASS, existing check script and `git diff --check`. |
| Package inventory and signing | PASS, 54 packaged files, production backend included, strict Mac ad-hoc signature verification. |
| New layout harness | PASS in source and final packaged executable; frozen owned backend; 36 window/layout/theme cases. Emergency remains visible at page bottom, both navigation layouts work, manual drafts/caret and collapsed previews survive updates, full refresh preserves focus, both transcript modes remain usable. |
| Session workflows | PASS in final package: native pinning, Worship retained across Start, bilingual records and outline saved/read, popup scrolling/focus return, AI-free emergency save, restart recovery and staging Resume without automatic Start. |
| Verse workflows | PASS in final package: exact-translation fixture previews, chapter paging, manual candidate reaches real delivery logic, duplicate and Worship suppression, history selection read-only, live/staged context and stopped Send invalidation. |
| Computer Use | Attached to the earlier 02:57:05 packaged 0.15.3 app, confirmed its exact `app.asar` URL and relocated header/navigation/reference controls. Clicked Chapter → John 4, verified prefilled Chapter tab, closed it and observed focus return. Final 03:04:12 package includes the subsequent full-refresh focus enhancement and passed all three packaged harnesses. |
| Real microphone/STT and visible VerseVIEW | UNVERIFIED for this group. All recognizer/browser/Bible transports in the harnesses were explicit QA substitutes. No real provider request or presentation was performed. |
| Windows/Intel native acceptance | UNVERIFIED for this group; shared frontend paths changed, but this artifact is Apple Silicon. No CI run was triggered. |

The backend was unchanged from Group 1's 217-test Python result; it was not
refrozen or presented as a new physical test. No STT model/provider behavior or
delivery guard was modified in Group 2.

Local evidence: `desktop-preview/test-results/live-layout/results.json`,
`live-default.png`, `live-narrow.png`, plus `operator-ui-checks.json` and
`verse-tools-ui-checks.json`. Final reports record `packaged: true` and the exact
03:04:12 executable. The first layout fixture accidentally requested silent QA
recognition; that fixture flag was corrected before the passing speech checks.
An early operator assertion raced native close/focus completion; the harness now
waits for focus and the final package passes the check.

Synthetic profiles and temporary source fixtures were cleaned. The inspection
app and owned backend were closed; its isolated inspection profile was removed.
No real app settings needed restoration. The test artifact remains for review.

## Handoff

Group 2 completes work packages 5–8. Current checklist progress is **8/32 (25%)**.
Next is Group 3: current-chapter verse-number grid, chapter/history actions,
watcher settings/status and an explicit approval inbox. The original earlier
intermittent incident remains unresolved; Group 1's observed substitution defect
and this layout verification do not establish its original cause.
