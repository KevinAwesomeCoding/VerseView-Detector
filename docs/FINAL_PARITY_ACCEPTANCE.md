# Final parity acceptance and handoff

October 22, 2026 (Chicago). Groups 1–7 and Group 8 items 29/32 are complete:
**30/32 (93.75%)**. This is not full physical or native-platform acceptance.
Item 30 still needs completion of native Computer Use visual acceptance; item 31
still needs available real-path acceptance. Current-code native Windows, Intel
Mac and Apple Silicon CI now pass (see the continuation below).
The user subsequently deferred the two remaining tests and explicitly requested
release (see release decision below). They remain unverified, not passed. Do not
rerun completed tests while these same external conditions remain unchanged.

## Exact artifact and provenance

- Version **0.15.7**, branch `main`, base
  `62c990b213cbf997d61745670073a016937ca22d`, plus uncommitted Groups 1–8 work.
  This describes the local artifact's build-time provenance. The same runtime
  source is now committed on `codex/consumer-parity`; see below. The installed app
  is unchanged. No release or security changes were made.
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
| Current native Mac Computer Use / real file chooser / external Glass backdrop | **PARTIAL**: native navigation and synthetic Google JSON import acknowledged. Screenshot/AX mismatch and export Save availability remain unresolved; see continuation. External Glass backdrop remains unverified |
| Real microphone/configured cloud STT/current visible VerseVIEW | **UNVERIFIED** for these final builds; no spoken user input or approved currently observed target was available in this run. Prior reported successes are historical evidence only |
| Actual ATEM / Discord network / real local inference | **UNVERIFIED**; synthetic acceptance is explicitly labeled |
| Current Windows x64 / Intel Mac / Apple Silicon native CI | **PASS**, run `39786390395` at `5798877`; all three native jobs, frozen checks, package verification and archive acceptance passed. Windows archive acceptance includes isolated silent install/runtime/uninstall checks. Physical Windows microphone/display remains unverified |

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

1. When the user returns to the Mac, complete inspection of this exact app in an isolated QA profile with
   Computer Use: default/resized Studio/Focus, native Glass over other windows,
   form focus, real native Google import/export dialog, diagnostics, independent
   note/transcript scrolling and accessible safety controls. Finish item 30 only
   after recording the observed result.
2. Native preview matrix is complete at `5798877` on `codex/consumer-parity`.
   Reuse that evidence while runtime source is unchanged. Do not push to main
   merely to obtain a test build: its workflow auto-publishes a beta.
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

## October 22 continuation — approved preview push and native acceptance

The user explicitly approved the preview branch commit/push and CI. The scoped
runtime changes were committed as `cca4923`; `e4fe028` adds a push trigger limited
to `codex/consumer-parity` to the existing preview workflow. No release publishing
was added and main was not changed. Unrelated `.DS_Store` files remain excluded.

Initial run `39785851547` passed both Mac jobs but failed three Windows notes tests:
the tests decoded UTF-8 Malayalam files using Windows' default cp1252 encoding.
Commit `5798877c96884e0a2c5de56683c85588743f445a` makes those notes/connections
test and smoke-file reads explicitly UTF-8. It changes no application runtime or
STT behavior. Focused notes/connections suites passed locally. The subsequent
[native preview run](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39786390395)
passed all three platforms, including frozen companion regressions, final package
verification and extracted/installed archive acceptance. Native Windows testing
here is CI software acceptance, not physical audio or visible VerseVIEW testing.

Retained local evidence: `desktop-preview/test-results/native-ci/` contains the
successful run/job/artifact metadata, initial Windows annotations and focused
encoding-check logs. The three retained GitHub preview artifacts are Windows x64
`12430350097`, Intel Mac `12429791598` and Apple Silicon `12427929572`. These are
preview CI artifacts, not a published release or an installed replacement.

The exact local 0.15.7 executable above ran as PID 33803, with owned frozen backend
33922 in disposable `QA/native-audit-20261022`, using `--verify-isolated`, synthetic
credentials, callback replay and a fake controller. Native accessibility actions
opened Settings and the real Google JSON chooser, selected a nonfunctional QA
JSON, and received “Import saved” / “Google service-account key: Configured.”
Credential-free export preparation was acknowledged and the native save sheet
opened. Save remained disabled during this attempt; the sheet was cancelled.
No export save success is claimed.

Native capture repeatedly showed an older Ready/Live surface while accessibility
reported Settings and current outcomes. Coordinate actions also reported
`noWindowsAvailable`; a Finder capture and VerseVIEW window lookup failed too.
The screenshot/AX discrepancy is preserved in
`desktop-preview/test-results/native-computer-use/`, alongside import/export AX
records. This does not establish an application rendering defect or a successful
visual pass. No runtime change was made on this uncertain evidence. Form focus,
fresh resized pixels, native independent scrolling and external Glass backdrop
still need observation. Automated packaged layout/scrolling evidence above remains
valid but does not replace this native pass.

The saved real configuration was read without changing it: English/Deepgram,
secondary stream off, microphone index 2 (currently Kevin’s iPhone Microphone),
remote `http://127.0.0.1:50010/control.html`. The remote refused connection during
read-only inspection. No real microphone capture or presentation command was
started. The user then reported being outside; remaining physical/native visual
checks wait for their return, current target resolution and isolation approval.
The idle QA profile and its synthetic import are retained for that continuation;
their cleanup is not yet claimed. Real settings and installed app are untouched.
Progress remains **30/32**; the original incident remains **unresolved**.

### User-confirmed foreground follow-up

The user answered “I see Settings” to the pending foreground-window question.
The next native screenshot also showed Settings, matching accessibility. This
supports stale native capture in the earlier attempt; it does not establish an
application freeze. No runtime fix was justified by that discrepancy.

With fresh capture available, native Settings scrolling reached Appearance and
About while the safety controls remained accessible. The Window layout label and
Studio selector aligned. Native Live captures for Sage, Midnight, Galaxy, Aurora
and Ember showed readable reference status, last-sent reference, separate English
and Malayalam panels and usable header controls. They are retained as
`native-computer-use/live-{sage,midnight,galaxy,aurora,ember}.jpg`. These five
captures use existing synthetic transcript data and the system's dark appearance.

Switching back to Glass produced ScreenCaptureKit invalid-parameter and
accessibility invalid-element errors; a refreshed native handle confirmed Glass
selected, but subsequent captures again showed older Ember pixels. The file named
`live-glass.jpg` is preserved as evidence of that mismatch, **not** a Glass pass.
Native half-screen resizing similarly returned a cropped older bitmap, so it
does not establish narrow-window layout success. The native Return to Previous
Size action was used afterward. Final accessibility records Settings,
Glass/Studio, verification microphone and engine stopped in
`native-computer-use/post-theme-restore-ax.txt`. Real settings were not changed.
Item 30 remains partial: Glass/backdrop, reliable resized pixels, native independent
scrolling/focus under incoming transcripts and completed native export save remain
unverified. No real microphone or presentation test was started.

### Owner release decision — October 22

The user explicitly instructed: “ill do the two test later, just release the app.”
Release is authorized with items 30–31 deferred; the checklist remains 30/32
verified rather than relabeling those checks as passed. The separate visual chat
is idle and reports that it stopped without changing the acceptance docs or
starting speech/presentation. Its last reported QA surface was Verse tools.

Publish through the existing main-push three-platform build/release workflow,
retaining its beta designation and verification gates. The release notes state
that final native visual and real microphone/STT-to-visible-output acceptance are
deferred. Paid publisher signing/notarization remains intentionally omitted.
Publication does not replace the installed app, change real settings or establish
a cause for the original incident. Once publication is verified, pause the
repeating parity task under this explicit scope change; physical checks resume
when the owner requests them.

### First release attempt: Windows fixture failure

Main release run `39797998800` passed both Mac jobs but failed the Windows Node
regression step at “Clear Memory follows only its exact acknowledged rotation and
stays stopped.” Publication was correctly skipped. Public check annotations retain
the failing test identity; full private runner logs were not accessible through
the unauthenticated API.

A controlled local reproduction fixed file modification times across the test's
same-size in-place writes. The reader then reused the cached wrong-ack snapshot
and kept the old session, reproducing the failing assertion. Production
`ObserverPublisher` uses a temporary file and `os.replace`, unlike those fixture
writes. The command fixtures now use temporary-file/rename publication too. The
Clear Memory test deliberately retains identical modification times for wrong and
correct acknowledgements, and still requires rejection of the wrong ID and a
stopped state after the correct rotation. All 18 command tests and all 99 desktop
unit tests pass locally; whitespace checks pass. This is a test-only correction,
not a runtime cache/STT/delivery change. The corrected native release run must
still pass before publication is claimed.
