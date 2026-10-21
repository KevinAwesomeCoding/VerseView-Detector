# Operator controls — group of four

October 20, 2026 (America/Chicago; build timestamps are October 21 UTC).
The user requested High thinking and implementation in groups of four. This group
contains Saved sessions, Worship, Always on top and Emergency Stop & Save. No work
on the next feature group is included.

Overall migration: **[████████████░░░░] 75% — 6/8 engineering milestones**.
This group's implementation and isolated Mac verification: **4/4**. These counts do
not establish production signing, complete legacy parity or physical acceptance.

## Delivered behavior

| Feature | Result | Behavior and evidence |
| --- | --- | --- |
| Saved sessions | PASS in isolated packaged Mac tests | Compact Live box opens a native modal. Dated records identify resumable sessions vs read-only text archives. Both original speech streams, engine context and edited outline are saved. Bounded catalogue/text paging, invalid records, symlinks, changed revisions and failed writes are covered. Selecting/previewing does not start recognition or present. Preparing Resume preserves current content, stages context/outline, and requires explicit Start. |
| Worship | PASS in isolated packaged Mac tests | Persistent, acknowledged toggle keeps bilingual recognition and detection running while suppressing presentation. It is reapplied after configure, fixing the new workflow's pre-Start reset hazard. Queue/VTC/onwards work is cancelled; old approval and model dispatches are invalidated. Turning off does not flush queued references. Existing external presentation is not automatically cleared. |
| Always on top | PASS for native Mac API/readback | Live toggle affects only the Detector window, persists a separate preference and returns native readback. Both directions passed. Normal/narrow windows were inspected; fullscreen/Spaces behavior is not universally certified. Windows native behavior remains a physical check. |
| Emergency Stop & Save | PASS in isolated packaged Mac tests | Persistent header control blocks new delivery first, cancels held approval/pending timed work, stops owned recognition/bot work and saves after owned delivery work drains. No summarizer is started by this path. Success includes record ID/time; failed writes retain old saves and the delivery hold. A queued pre-emergency Start cannot restart afterward. The app stays open for inspection. |

Manual saves create immutable private records under `Backend/SessionLibrary`.
Normal Stop creates a record; rolling autosave replaces one `autosave.json` entry
instead of creating a new library row every 15 seconds. Existing recovery and dated
text archives remain supported. A valid recovery record is archived before Start
new discards its working checkpoint. Save/restore/export data excludes settings,
credentials, provider logs, queued commands and approval decisions.

The reference and separated speech panels remain above the tools. Detailed Settings
and Developer diagnostics are not brought back onto normal Live. The full transcript
switch and Jump to live remain in place. The listening header now shows stopped/save
state after an emergency instead of an old preparation message.

## Exact artifact and provenance

- Desktop source: `66dc11b2442d2e39df7af6c5f696a318872b21aa`.
- Core/backend source: `05031326d7d4cc3c3ddabdc90a3e54e447fe0012`.
  The second commit changes only header status and its desktop regression test.
- Version: `0.13.0`, Mac ARM64.
- Build ID: `2026-10-21T02-31-40-193Z-66dc11b2-darwin-arm64`.
- Tested application:
  `/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-21T02-31-40-193Z-66dc11b2-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
- Frozen backend:
  `desktop-preview/backend-build/20261021T022837Z-darwin-arm64/backend`.
- Build commands (existing workflow, existing approved temporary dependency environment):

  ```text
  /tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
  cd desktop-preview
  node scripts/package-native.cjs
  node scripts/verify-latest.cjs
  python3 scripts/archive-latest.py
  ```

- The application and backend build manifests record their source hashes. Every
  packaged backend source hash was compared with current repository source; all
  matched. All application implementation changes were committed before this build.
  Build provenance reports only unrelated untracked `../.DS_Store`; it is excluded
  from the packaged runtime. No uncommitted application fixes were included.
- Signing: existing workflow's local ad-hoc test signing and strict signature check;
  no production certificate, notarization or OS security setting changed.
- Archive: `desktop-preview/out/deliverables/2026-10-21T02-31-40-193Z-66dc11b2-darwin-arm64.tar.gz`.
  SHA-256: `178a06f924fa43719fe188762d5f3095891cb5be6fb649e0800db5652eeb130a`.

The [packaged UI report](evidence/2026-10-20-operator-controls/packaged-ui.json)
records `packaged: true`, the exact application executable, a frozen owned backend,
verification mode and `guiImported: false`. Computer Use's accessibility tree
confirmed the final `app.asar/src/index.html` path, the Stopped header, session
browser, English/Malayalam originals and saved outline. This was the packaged app,
not a Python GUI/source-script process.

## Validation

| Check | Result |
| --- | --- |
| Python regression suite | PASS — 194 tests; session-specific tests rerun after portable UTF-8 test-file edits |
| Desktop unit suite | PASS — 74 tests, including the final emergency-header regression |
| JavaScript syntax/offline CSP and whitespace | PASS |
| Frozen recovery/crash/restart smoke | PASS — real frozen process, fake speech/services/browser; existing checkpoint survives hard kill and restore remains stopped |
| Packaged group-of-four UI | PASS — final artifact, real native pin readback, Worship before Start, bilingual suppression, rolling autosave/outline, normal Stop, saved-session preview, emergency cancellation/save and stage-only Resume |
| Package byte/provenance/integrity check | PASS — 29 embedded files including operator UI; native backend manifest verified |
| Extracted archive integrity and frozen startup | PASS — extracted deliverable starts its frozen host without recognition/presentation |
| Computer Use | PASS for final packaged Live/popup inspection, popup scrolling and Escape returning focus to Saved sessions |
| Physical microphone/configured STT/visible VerseVIEW | UNVERIFIED in this group — all new delivery tests use explicitly isolated callback replay and a fake controller |
| Windows GUI/physical tests | UNVERIFIED; user previously deferred physical Windows testing |
| Original intermittent incident | UNRESOLVED; these findings do not establish its cause |

Packaged automated layout checks used 1180×880 and 660×620 windows. The dialog had
no horizontal overflow at the narrower size. Native Escape and focus return passed.
The existing transcript view was kept separate from historical session previews.
This is not a claim of exhaustive testing of every theme, DPI or monitor setup.

Native CI for core commit `0503132` is recorded at
[run 39533228978](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39533228978):
all three targets passed. For final desktop commit `66dc11b`,
[run 39533785069](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39533785069)
has passed Mac ARM64; Windows x64 and Mac Intel were still running at
2026-10-21 02:38 UTC. The [CI snapshot](evidence/2026-10-20-operator-controls/ci-status.json)
records the exact observed state. Pending runs are not labelled as passed.

Evidence: [Python tests](evidence/2026-10-20-operator-controls/python-tests.log),
[desktop tests](evidence/2026-10-20-operator-controls/desktop-tests.log),
[frozen recovery](evidence/2026-10-20-operator-controls/frozen-recovery.log),
[package verification](evidence/2026-10-20-operator-controls/package-check.log),
[archive verification](evidence/2026-10-20-operator-controls/archive-check.log),
[session browser](evidence/2026-10-20-operator-controls/sessions.png),
[narrow browser](evidence/2026-10-20-operator-controls/sessions-narrow.png),
[emergency result](evidence/2026-10-20-operator-controls/emergency-saved.png),
[native Live inspection](evidence/2026-10-20-operator-controls/native-live.png).

## Limits and remaining work

- A command already accepted externally cannot be undone by a later mode toggle.
  An already-started cloud request can finish; mode epochs prevent stale delivery,
  and emergency waits for owned work rather than claiming immediate completion.
- A hard kill still has a checkpoint window of up to roughly 15 seconds plus any
  save already in progress. Saving can fail; the UI does not claim success then.
- Legacy recovery contains bounded raw previews, not a complete outline/original-
  speech archive. Prefer a new full library record where available. Library Resume
  restores engine context/outline and preserves prior originals for subsequent
  saves, but the Live Full transcript journal begins with the resumed listening
  run; earlier originals remain readable in Saved sessions rather than being
  replayed into that new live journal.
- Save & Quit, history/chapter/manual/context verse tools, on-demand notes/export,
  other integrations and the remaining typed settings are outside this group.
- Live semantic queue release with real speech, production signing/distribution,
  remaining Mac physical checks and explicit installed-app replacement approval
  remain separate gates. This is an ad-hoc signed preview.

## Changed files and cleanup

Implementation adds `desktop_sessions.py`, `desktop_operator.py` and
`desktop-preview/src/operator.js`. Existing backend, recovery and control adapters,
engine/watcher dispatch guards, Electron IPC/preload, consumer rendering/styles,
package version/manifests and verification scripts were updated. Focused Python,
desktop and packaged UI regression coverage was added. The exact changes are in
commits `0503132` and `66dc11b`.

All new runtime checks used the explicit QA profile with synthetic credentials,
fake speech/provider/browser transports and no outbound presentation. Native pin
was toggled off again. No dependencies were installed for this group; the existing
approved isolated build environment was reused. No normal user settings, Drive sync
configuration, installed original app or existing 0.12.1 preview were replaced.
The QA process is closed after inspection. Test-only source directories are removed
by the harness; the stopped synthetic QA backend profile and test-only native pin
preference were removed after confirming no QA backend was running. Final cleanup
retains evidence and the final distributable. The existing reusable build environment
was retained. Concurrent theme/icon edits that appeared during final documentation
were left untouched and are not part of this tested artifact.

To try this build, use its separate application bundle or extract its archive to a
new version folder. Keep the older preview for rollback. Replacing the original
installed detector is not part of this group and still requires the user's explicit
approval after the remaining acceptance/signing checks.
