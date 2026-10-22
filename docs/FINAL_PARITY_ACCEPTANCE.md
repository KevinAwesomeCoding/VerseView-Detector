# Final parity acceptance and handoff

October 22, 2026 (Chicago). Groups 1–7 and Group 8 items 29/32 are complete:
**30/32 (93.75%)**. This is not full physical or native-platform acceptance.
Item 30 still needs the requested unlocked-Mac Computer Use pass; item 31 still
needs current-code native Windows/Intel CI and available real-path acceptance.
The repeating task must remain active until those items are resolved or the user
explicitly changes their scope. Do not rerun completed tests while these same
external conditions remain unchanged.

## Exact artifact and provenance

- Version **0.15.7**, branch `main`, base
  `62c990b213cbf997d61745670073a016937ca22d`, plus uncommitted Groups 1–8 work.
  The installed app is unchanged. No commit, push, release or security changes.
- App: `/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-22T05-50-40-417Z-62c990b2-darwin-arm64/VerseView Detector-darwin-arm64/VerseView Detector.app`.
- Single-app ZIP: `/Users/kevinanil/VerseView-Detector/desktop-preview/out/deliverables/2026-10-22T05-50-40-417Z-62c990b2-darwin-arm64.zip`.
- ZIP SHA-256: `c1fc441f5e467601cd851e5a63648ad48dd04b4fbc96a3c5ad6de1f7138d5b3a`.
- Companion: `desktop-preview/backend-build/20261022T055008Z-darwin-arm64/backend`.
- Approved build environment reused: `/tmp/verseview-group5-build-20261022`.
- Build commands, using the existing scripts:
  `python desktop-preview/scripts/build-backend.py`,
  `node desktop-preview/scripts/package-native.cjs`,
  `node desktop-preview/scripts/verify-latest.cjs`,
  `python desktop-preview/scripts/archive-latest.py`.
- Sibling `provenance.json` records branch/revision, dirty working tree, dependencies,
  command and file hashes. Backend manifest records its exact 32 source inputs.
- `test-results/final-source-match.json`: all **61 frontend runtime source files**
  and **32 backend inputs** match the tested build. Later documentation, CI scripts
  and excluded verification fixtures differ without changing shipped code.
- Final package verifier: **62 files**, production engine and owned frozen backend
  present. Archive is extracted to a fresh temporary directory; its strict ad-hoc
  signature, runtime and frozen startup are verified. Its only top-level item is
  `VerseView Detector.app`; licenses/provenance remain inside the application.
- Packaged acceptance records `app.isPackaged=true`, the exact executable above,
  owned frozen backend PID, `guiImported=false`, and explicit QA status. Tests did
  not launch the source script as the consumer app.

## Consolidated results

| Check | Result / evidence |
| --- | --- |
| Python | **PASS**, 257 tests; `desktop-preview/test-results/final-python.log` |
| Desktop boundaries/policy | **PASS**, 99 tests; `final-node.log` |
| Syntax/offline CSP/whitespace | **PASS**, existing checker and `git diff --check` |
| Final package/source integrity | **PASS**, `final-package-verification.json`, `final-source-match.json` |
| Extracted single-app download | **PASS**, `final-download-verification.log` and archive report beside ZIP |
| Detection save/restart and connection telemetry | **PASS**, actual packaged app/frozen companion, fake browser; `detection-group1/native-results.json` |
| Live layout, manual preview, context, history, safety controls and popup focus | **PASS**, `live-layout/results.json`, 36 size/layout/theme cases |
| Chapter grid and bilingual watcher inbox | **PASS**, `chapter-watcher/results.json`, 36 cases, preview/dismiss/revision clear and guarded manual send |
| Notes/cancel/failure/export/auto-save/backup-first clear/restore | **PASS**, `sermon-notes/results.json`, 36 cases; long notes scroll independently to the final marker and back; full Unicode export is 22,016 characters |
| Language labels, timetable, local startup opt-in/countdown/cancel, shortcut | **PASS**, `session-setup/results.json`, 36 cases; permission and speech are QA substitutes |
| Connections, credential file scope and Developer settings | **PASS**, `connections/results.json`, 36 cases; see Groups 6–7 report |
| Frozen startup/recovery/sync/outline/Discord/watcher/connections | **PASS**, `final-smoke-*.log`, `final-connections-smoke.log`; all isolated transports/hardware substitutes |
| Real local HTTP request wiring | **PASS** against loopback synthetic server through existing Test/Warm code, including model/auth; a real model is **UNVERIFIED** |
| Diagnostics under arriving transcripts | **PASS**, `diagnostics/results.json`: 80 synthetic outcomes, ongoing 150ms transcript frames, keyboard page scrolling and usable Stop at 660×620. External controlled callback-replay feed, not production microphone capture |
| All six theme renders | **PASS** automated screenshots personally inspected in `test-results/diagnostics/`; Glass navigation/titlebar now use the existing reading-surface background for reliable contrast |
| Current native Mac Computer Use / real file chooser / external Glass backdrop | **UNVERIFIED**: tool explicitly reported locked Mac. Unlock requested. Renderer screenshots and automated native-dialog responses do not establish this result |
| Real microphone/configured cloud STT/current visible VerseVIEW | **UNVERIFIED** for these final builds; no spoken user input or approved currently observed target was available in this run. Prior reported successes are historical evidence only |
| Actual ATEM / Discord network / real local inference | **UNVERIFIED**; synthetic acceptance is explicitly labeled |
| Current Windows x64 / Intel Mac native build and install | **NOT RUN**. Existing matrix retained and new frozen connection check added; uncommitted working-tree changes have not been uploaded to a native runner |

All evidence paths above are relative to `desktop-preview/` unless specified.
QA callback/observer replay does not test microphone access, STT transport, cloud
recognition accuracy or visible presentation pixels. No STT algorithm change was
introduced in Groups 6–8.

## Failures investigated without weakening safeguards

- Legacy bare local endpoint was rejected by the new surface. It now uses the
  production normalizer after rejecting URLs containing embedded secrets.
- Conditional progress markup shifted connection-panel disclosure positions.
  A stable job container keeps the form structure consistent.
- Synthetic connection work was too short to guarantee a poll saw its busy state.
  Only explicit QA work delay was increased; production timeouts/retries are unchanged.
- An old pending UI timeout could clear a newer request. Timeout now checks its ID.
- Older detection harness used a class selector that is now shared by ten fieldsets.
  It now selects the named Detection behavior group; the controls were present.
- Older watcher smoke sent during the real cooldown and expected `failed` for a
  repeated invalid identity. It now previews, waits beyond the normal cooldown,
  sends once, and requires the current `rejected` result for a repeated send.
  Delivery guards were retained. Initial failing logs are preserved with `initial-`
  prefixes in test-results. This does not explain the original intermittent incident.
- Long generated-note scrolling had previously been unverified because the fixture
  was short. The QA completion now contains 180 explicitly synthetic points and a
  final marker; the existing bounded scroll surface passed without a layout rewrite.
- The first diagnostic stress fixture used the wrong publisher argument shape.
  It was corrected to the existing `event` envelope; no production fix was needed.

## Files changed in Groups 6–8

New: `desktop_options.py`, `desktop_connections.py`,
`desktop-preview/profile-transfer.cjs`, `desktop-preview/src/options-policy.js`,
`desktop-preview/src/connections.js`, focused connection/unit/UI/diagnostic tests,
`desktop-preview/scripts/smoke-connections.py`, the 79-field current settings audit,
and this report/Groups 6–7 report.

Updated: typed settings/backend/control/notes guards; narrow preload/main command,
feed and transfer boundaries; Settings/Live/About rendering and styles; package
allowlists, companion source inventory, version 0.15.7; existing native CI matrix
with connection smoke; QA long-note fixture and older regression selectors/timing;
investigation and parity checklists. All prior Groups 1–5 edits are retained.
`.DS_Store` files are unrelated and remain excluded from intended commits.

## Remaining actions and installation procedure

1. After the Mac is unlocked, inspect this exact app in an isolated QA profile with
   Computer Use: default/resized Studio/Focus, native Glass over other windows,
   form focus, real native Google import/export dialog, diagnostics, independent
   note/transcript scrolling and accessible safety controls. Finish item 30 only
   after recording the observed result.
2. Upload a reviewed, scoped source commit to a `codex/` branch and run the existing
   desktop-preview native matrix. Verify current revision, Windows Setup install/
   uninstall, Intel/ARM packages and retained diagnostics. A historic successful
   main run at `13111da` is not evidence for these uncommitted features. Do not push
   to main merely to obtain a test build: its workflow auto-publishes a beta.
3. Before any fresh real presentation test, resolve the exact current VerseVIEW
   instance/output and obtain the requested isolation approval. Capture spoken
   phrase, raw provider text, candidate/attempt IDs, guards/queue/approval, command
   acceptance and observed verse pixels with timestamps. If hardware/user speech
   is unavailable, retain that label or ask the user for an explicit scope waiver.
4. When replacement is approved, Stop & Save and quit the old detector; retain a
   backup of its bundle and desktop profile. Extract the verified single-app ZIP,
   then replace `/Applications/VerseView Detector.app` with this app. Launch it and
   verify version, retained settings/sessions, microphone/provider/output and theme.
   Keep the previous app backup until acceptance. Existing saved profile path is
   retained; do not delete it or reset credentials. No unattended updater is used.
5. An ad-hoc signed downloaded Mac app can still trigger Gatekeeper. Paid signing/
   notarization was deliberately deferred by the user. No quarantine removal,
   security override, certificate installation or security-setting change was made.

Temporary changes were confined to named disposable QA profiles, synthetic source
settings and exports. Their cleanup removes only test-owned profiles/files; source
settings are checked unchanged. Build environments, artifacts and diagnostic
reports are retained for reproducibility. The real app, real keys, sessions, sync
link and system display preferences were not changed in this work. The original
intermittent delivery incident remains **unresolved**.
