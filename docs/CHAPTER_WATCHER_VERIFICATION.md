# Group 3: Chapter navigation, history and watcher approval

October 21, 2026 (Chicago); build timestamps use UTC, October 22.
Implementation packages 9–12 complete: **12/32 (37.5%)**. This counts the documented
implementation packages, not physical/platform certification or elapsed effort.

## Exact build and scope

- Branch `main`, base source revision `62c990b213cbf997d61745670073a016937ca22d`.
- Version **0.15.4**, build `2026-10-22T03-32-14-062Z-62c990b2-darwin-arm64`.
- Exact tested app: `/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-22T03-32-14-062Z-62c990b2-darwin-arm64/VerseView Detector-darwin-arm64/VerseView Detector.app`.
- Frozen companion: `desktop-preview/backend-build/20261022T033156Z-darwin-arm64/backend`.
- Existing commands: approved temporary Python environment running
  `python desktop-preview/scripts/build-backend.py`, then
  `node desktop-preview/scripts/package-native.cjs` and
  `node desktop-preview/scripts/verify-latest.cjs`.
- The package includes the existing uncommitted Groups 1–2 changes and Group 3
  runtime changes; it is not a clean-commit artifact. Its sibling
  `provenance.json` records the dirty working tree, build command and file hashes;
  `backend-manifest.json` records all 28 backend source/manifest inputs.
  All 28 backend inputs and frontend runtime source hashes matched current source.
  Two excluded verification harnesses changed after packaging: `tests/chapter-watcher-ui.cjs`
  (inspection stdin cleanup) and `tests/live-layout-ui.cjs` (wait for asynchronous
  close/focus). These documented hash differences are verification material, not
  shipped runtime changes.
- Actual executable path and `packaged: true` are recorded in both packaged UI
  reports. The owned companion was frozen, `guiImported: false`, and explicitly
  isolated for verification. No source-script app was substituted.

No dependencies were installed, real settings/keys altered, installed app replaced,
release published, Git push made or system security settings changed. Existing
approved dependencies and the established separate-artifact ad-hoc signing were
used. This is an Apple Silicon test artifact, not a new Windows/Intel release.

## Delivered behavior

1. **Current-chapter grid:** compact, expandable verse-number grid below Live's
   reference row and in the Chapter tab. John 3 has 1–36; it tracks acknowledged
   parser context, highlights its current verse, and rejects clicks whose context
   revision has changed. Current context is not proof of visible presentation.
   Counts are local: 66 books, 1,189 chapters and 31,102 KJV verse indices validated
   against sequential source data, with no STT/model/network calls. KJV numbering
   and translation differences are labeled. Text is requested only on explicit
   Preview, through the existing exact-translation lookup/cache.
2. **Guarded selection/history:** selecting a number or history entry is read-only;
   Send remains explicit through existing approval, duplicate, cooldown, worship,
   queue and controller guards. Clear current history is revision checked and
   empties only the current history list. Saved sessions, sermon reference memory,
   context, delivery events and credentials remain intact.
3. **Watcher setup/status:** normal Settings exposes enable/provider even while
   disabled. Developer Mode adds batch interval, both confidence thresholds,
   line/time window and repeated-suggestion cooldown. Types, bounds, threshold
   ordering and save/rollback are validated. Status uses actual in-flight/cycle
   state, configured-client evidence and typed free-profile auth/rate/quota/budget
   outcomes. Raw provider exceptions/keys are not exported. Unknown provider
   failures show a generic failed/no-usable-response state rather than guessing a
   rate limit. The effective free profile is identified; selecting another watcher
   provider does not override its English/Malayalam routing or budgets.
4. **Approval inbox:** English/Malayalam reference, reason, language/stream,
   confidence and creation time; Preview, Display, Dismiss and revision-checked
   Clear. Every desktop watcher suggestion requires explicit approval, including
   the engine's high-confidence AUTO_SUGGEST branch. Legacy GUI behavior retains
   its existing default through a separate configure flag. Desktop Display has
   **no cooldown bypass**, captures the delivery epoch and candidate ID, reports
   actual guarded outcomes, and disables competing manual sends. Expiry (90s),
   replacement, context/worship/Stop changes and session rotation invalidate advice.
   Generation never counts as delivery; command acceptance never counts as pixels.

The old count table contains inconsistent data, including Leviticus chapter sizes.
KJV delivery/structural checks now use the same validated index as the KJV grid,
so a valid grid item such as Leviticus 27:34 is not rejected by the old table.
Other translations retain the existing engine bounds behavior and receive the
explicit KJV-baseline warning in the number grid. Exact alternative versification
metadata is not claimed. Source/license: [KJV metadata source](KJV_METADATA_SOURCE.md);
the upstream MIT license is also bundled inside the companion resources.

## Verification and evidence

| Check | Result and limits |
| --- | --- |
| Python suite | **PASS — 225 tests.** Includes local canon sizes, KJV boundaries without changing other numbering, stale grid/history identities, invalid translation fallback, watcher settings save/rollback, approval-only engine dispatch, expiry, replacement, stop/worship and guarded candidate delivery. |
| Desktop suite | **PASS — 84 tests.** Includes typed watcher settings and bounded review/grid IPC, stale/disconnected rejection and privacy filtering. |
| Syntax/offline/whitespace | **PASS**, existing JavaScript/offline checks and `git diff --check`. |
| Package verification | **PASS**, 54 packaged files, production engine included, strict existing Mac signature/inventory checks; all 28 backend source hashes match. |
| New packaged workflow | **PASS** — actual frozen watcher processes synthetic .95 English and .70 Malayalam replies into separate held rows. Neither reference is automatically accepted. Preview is read-only. Explicit Display of John 3:19 is correlated to candidate `ad21d67e10e147398b31b490bb69fa39` and COMMAND_ACCEPTED at `2026-10-22T03:32:37.982478+00:00`. Dismiss/Clear and stale/repeated action rejection pass. High-confidence AUTO_SUGGEST bypass protection is also covered by the real-engine focused regression, independently of fast-path conflict downgrading. |
| Guard enforcement | **PASS** — initial separate build recorded cooldown SUPPRESSED for an explicit watcher Display. The final-package positive test waits for the ordinary cooldown to pass before its first Display; it does not retry a suppressed candidate or alter the cooldown. |
| New UI layouts | **PASS — 36 combinations** of 1180/900/660 widths, Studio/Focus layouts and six themes. Grid's final verse remains reachable; emergency controls stay usable. |
| Existing Live layout regression | **PASS — 36 combinations in this exact final package**, including drafts/caret, preview collapse, native pinning, Worship, bilingual session saves, focus return, emergency save and restart recovery. An initial immediate assertion ran before asynchronous modal close/focus restoration; the screenshot already showed the restored focus. The harness now waits for that observable result; runtime focus behavior was not changed. |
| Computer Use | **PASS**, exact packaged `app.asar` inspected. Read grid 1–36 with verse 19 highlighted; scrolled to watcher/speech setup with safety header visible. Normal Settings had enable/provider without tuning. Enabled Developer Mode in a disposable QA profile, expanded all six advanced fields, entered 12 context lines through the keyboard and saved; UI acknowledgement and the owned backend settings file both confirmed it. |
| Actual microphone, STT transport, live cloud inference, visible VerseVIEW | **UNVERIFIED for this group.** Speech callbacks, model replies, Bible lookup and browser/controller services were explicit QA substitutes. No live command/provider request was made. |
| Native Windows/Intel | **UNVERIFIED for this group**; shared code is implemented, but no new native artifacts/physical acceptance were run. |
| Original intermittent delivery incident | **UNRESOLVED.** Neither this group nor the prior observed substitution defect proves the cause of the older incident. |

Evidence remains under `desktop-preview/test-results/`:

- `chapter-watcher/results.json`, `watcher-ready.png`, `chapter-narrow.png`,
  `computer-use.json`, `initial-guarded-suppression.json`.
- `live-layout/results.json`, `live-default.png`, `live-narrow.png`; the initial
  close/focus timing failure screenshot remains preserved as `failure.png`.
- `python-checks.txt`; package provenance and inventory verification are beside
  the exact artifact above. Temporary command logs were retained under `/tmp/vv-group3-*`.

## Changes, cleanup and next group

Runtime/build files changed for Group 3: `bible_metadata.py`,
`bible_metadata.LICENSE`, `contextual_watcher.py`, `vv_streaming_master.py`,
`desktop_backend.py`, `desktop_control.py`, `desktop_verses.py`,
`desktop_suggestions.py`, `desktop_settings.py`, `verseview.spec`,
`desktop-preview/scripts/build-backend.py`, main/command/feed boundaries,
`src/settings-policy.js`, `settings.js`, `observer.js`, `verse-tools.js`,
`verse-tools.css`, `dashboard.js` and package version manifests. Added the packaged
`tests/chapter-watcher-ui.cjs`; extended focused Python/desktop regressions and
corrected the existing layout harness's asynchronous focus wait. Prior Groups
1–2 edits and unrelated `.DS_Store` files were preserved.

All test settings were changed only in disposable private QA profiles. Source
fixture settings remained unchanged in the parsed comparison; temporary profiles/fixtures and
owned test app/backend processes were removed/closed. The separate build and
verification evidence remain for review. No real app settings needed restoration.

Next authorized chunk on request is **Group 4, items 13–16**: Generate Sermon
Notes, notes/transcript export, auto-save/save status and recoverable Clear Memory.
