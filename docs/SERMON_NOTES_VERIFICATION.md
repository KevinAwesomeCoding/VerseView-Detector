# Group 4: Sermon notes, export, automatic saves and Clear Memory

October 21, 2026 (Chicago); artifact timestamps use October 22 UTC.
Implementation packages 13–16 complete: **16/32 (50%)**. This is a scope checklist,
not elapsed effort or physical/platform certification.

## Build provenance

- Branch `main`, base revision `62c990b213cbf997d61745670073a016937ca22d`.
- Version **0.15.5**; separate Apple Silicon build
  `2026-10-22T04-46-06-993Z-62c990b2-darwin-arm64`.
- App: `/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-22T04-46-06-993Z-62c990b2-darwin-arm64/VerseView Detector-darwin-arm64/VerseView Detector.app`.
- Frozen companion: `desktop-preview/backend-build/20261022T044543Z-darwin-arm64/backend`.
- Existing build commands: approved temporary Python running
  `python desktop-preview/scripts/build-backend.py`, followed by
  `node desktop-preview/scripts/package-native.cjs` and
  `node desktop-preview/scripts/verify-latest.cjs`. The final build includes the
  dashboard session-following and notes-only provider initialization fixes.
- Sibling `provenance.json` records the dirty working tree, build command and
  source hashes. This contains uncommitted Groups 1–4 changes, not just the base
  commit. The 29 companion inputs and shipped frontend runtime hashes are checked
  against source. Documentation/QA harness changes after packaging are excluded
  verification material, not additional shipped runtime changes.

The installed `/Applications/VerseView Detector.app` is untouched. No dependency
installation, security setting change, commit, push, release or replacement was
performed. Existing approved ad-hoc signing was used for this separate artifact.

## Behavior implemented

1. **Generate sermon notes:** normal workspace page and nearby Live action;
   immutable identified bilingual session snapshot, visible generation progress,
   captured/generated times, configured summary route, cancellation and useful
   empty/failure states. Later speech is excluded from the generated result.
   Previous notes remain available on cancellation/failure. Reuses the existing
   summary prompt/provider routing and free-cloud allowance policy. Outline stays
   separate. No unsolicited Discord notification is sent by this desktop action.
   Cancellation ignores late results; an already-running provider request can
   still finish and blocks competing reconfiguration until it returns.
2. **Export:** notes, full current transcript, current cited references or a
   combined notes-snapshot export. Full original English/Malayalam and language
   labels are retained; engine-context fallback is labeled. A known incomplete
   original journal refuses a purported full transcript. Native Save selects
   destination; the main process reads a bounded, hash-verified private packet
   from the current owned backend and atomically writes UTF-8. The renderer
   supplies opaque identities, never arbitrary paths/content. Cancel writes no
   destination file. Success includes destination and source snapshot.
3. **Auto-save:** normal Settings exposes the existing preference. Normal Stop
   and closing while active save a transcript first, then optionally summary
   notes. Status reports transcript availability, pending/generating/saved/failed,
   save time and paths. Same-source existing notes are reused. Closing an already
   stopped app does not create another cloud request. Emergency/checkpoint saves
   remain AI-free. Interrupted generation is reported on reopen without retry.
4. **Clear Memory:** stopped-only scoped review, recoverable session backup and
   diagnostic archive before clearing. Covers both speech streams, parser/current
   context, high-water/duplicate state, queues, suggestions, history, outline and
   generated working notes. Save failure aborts before reset. Saved sessions,
   credentials, native exports, quota ledger, delivery guards and diagnostic
   evidence remain. VerseVIEW visible output is unchanged. Saved sessions can
   restore the backup, including original speech and generated notes, while
   listening remains stopped.

Configured route readback describes configuration, not proof of which fallback
model served a response. Restored older notes explicitly lack their original
generation timestamp rather than inventing one. Pending verse approvals are also
visible on Notes, allowing review while using this page.

## Verification

| Check | Result and scope |
| --- | --- |
| Python regressions | **PASS — 238 tests**, including the real engine's notes-only configuration preserving the observer session and legacy configure still starting one by default. |
| Desktop regressions | **PASS — 89 tests**, including exact acknowledged Clear Memory rotation and native export ownership/integrity/cancellation. |
| Syntax/offline/whitespace | **PASS**, existing JavaScript/offline checks and `git diff --check`. |
| Package inventory/signatures | **PASS — 56 files**, production companion included; existing strict verification, no signing-policy changes. |
| Source provenance | **PASS**, all 29 companion inputs and frontend runtime hashes match current source. |
| Packaged notes workflow | **PASS**, frozen owned backend; empty/cancel/success, synthetic failure with old result retained, full bilingual export/cancel, preference persistence, transcript-first saving, scoped clear/backup/restore. No renderer errors. |
| Layouts | **PASS — 36 combinations**, 1180/900/660 widths, Studio/Focus and six themes; no horizontal overflow and emergency remains usable. This bounds/layout check does not certify arbitrary desktop-background contrast for translucent Glass navigation. |
| Computer Use/native Save | **PASS**, exact packaged `app.asar`; page scrolling reaches export and save locations while safety header stays visible. Actual native dialog saved 35,460 UTF-8 bytes / 19,408 characters, including full original English, Malayalam and cited references. |
| Existing Live regression | **PASS — 36 size/layout/theme combinations** in the final package, including drafts/caret, preview, native pin/Worship, bilingual session saves, popup focus, emergency save and restart recovery. |

Final packaged acceptance and native Save results are recorded in
`desktop-preview/test-results/sermon-notes/`; machine-readable results identify
the actual packaged executable and frozen owned QA companion. QA speech,
completion and controller transports are deliberately synthetic, not real
microphone/STT, cloud inference or observed VerseVIEW pixels.

Focused regression coverage includes immutable sources, original Unicode text,
cancel/late output, interrupted reopen, previous-result retention, incomplete
journals, snapshot-bound exports, transcript-first auto-save/deduplication,
stale review rejection, save-failure-before-reset, backup restore, guarded
engine reset and trusted native export validation.

The first packaged pass exposed a real missing verse-approval panel on Notes;
the panel was added without changing approval policy. A later packaged run
exposed a second real defect: Clear Memory completed its backup/reset but the
dashboard retained the old selected session identity and disconnected. The main
process now follows only that exact acknowledged Clear Memory request, with the
same PID/control identity, through session rotation. The new regression rejects
an unrelated request identity and verifies the cleared session remains stopped.
Failure screenshot/log are preserved as `initial-clear-session-loss.*`.
The saved-session failure test then reproduced another real issue: initializing
summary clients before the first Start called the regular configuration routine,
which unintentionally began a new observer session. Notes-only initialization now
explicitly preserves the current observer identity. Ordinary engine configuration
retains its default behavior. Its initial failure screenshot/log are preserved as
`initial-provider-init-session-loss.*`.

The Glass notes card remained readable, but existing translucent navigation and
the outside-card status text showed low contrast against the gray desktop
backdrop in the Computer Use screenshot. Retain this as a Group 8 visual-polish
follow-up; theme-wide contrast is not certified by the layout bounds checks.
The short generated fixture did not overflow the notes preview itself, so
long-note inner scrolling remains a separate acceptance gap; whole-page scrolling
and safety-header reachability were physically checked.

Live provider latency/failure details, real microphone/STT and visible output,
physical Windows/Intel acceptance and abrupt process termination during a real
cloud request are **unverified for this group**. The original intermittent delivery
incident remains **unresolved**.

## Files and cleanup

New runtime files: `desktop_notes.py`, `desktop-preview/session-export.cjs`,
`desktop-preview/src/notes.js`. Extended the engine summary/reset helpers,
backend/control/operator/session/recovery/settings modules, synthetic QA adapter,
typed Electron main/preload/command/feed boundaries, dashboard/settings/styles,
packaging allowlists and version manifests. Added focused Python notes/native
export/packaged UI tests, a narrow `.gitignore` exception retaining the new Python
regression, and extended engine/command regressions. Prior Groups 1–3 and
unrelated `.DS_Store` changes were preserved.

All settings changes are confined to disposable QA profiles; no real provider
keys, app preferences or saved sessions were edited. Temporary profiles and
exports are removed after verification; separate builds and evidence are retained.
No installed-app replacement is implied by this report.

Evidence: `sermon-notes/results.json`, `native-export.json`, `source-hashes.json`,
`notes-ready.png`, `notes-narrow.png`, `computer-use-top.png`,
`computer-use-bottom.png`, `computer-use.json` and the preserved failure pairs;
`live-layout/results.json` records the final-package regression.
Temporary execution logs are retained under `/tmp/vv-group4-*`.
Next chunk is **Group 5, items 17–20**: language/transliteration, session/startup,
Smart Schedule and keyboard shortcut behavior.
