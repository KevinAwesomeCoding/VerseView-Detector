# Verse tools — second group of four

October 20–21, 2026. Preview version 0.14.0. The four features in this group are
implemented and pass isolated packaged Mac checks. Overall engineering milestones
remain **[████████████░░░░] 75% (6/8)**; complete GUI parity, physical acceptance and
production release/signing are separate outstanding work.

## Behavior and verification

| Feature | Result | Verified behavior |
| --- | --- | --- |
| Context editing | PASS, isolated | Context tab accepts one canonical book/chapter and optional verse. Stopped edits prepare the next explicit Start; running edits invalidate older delivery work. Applying context presents nothing. Revisions reject stale edits without overwriting speech updates. |
| Manual reference entry | PASS, isolated | Reference tab validates aliases, unique book prefixes and chapter/verse bounds. Preview retrieves text separately. Explicit Send uses the shared delivery path with no cooldown bypass and a candidate ID; Worship, verification, duplicate, context and stale-epoch guards remain active. |
| Selectable history | PASS, isolated | The accepted-command history is bounded to 128 references. Selecting one only previews it. Sending requires the separate Send button while listening. History acceptance does not certify a visible VerseVIEW screen. |
| Chapter browsing/preview | PASS, isolated | All 66 books are available, with chapter validation and eight verses per page. Selection previews without presenting. Lookup uses the selected translation; unsupported/unavailable text is labelled unavailable instead of silently substituting KJV. |

A compact **Verse tools** launcher sits below speech in Live. Its four tabs share
one preview and explicit Send action. The popup keeps Stop, Emergency Stop & Save
and held-candidate decisions accessible. Saved sessions now also retains these
safety/decision controls while its modal makes the background inert. Incoming feed
updates preserve the reference draft, caret and reading position. Technical IDs
remain in Developer Mode. Consumer outcomes use labels such as “Command sent” and
“Not sent,” with the delivery reason alongside them.

## Exact tested artifact

- Desktop application source: `1efd47007994bb87086c0d30710d647c8bb00c25` (see build
  provenance for the authoritative full revision; abbreviated `1efd470`).
- Backend source: `1c20c4c` (the full revision is in the packaged backend manifest).
  The subsequent application commit changes outcome labels and QA sequencing only.
- Packaged UI harness: `5483f68b947635e40943865752df9c257c7a1aa5`; it waits for the
  existing three-second cooldown before requesting the first manual command.
- Build ID: `2026-10-21T03-03-23-008Z-1efd4700-darwin-arm64`.
- Preserved application:
  `/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-21T03-03-23-008Z-1efd4700-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
- Archive:
  `desktop-preview/out/deliverables/2026-10-21T03-03-23-008Z-1efd4700-darwin-arm64.tar.gz`.
- Archive SHA256:
  `32e5ed03925abf2a75f2b8d2ff9b0e7f06d8fdea4e1772aba9aafd38f42c8081`.

The app ran directly from the isolated build checkout before it was copied to the
preserved path above. The harness recorded `app.isPackaged=true`, its exact executable
path and backend PID 62135 with `frozen=true`, `verification=true`, `guiImported=false`.
The preserved copy passed ASAR/source hashes, frozen-backend manifest verification
and `codesign --verify --deep --strict`. The archive was extracted, its contents
verified and its frozen backend started successfully without audio/presentation.

Build commands used the established specification and scripts:

```text
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
node desktop-preview/scripts/package-native.cjs
node desktop-preview/scripts/verify-latest.cjs
python3 desktop-preview/scripts/archive-latest.py
```

Existing approved dependencies were reused. The build checkout contained committed
application sources and one untracked symlink to the existing development
`node_modules`; no uncommitted application code was included. Concurrent theme/icon
work and both unrelated `.DS_Store` files in the primary checkout were preserved
and excluded from this build and these commits. No installed application was replaced.

## Evidence and limitations

[Evidence directory](evidence/2026-10-20-verse-tools/) contains packaged-process proof,
checks, provenance, default/narrow screenshots and the preserved artifact mapping.

- **203 Python tests PASS** in the isolated source checkout. New focused cases cover
  reference validation, staged/live context, stale revisions, lookup paging/cache,
  translation changes, missing/malformed text, stale selection/Stop, and real-engine
  Worship, deduplication and epoch cancellation. Command payloads now have per-action
  field allowlists, preserving the previous rejection of extra fields.
- **76 desktop tests PASS** in the isolated checkout, plus syntax/offline CSP and
  whitespace checks. The primary checkout also passed 79 tests including three
  independent, uncommitted theme-icon tests; these are excluded from this group's
  reproducible source count.
- **Packaged UI PASS**: read-only preview/chapter/history; selected manual John 3:21
  accepted with candidate `b79481a2f6d94b5194c1ba115ec8ca7e`; repeated reference
  suppressed; Worship suppresses John 3:22; live/stopped context does not present;
  draft survives updates; held decision accessible; Stop invalidates selection;
  Emergency Stop & Save acknowledges saved state. No renderer errors were recorded.
- **Layout PASS in automated packaged checks** at 1180×880 and 660×620. The narrow
  content scrolls, has no horizontal overflow, and Escape returns launcher focus.
  Computer Use separately inspected the actual packaged app and browsed the fixture
  chapter; `native-chapter.png` records default-window readability. A later native
  scroll attempt coincided with the harness's scheduled app closure, so native
  trackpad/gesture scrolling is not independently certified by that attempt.
- **Initial harness runs FAILED expectations**, with screenshots/logs preserved.
  A context edit correctly triggered the existing 45-second quarantine, and a later
  manual request correctly hit the three-second cooldown after a synthetic STT
  command. The harness now tests context separately and waits for the configured
  cooldown before its distinct delivery case. No guard was disabled and no app retry
  was added.
- **UNVERIFIED in this group**: actual microphone/STT transport, live Bible HTTP,
  actual visible VerseVIEW reference/text, live semantic queue release and physical
  Windows UI/audio behavior. Speech was synthetic callback replay, chapter text was
  explicitly labelled fixture data, HTTP was forbidden and the controller was fake.
  The original intermittent incident remains unresolved.

## Cross-platform CI

The first run, [39536729118](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39536729118),
passed Mac ARM64 and Intel builds/archive verification, but Windows failed at the
early JavaScript tests before packaging. Its public annotation only exposed the
exit code. The workflow now routes those tests through its existing retained-log
wrapper so a repeat failure exposes the actual assertion in check annotations.
The rerun [39550861376](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39550861376)
passed Windows JavaScript tests and proceeded to the native build. The initial
assertion remains unavailable; no application change is attributed to that failure.
Windows x64 and Mac ARM64 completed successfully, including native frozen checks,
packaging, archive extraction and startup verification. Intel Mac passed the earlier
run with identical application code; at this report checkpoint its rerun is still
installing dependencies. The workflow-only rerun is therefore not labelled fully
green. `native-ci.json` preserves the run/job checkpoint; Windows physical testing
remains unverified.

## Cleanup and remaining work

The QA app and its frozen backend closed. Each test used an explicit QA profile,
synthetic keys, fixture lookups and a fake controller; normal settings, normal
sessions, the installed detector and the existing theme preview were left intact.
Failed QA profiles were moved to temporary directories for investigation. After
retaining screenshots/logs, all three confirmed synthetic QA profiles were removed.
The build dependency symlink was removed and the managed checkout was archived;
the verified app/archive copies remain at the preserved locations above. Existing
shared build dependencies were retained for later milestones. No test processes
remain running. The original installed app and unrelated theme/icon edits are intact.

This delivery stops at these four features. Notes/export/reset and remaining typed
settings parity stay in the audited backlog. Installing/replacing the original app
and production signing still require their separate approval/release stage.
