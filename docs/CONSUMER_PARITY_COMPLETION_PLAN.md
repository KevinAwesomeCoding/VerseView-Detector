# Consumer parity completion plan

October 21, 2026. Baseline: main at 62c990b, Electron 0.15.1.
Groups 1–7 are now implemented in separate test artifacts; see
[Group 1 verification](DETECTION_CONTROLS_VERIFICATION.md) and
[Group 2 verification](LIVE_LAYOUT_VERIFICATION.md) and
[Group 3 verification](CHAPTER_WATCHER_VERIFICATION.md) and
[Group 4 verification](SERMON_NOTES_VERIFICATION.md) and
[Group 5 verification](SESSION_SETUP_VERIFICATION.md).
This document is the current implementation checklist for the user's latest
requirements. It supersedes conflicting placement recommendations in the older
LEGACY_GUI_PARITY_PLAN.md; the older audit remains supporting source evidence.
The original planning pass changed no runtime. Group 1–7 code/test changes are now
tracked below; the installed app and user settings remain unchanged.

## What is already present, and what remains incomplete

These are source findings, not new physical-test results.

| Area | Current evidence and gap |
| --- | --- |
| Remote connection | `vv_streaming_master.py:main` already tries five times, with five-second waits between failures, and emits terminal `connection_failed`. Group 1 added structured attempt/status events and a consumer failure/retry surface; Group 2 retains these beside the controls. Backend IPC connectivity is different from VerseVIEW connectivity. |
| Detection options | `vv_gui.py:_build_options` exposes confidence, manual confirmation, hear-twice verification, verse interrupt, spoken numerals and Smart Amen. Saved options still feed the backend, but the initial `desktop-preview/src/settings-policy.js` boundary allowed only eight basic speech/connection fields plus cloud settings. Group 1 extended the typed boundary and exposed these six detection options in normal Settings. |
| Wrong-reference incident | The current live-session evidence shows unmarked `John three seventeen` becoming chapter-only John 3, then being upgraded to remembered 3:18. Full chapter/verse wording produced correct commands. Group 1 removed that substitution; real speech/output retesting remains separate. It does not conclusively explain the original older incident. |
| Live safety/tools | Start/Stop, emergency save, Worship, pinning and Save session already exist in `observer.js`/`operator.js`; Group 2 completed the requested header/sidebar relocation. Clear output and Emergency Stop & Save have different meanings. |
| History and chapter tools | `verse-tools.js` provides Context, History and Chapter tabs; Group 2 moved reference entry/preview to Live and added a current-chapter shortcut. Group 3 adds a local KJV-number grid, current-context highlighting, read-only preview and explicit guarded Send; chapter text remains paged eight verses at a time. Clear current history retains saved sessions and diagnostic evidence. |
| Watcher | Group 3 adds normal enable/provider settings, Developer Mode tuning, evidence-based status, bilingual Preview/Display/Dismiss/Clear and an explicit desktop approval-only engine flag. Expiring/revision/epoch-bound advice cannot automatically present, even through the high-confidence watcher branch. Free cloud routing/budgets remain in effect. |
| Session saving | Recovery checkpoints and session-library saves already exist. `desktop_backend.py` checkpoints at 15-second intervals while active, saves on normal stop, and exposes explicit/emergency saves. These are not the same as generated sermon notes or an exported transcript. |
| Sermon notes | Group 4 adds normal Generate/Preview/Export, snapshot-bound bilingual source, cancellation/failure retention, native Unicode export and transcript-first automatic saving. Clear Memory saves a recoverable backup and diagnostic archive before resetting working state. Emergency saves deliberately skip summarization. |
| Outline | Editable live outline and separate output exist; they must remain distinct from a final sermon summary. |
| Local AI | Saved routing/configuration and startup warmup already exist. A complete settings editor and explicit Test connection/Warm selected model actions remain missing. |
| Session setup | Group 5 adds labeled supplied-text/translation/transliteration views, stream-limited Sarvam transliteration configuration, fresh per-computer startup opt-in/countdown/cancel, a timezone-aware timetable editor with next-Start preview, and a configurable focused-window panic shortcut. Legacy startup flags never enable listening. Actual provider/OS/platform checks remain separate. |
| Other setup | GCP import, ATEM setup/manual control, local-model editors and low-level option editors still need desktop workflows. |
| Updates | Legacy Python updater exists. No verified Electron update checker/apply workflow should be implied by a legacy or placeholder button. |

Source references: `vv_gui.py:_build_ui`, `_build_options`, `_build_advanced`,
`_build_suggestions_panel`, `_on_close`; `desktop_backend.py`, `desktop_control.py`,
`desktop_sessions.py`, `desktop_operator.py`, `desktop_verses.py`,
`desktop_suggestions.py`, `desktop_warmup.py`; `desktop-preview/src/observer.js`,
`operator.js`, `verse-tools.js`, `settings.js`, `settings-policy.js`, `cloud-settings.js`.
The prior audit includes a field-by-field inventory of all 75 legacy settings and
four preserved fields in `docs/evidence/legacy-gui-audit/settings.csv`.

## Intended layout

**Live header:** Start/Stop, Emergency Stop & Save, Worship, Always on top and Save
session together. Keep the safety controls usable when scrolling and at narrow
widths. Show connection/readiness status and a small expandable activity strip
near these controls. Plain-language status belongs in normal mode; raw logs do not.

**Live body:** prominent reference/result, followed by independently scrolling
English/Malayalam speech panes. Retain Focus/Full transcript and Jump to live,
including smooth scrolling with reduced-motion support. Put the manual Bible
reference input directly below the transcripts, with Preview reference beside it.
Preview shows verse text and an explicit Send action; typing/previewing alone
does not present anything.

**Nearby tools:** Verse tools retains Context and the full Chapter browser; retain
selectable History as well. Add a compact current-chapter access control beside
Verse tools, opening a verse-number grid without making operators hunt through
tabs. Clearly marked verse buttons provide an intentional guarded presentation
action, with a separate read-only preview option. This replaces the need for a
large permanently expanded chapter/text card. Suggestions appear compactly below
the reference-entry row and expand when there is advice or an error to review.

**Workspace sidebar:** Saved sessions opens the existing browser; show latest-save
status/count if available. It remains different from the header's Save session.
Keep access on narrow windows through a labelled navigation/menu equivalent.
Notes opens Generate/Preview/Export and existing Outline tools. More contains
Clear visible transcript, Clear history, Clear suggestions and Clear memory.

**Settings:** Detection behavior; Language/display; Session/startup; Schedule;
Provider connections including Google credentials; AI watcher; Local models;
ATEM/integrations; Keyboard shortcuts; About/updates. Keep normal choices usable
without Developer Mode. Technical timing, model overrides and diagnostic detail
belong in Developer Mode. Preserve existing themes, profile and credential sync.

## Implementation checklist — groups of four

Each numbered item is a work package, not one checkbox in the final UI. Complete
one group, verify it, and report its result before proceeding to the next group.
Current completion is **20/32 work packages (62.5%)**; existing functionality
is reused rather than counted as newly completed. Packages differ in effort, so
this is a scope checklist, not an estimated percentage of hours or total historical
project progress. Only Groups 1–7 are checked; external physical/platform checks retain the limits in
the verification report.

### Group 1 — Connection visibility and detection correctness

- [x] **1. Remote connection lifecycle.** Publish Connecting, attempt 1/5 through
  5/5, retry delay, Connected and terminal failure, with timestamps and safe error
  categories. Clearly distinguish remote unavailable, browser/driver failure,
  backend disconnected, microphone failure and provider failure. Retry is an
  explicit new bounded attempt sequence after the old one ends; no blind retries.
- [x] **2. Prevent remembered-verse substitution.** Fix the evidenced chapter-only
  upgrade so ambiguous/chapter-only input cannot silently present an unrelated
  remembered verse. Preserve chapter context, history and explicit operator
  navigation. Add regression coverage using the recorded phrase sequence and
  restored high-water state. Do not change STT to conceal a downstream bug.
- [x] **3. Approval and verification settings.** Add editable confidence threshold,
  Require manual confirmation and Require verification/hear twice. Explain that
  manual confirmation applies to low-confidence detections and verification is
  a separate rule; high-confidence fast-path behavior must be accurately described.
  Show saved/effective values and when changes apply.
- [x] **4. Remaining detection switches.** Add Verse Interrupt, Spoken Numeral Mode
  and Smart Amen with accurate descriptions and visible effective state. Validate
  full/shorthand references, repeated input, queue release/cancel/expiry, and
  prayer-trigger clearing. Smart Amen clears the presentation, not the app or
  transcript; timers must cancel correctly on Stop/emergency/mode changes.

### Group 2 — Live controls and navigation

- [x] **5. Consolidated header.** Move Worship, Always on top and Save session beside
  Start/Stop and Emergency Stop & Save. Preserve acknowledged states, keyboard
  access, narrow-window wrapping and persistent emergency reachability.
- [x] **6. Saved sessions in workspace navigation.** Move its launcher to the
  sidebar; retain browser popup, dated records, read-only previews, resume/start-new
  choices and save status. Make pending recovery obvious beside Start, with a
  direct route to resolve it instead of appearing to ignore a click.
- [x] **7. Reference entry below transcripts.** Move the existing validated input
  and adjacent Preview reference action into Live. Reuse existing preview/Send
  backend commands; preserve drafts/focus through feed updates and show parse,
  lookup and delivery outcomes honestly.
- [x] **8. Verse tools and transcript layout.** Keep Context/Chapter/History in the
  tools popup; add nearby quick chapter access. Keep language panes, stream status,
  Full transcript scrolling, Jump to live and essential controls usable across
  themes, default size and resized windows without duplicate crowded tool rows.

### Group 3 — Chapter navigation, history and watcher

- [x] **9. Current-chapter verse-number grid.** Follow the acknowledged book/chapter
  context and display every valid verse number with current selection highlighted.
  John 3 must show 1–36 for the supported standard chapter table, not a guessed
  1–20. Use a validated complete local count table for supported canon; identify
  translation/versification differences or unavailable counts explicitly. Verse
  numbers need no STT/LLM call; verse text uses existing cache/lookup only on demand.
- [x] **10. Guarded chapter/history actions.** Make nearby verse buttons and past
  references easy to select, preview and intentionally send. Reuse existing send
  policy, rather than copying legacy direct Selenium writes or introducing new
  cooldown bypasses. Report actual acceptance/suppression; add Clear history with
  defined scope, separate from deleting saved sessions or diagnostic evidence.
- [x] **11. Watcher setup and status.** Add enable/provider settings and visible
  Off, Waiting, Scanning, Suggested, Missing credentials, Rate limited and Failed
  states as supported by actual evidence. Preserve English/Malayalam attribution;
  settings access must exist even while the watcher is disabled. Technical batch
  interval, thresholds, window size and cooldown belong in Developer Mode.
- [x] **12. Watcher approval inbox.** Match the requested ask-before-display flow:
  show reference/reason, Preview, Display and Dismiss/Clear suggestions. Explicitly
  reconcile the existing automatic-suggestion path so this mode cannot send before
  approval. Handle stale/expired/replaced suggestions, worship, stop and active
  sends; retain budget/free-only policy and never claim a suggestion was displayed
  merely because it was generated.

### Group 4 — Sermon notes and clearing actions

- [x] **13. Generate Sermon Notes.** Add Live Notes action with generation progress,
  cancel/failure/empty-session handling and configured provider/model readback.
  Generate from an identified session snapshot, retaining both speech streams and
  reference history where applicable. Reuse the summary engine; preserve existing
  cloud allowance rules and keep Outline distinct from final notes.
- [x] **14. Notes and transcript export.** Preview generated notes and save/export
  notes, transcript and reference list through explicit native file actions. Show
  destination and success/failure. Preserve originals, language labels and Unicode;
  do not silently export a truncated recovery preview as the complete transcript.
- [x] **15. Auto-save notes and save visibility.** Expose the existing auto-save
  preference and define save-on-Stop versus normal-close semantics. Show saving,
  saved time/location, summary pending/failed, and transcript availability. Retain
  AI-free emergency saves and crash checkpoints even when AI summarization is off.
- [x] **16. Clear Memory and related clear actions.** Add a deliberate current-session
  memory reset covering both languages, parser context/high-water, suggestions,
  queues, outline and summary working state as appropriate. Present exact scope,
  save a recoverable snapshot first and cancel in-flight work. Distinguish Clear
  memory from Clear visible transcript, Clear history, Clear suggestions and Clear
  output. Existing saved sessions/credentials must not be silently deleted.

### Group 5 — Language, startup and keyboard behavior

- [x] **17. Language/transliteration options.** Add Malayalam transliteration with
  provider/language availability and original/translated/transliterated display
  choices. Keep primary/secondary languages and enable controls on Live. Preserve
  saved originals and avoid presenting transliteration as unchanged raw speech.
- [x] **18. Session/startup preferences.** Expose supported startup choices, including
  an explicit opt-in Auto-start on launch. A legacy saved flag alone must not
  activate microphone capture after migration. Recovery choice, sync readiness,
  permission/device/provider state and stop/cancel still take precedence.
- [x] **19. Smart Schedule.** Expose enable, schedule/time-zone view and editor using
  existing schedule resolution; show selected language/dual-stream configuration
  before starting. Do not silently change live speech streams mid-session.
  Interpret the user's “remote schedule” as the existing Smart Schedule; any
  separate remote scheduling feature requires a distinct specification.
- [x] **20. Panic keyboard shortcut.** Expose current shortcut and a validated custom
  binding on Mac/Windows, conflict/reset behavior and honest in-app/global scope.
  Panic clears presentation; Emergency Stop & Save is a different action. Preserve
  popup Escape and text editing, and report unsupported OS registration explicitly.

### Group 6 — Connections, integrations and local AI

- [x] **21. Google credentials and sync.** Add service-account JSON picker, validation,
  managed private copy and presence/status readback. Retain existing approved Drive
  sync, manual pull/conflict results, basic provider credentials and saved-profile
  migration. Add validated settings import/export with explicit credential scope;
  never expose service-account private keys or tokens in UI logs or diagnostics.
- [x] **22. ATEM Chroma Key overlay.** Add enable, IP/discovery, duration and explicit
  test/manual Keyer On/Off controls/status. Setup stays in Settings; configured
  operator controls are accessible from Live integrations. Hardware/network tests
  require the actual resolved target and appropriate approval; otherwise report
  unavailable. Do not infer hardware success from a mock.
- [x] **23. Local model setup.** Expose enable, endpoint, authentication presence,
  per-role routing/model selection, startup warm preference and cloud-fallback
  policy. Keep custom headers/timeouts/model overrides in Developer Mode. Include
  existing Local Whisper endpoint setup separately from text-generation LLM setup.
- [x] **24. Test connection and Warm selected model.** Add bounded explicit actions
  with effective endpoint/model, progress/cancel/result. Reuse existing resolution
  and startup warmup; do not download models implicitly. Expose configured Discord
  runtime controls through Live integrations while retaining credential setup in
  Settings and existing guarded backend ownership.

### Group 7 — Developer controls, settings integrity and updates

- [x] **25. Audio/timing settings.** Add sample rate, chunk size, cooldown, duplicate
  window (confirm whether a distinct debounce exists rather than inventing one),
  silence timeout, AssemblyAI turn cutoff and GCP interim flush. Enforce typed
  ranges/units/provider applicability, stopped-only application where required and
  effective-value readback. Keep this group in Developer Mode.
- [x] **26. AI/watch tuning and diagnostics.** Add LLM fallback, model/provider tuning,
  watcher batching/confidence/windows/cooldowns, and structured diagnostic detail.
  Preserve actual provider failures and candidate IDs without secrets. Normal Live
  keeps human-readable progress/errors; Developer Mode is not required to learn
  why listening or delivery failed.
- [x] **27. Full settings persistence audit.** Reconcile every legacy field in the
  existing 79-field inventory against the new forms/backend boundary. Preserve
  unknown/unexposed saved fields, credentials and unsaved-draft conflict behavior.
  Verify restart/migration and stale revision rejection. Label unsupported options
  honestly instead of offering controls that do nothing.
- [x] **28. About/updates.** Remove any nonfunctional Check for update affordance;
  offer an honest current-version/release-page action initially. A later actual
  checker must distinguish available, up-to-date, offline and failed, and select
  the correct channel/platform/architecture. Do not port the Python self-replacer
  into Electron or promise unattended installation without a tested update path.
  Paid signing/notarization remains optional per the user's decision.

### Group 8 — Packaged acceptance and delivery

- [x] **29. Focused regression coverage.** Test settings validation/persistence,
  connecting/retrying/failed/cancelled status, saved recovery, wrong-verse phrase
  sequence, all manual send origins, clear/reset races and summary/export failures.
  Use isolated fakes for deterministic failures without labelling them real STT.
- [ ] **30. Packaged visual checks.** Build a separate artifact through existing
  scripts. Use Computer Use on default/resized windows, all themes, keyboard/focus,
  independent scrolling and popups. Confirm controls stay usable during continuous
  transcription; no new UI redesign beyond the requested layout.
- [ ] **31. Real-path and native-platform checks.** Verify microphone/provider text,
  candidate ID, confirmation/queue/delivery stages and actual visible output using
  an approved isolated target. Exercise disconnected remote/recovery. Run Windows
  and Intel native CI; audio fixtures may test real recognition, but injected text
  and mocked CI do not prove physical microphone/display operation. Mark unavailable
  hardware checks unverified rather than blocking unrelated completed work forever.
- [x] **32. Release and handoff.** Record exact source/build provenance, files changed,
  tests and limits; update investigation/parity documents and installation guidance.
  Keep the installed app intact until replacement is approved. Report remaining
  failures and original-incident uncertainty. Restore temporary settings and clean
  disposable test environments without removing user sessions or credentials.

## Completion rules

A package is done only when the intended control is discoverable, its backend
operation is acknowledged, errors have a useful visible result, persistence works
where applicable and focused checks pass. Source presence alone is not completion.
Reusing an existing feature requires checking its revised placement and workflow.

All configuration additions must extend the shared typed Electron/Python settings
boundary; no arbitrary renderer-to-filesystem writes. Live actions must use owned,
session-bound commands. Preserve STT provider behavior and delivery guards. Do not
add blind retries or disable validation to obtain output. Distinguish recognition,
parsing, contextual interpretation, queued approval, controller acceptance and
observed pixels throughout troubleshooting.

Progress reports should show the current group (0/4 through 4/4) and total checked
packages (0/32 through 32/32), plus separate physical checks that are unverified.
Do not carry the older 75% milestone figure forward as a claim of full parity.

Current scope: **Group 8: 2/4 complete**. Total **30/32 (93.75%)**. Current-code Windows/Intel/Apple Silicon preview CI passed at `5798877` (run `39786390395`). Native Google import was acknowledged, but screenshot/AX mismatch and native export-save availability remain unresolved. The user is away from the Mac; items 30–31 retain visual and real microphone/output acceptance gaps. See [Final acceptance and handoff](FINAL_PARITY_ACCEPTANCE.md). Groups 6–7 verification: [Connections and Developer settings](CONNECTIONS_DEVELOPER_VERIFICATION.md).

**Owner scope change, October 22:** items 30–31 are deferred for later testing at
the owner's explicit request to release now. They remain unchecked. Release is
authorized through the existing verified beta workflow; pause the repeating task
after publication is confirmed, without claiming those tests passed.
