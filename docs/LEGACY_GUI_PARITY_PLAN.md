# Legacy GUI parity and saved-session browser — proposed plan

October20,2026. Planning only: no application behavior, settings, saved sessions
or presentation output changed. This extends CONSUMER_UI_PLAN.md following the
user's request to inventory the old GUI before implementing further controls.
Overall migration progress remains6/8 (75%). Feature parity is not complete.

The [complete legacy GUI source audit](LEGACY_GUI_AUDIT.md) now supersedes the
preliminary inventory below as the coverage reference. It maps both GUI files,
all function definitions and control/binding sites, and all 75 explicit settings
plus four preserved profile fields. This is static source coverage, not a claim
that every control has been physically tested. Implementation has not begun in
this audit change.

## What the code establishes

- `vv_gui.py:_build_ui` contains Start/Stop, Worship, Pin, Update, transcript panes,
  verse history, chapter browsing/manual verse entry, suggestions, diagnostics,
  Clear Log, Generate Sermon Notes and Clear Memory. The right-hand Settings panel
  also includes context controls and configuration, which need separate treatment.
- `vv_gui.py:_toggle_worship_mode` toggles the engine's WORSHIP_MODE. Its UI log
  says detection is suspended, but `vv_streaming_master.py:VerseController.send_verse`
  actually gates delivery after detection. It sends no VerseVIEW command when on.
  The new UI must describe the actual behavior, not repeat the misleading label.
- `vv_gui.py:_panic_shortcut` calls `trigger_panic`, which clears/closes presentation;
  it is not the emergency-save action. `_emergency_quit` saves settings and a recovery
  snapshot, pauses Discord logging, force-stops recognition, kills its bot and exits,
  skipping summarization. These are distinct controls, not interchangeable labels.
- `desktop_recovery.py:SessionRecovery` currently has one restorable checkpoint:
  `Recovery/session.json`. Its projection includes sermon/context/history and bounded
  raw previews; it excludes settings, credentials, command state and outline notes.
- `desktop_backend.py:_save_session` also creates dated transcript/summary text files
  under `Sessions`. Those are archives to read, not full restorable checkpoints.
  Older text files cannot be relabelled as complete resumable sessions.
- The packaged backend checkpoints meaningful session content every15seconds and on
  stop/error. Saved settings are persisted separately. An abrupt kill can lose work
  since the last successful checkpoint; recovery of every final word or unsaved
  settings draft is not established and must not be promised.
- The new app already provides safe Start/Stop, Clear output, guarded approvals,
  suggestions, basic recovery, bilingual transcript views, settings sync, outline
  editing and a separate outline output. It does not yet have the complete legacy
  operator surface. GUI parity needs backend commands as well as new buttons.
- Shared service scheduling already applies on explicit Start, and startup local
  model warmup already runs from saved configuration. Their settings editors and
  manual local-model Test/Warm actions remain incomplete; do not rebuild these
  backend features. The audit also identifies legacy Worship reset ordering,
  direct Selenium sends, incomplete bilingual memory reset and recovery omissions
  that must not be copied into the new controls.

## Live layout

Keep the existing compact listening/safety header, reference result and speech
panels at the top. Preserve Focus / Full transcript, independent stream scrolling
and Jump to live. Place a compact row of operator tools below the speech panels:

`Saved sessions · Worship · Always on top · Verse tools · Notes · More`

Tools open a popup or expandable panel rather than permanently filling Live with
large cards. Emergency Stop & Save remains visibly reachable in the persistent
safety controls, including during long-page scrolling. It must not be hidden behind
Developer Mode or confused with Clear output. Speech setup stays below the primary
output as requested. Detailed defaults, credentials, provider/model tuning and
integration setup stay in Settings; raw diagnostics remain in Developer Mode.

## Complete operational inventory

| Legacy function | Proposed normal location / behavior | Current new-app gap |
| --- | --- | --- |
| Start / Stop and state | Persistent listening controls | Implemented; retain guards |
| Primary/secondary STT languages, providers and second-stream switch | Live Speech setup | Implemented; retain stopped-only saves |
| Primary/secondary speech display, Malayalam original/translation display | Live speech panels and compact display options | Basic separated streams implemented; audit original/transliteration view choices and resizable pane parity |
| Worship mode | Live toggle with persistent active indicator; detected reference/available verse text stays in Detector preview; nothing sent to VerseVIEW | New acknowledged runtime command/state projection needed |
| Pin / always on top | Live utility toggle for Detector window only | New narrow Electron main-process window action; native readback on Mac/Windows |
| Saved recovery / session selection | Small Saved sessions card opens session browser popup | Replace expanded recovery panel; add safe archive/checkpoint catalogue |
| Emergency Quit | Emergency Stop & Save, plus explicit Save & Quit variant | New AI-free save/quiesce/stop acknowledgement and controlled shutdown flow |
| Panic key / presentation clear | Keep Clear output separate; retain shortcut | Current Shift+Escape clears output; custom-key configuration remains Settings |
| Verse history / clear history / click past verse | Live Verse tools popup, with History retained as an alternate view | Add history selection and clear-history command; current History is a read-only event projection |
| Current book/chapter/verse, Set Context | Live Verse tools contextual controls | Add validated context-edit command; do not present merely by changing context |
| Chapter browser / select a verse | Live Verse tools popup | Add bounded chapter lookup/preview and guarded explicit Send |
| Manual reference entry | Live Verse tools, with Enter or explicit Send | Add parser validation and shared guarded delivery command |
| Verse text popup | Live reference/Verse tools preview | Feed currently lacks verse text; bounded lookup using selected Bible translation, with honest missing-text state |
| Context watcher suggestions / send / clear suggestions | Live suggestions, compact when empty | Existing send supported; add clear-suggestions runtime action |
| Clear Log | Live More → clear visible transcript view | Define as view-only clear; retain private session/recovery and diagnostics |
| Generate Sermon Notes / preview / save to file | Live Notes popup with explicit Generate and Export | Add on-demand summary command and native export; retain cloud budgets and free-only policy |
| Clear Memory | Live More → clear current sermon memory, visibly separate from Clear Log/output | New bounded reset command; protect active work with a restorable save and explicit destructive choice |
| AI Live Outline enable, preview/edit and audience display | Live Notes/Outline tool with access to existing Outline page; display target/open/close available from Live | Editing/output exists; add Live entry points and acknowledged enable control |
| Discord start/stop/status and live-log lifecycle | Live Integrations tool when configured | Bot runtime exists in Developer Runtime; add consumer entry point; tokens/setup stay Settings |
| Manual ATEM keyer on/off | Live Integrations tool only when configured | Needs an acknowledged integration command/status; credentials, IP, discovery/setup stay Settings |
| Update/check/apply update | Settings → About/Updates | Legacy updater is not automatically safe for Electron; retain separate packaging/release/signing work |
| Delivery logs, parser source IDs, raw provider errors | Developer Mode → Diagnostics | Already separated; do not bring diagnostic bloat back to normal Live |
| Microphone/refresh, Bible translation, target URL, approval thresholds, verification, detection options, Smart Amen, timing, model/prompt/provider credentials, schedules, Discord/ATEM connection setup, import/export and sync | Settings; advanced technical tuning in Developer Mode where appropriate | Existing settings cover only a subset. Audit the old Settings fields and add a typed migration backlog; do not silently reset unsupported saved options |

The old chapter-browser send writes Selenium fields directly. The new app must
not copy this bypass: manual entry, chapter selection, history resend and suggestion
send all use the same controller validation, worship, deduplication and delivery
checks. Configuration UI placement is separate from operational feature parity.

## Saved sessions popup

The compact card shows Saved sessions, count/status and latest save time. Clicking
it opens a keyboard-accessible modal with dated records and clear type badges:
Recovery, Saved session or Transcript only. Selecting a record opens its preview,
including available language streams, references, notes if saved, and save reason.

- Opening or selecting a record is read-only. It does not restore, listen, change
  current settings, present a verse or call a cloud summarizer.
- A Resume action is offered only for validated full checkpoints. While recognition
  is running it explains that listening must first be stopped. Preserve the current
  session before replacing its working context; do not overwrite the only recovery
  copy. Resume stages the selected context, then explicit Start resumes STT.
- Transcript-only legacy archives open in the viewer/export flow. A future Import
  as transcript action would need separate semantics and must not imply recovered
  parser anchors, multilingual originals or outline state that the file lacks.
- Add a private, versioned session library with immutable checkpoint IDs, dated
  snapshots and a current autosave pointer. Save on explicit Save session, normal
  Stop and emergency; autosave updates the current checkpoint without creating a
  new list row every15seconds. Original recovery remains supported/migratable.
- Save original speech for both languages, context/history and separately versioned
  outline/manual edits. Store display-language metadata, not credentials or complete
  settings. Restore cannot roll back provider keys, routes, budgets or account setup.
- Catalogue requests use opaque record IDs and bounded pages/previews, never arbitrary
  filesystem paths from the renderer. Handle corrupt, replaced, missing and oversized
  records explicitly. Popup Escape closes it and returns focus to its launcher.
- Archive deletion/retention is not introduced silently. Preserve existing records;
  expose intentional removal only with an appropriate recoverable operation or
  explicit irreversible-delete choice. Exports are explicit user actions.

## Worship, pinning and emergency semantics

Worship means STT and detection continue, results remain visible in the Detector,
and no new verse-delivery request reaches VerseVIEW. Existing presentation content
is not automatically cleared just because Worship turns on; Clear output remains
explicit. This plan interprets 'verse viewer' as the Detector's reference preview.
Selecting a reference inside VerseVIEW's own control-page preview would be a
separate behavior, since the old worship gate sends no VerseVIEW commands at all.

Publish authoritative worship state and the reason for suppressed references.
Apply the state before enabling delivery at Start. Keep an enabled state visible
and preserve it safely across restarts. Turning Worship off never flushes old
suppressed candidates or replays queued commands; wait for new eligible input or an
explicit guarded user send. Inspect timers, queues, bot/manual sends and in-flight
requests so a display-only toggle cannot accidentally leave another send path open.
An already accepted external command cannot be undone by toggling Worship.

Always on top affects the Detector operator window, not VerseVIEW or the outline
audience window. Persist the preference and acknowledge native state; handle OS
full-screen/workspace restrictions honestly instead of claiming universal stacking.

Emergency Stop & Save immediately blocks new delivery and cancels queued/timed
work, takes an AI-free consistent checkpoint, shuts down recognition/background
work and acknowledges the saved record ID/time. Keep the app available to inspect
save failures. Save & Quit adds owned-backend/bot shutdown and closes the app only
after the save result is known. Do not report Saved on a failed write, delete the
previous valid checkpoint, invoke summaries during emergency, or copy the legacy
unconditional os._exit path. Distinguish a partial/in-flight external delivery from
a confirmed clear/stop. Shortcut assignment must not conflate emergency with panic.

## Implementation sequence and completion checks

1. **Session browser and storage.** Add bounded archive/checkpoint metadata and
   preview API; compact card/modal; validate migration; stage selected recovery
   without starting STT. Check empty, one, multiple, transcript-only and corrupt
   records, an active session and keyboard/focus behavior.
2. **Core Live controls.** Add acknowledged Worship and native pinning, explicit
   Save session, Emergency Stop & Save / Save & Quit. Check restart persistence,
   failed/slow saves, emergency during startup/sync and delivery, no summarization,
   no stale-control commands, no worship queue catch-up and correct owned shutdown.
3. **Verse tools parity.** Add context, manual entry, history/chapter navigation,
   verse preview, clear-history and clear-suggestions actions through shared guards.
   Check ambiguous/invalid references, worship, deduplication and queue/manual rules.
4. **Notes and integrations.** Add Live access to outline/summary/export, intentional
   memory/log reset, configured Discord and ATEM operator controls. Preserve free
   usage gates; never contact services or present merely by opening a popup.
5. **Settings parity and packaging.** The static field/control audit is complete
   in LEGACY_GUI_AUDIT.md; implement its typed configuration backlog in bounded
   groups. Test saved settings separately from crash context, both speech
   streams, restored outline and disk failures. Package with the established build;
   inspect normal/narrow windows, keyboard, themes and Developer Mode on Mac, run
   native Windows CI and report Windows physical checks separately when unavailable.

This is a plan only. No controls, checkpoint formats, saved data, runtime modes,
application installation or system preferences were changed during this inventory.
