# Complete legacy GUI source audit

Audit date: October 20, 2026. Branch: `codex/desktop-backend`.
Base revision: `34cae83` (plan-only commit); current application behavior is the
0.12.1 / `fcac8c15` baseline. The audit adds documentation and source-derived
inventories only. It does not change application behavior or installed bundles.

## Scope and evidence

The static inventory covers the whole legacy GUI: Detector, Options, Advanced,
Discord, Live Points, child windows, shortcuts, timers, startup, recovery and exit.
Both GUI source files were inventoried, including nested callbacks and helper
functions. Configuration and engine/controller handlers were traced where needed
to distinguish what a control says from what it actually does.

| Coverage | Result |
| --- | --- |
| Legacy GUI sources | `vv_gui.py`: 4,598 lines; `live_points_app.py`: 205 lines |
| Function definitions | 178, including nested callbacks: 161 + 17 |
| Control/factory call sites | 114; helper/loop sites can produce multiple controls |
| Other explicit widget sites | 105 labels, containers, child windows and progress bars; fonts excluded |
| Event/timer/command binding sites | 86; these are not 86 keyboard shortcuts |
| Explicit collected settings | 75 |
| Additional preserved profile fields | 4; not editable widgets in the old GUI |
| Field mappings | All 79 have a status, runtime path, destination and gap |

The [coverage appendix](evidence/legacy-gui-audit/coverage.md) lists every function,
control/factory site, passive widget constructor and binding. The [machine-readable inventory](evidence/legacy-gui-audit/inventory.json)
records source hashes, source positions, calls, mutations, conditions and settings.
The [settings CSV](evidence/legacy-gui-audit/settings.csv) includes the full field-level
notes. Supporting source hashes establish the exact code used for this mapping;
they do not mean every supporting module received a whole-file audit.

**This completes a static GUI source inventory, not a runtime parity certification.**
No controls were clicked, microphones started, provider accounts tested or
presentation commands sent during this audit. Historical test results remain in
their existing verification reports. Current layout, native shortcuts, external
services and OS-specific behavior still require the relevant runtime checks.
No private user settings or credentials were read for this inventory.

## Status meanings

- **Implemented:** an equivalent current UI/control path exists in source. This
  label alone does not establish a new physical or end-to-end test result.
- **Partial:** backend behavior, saved configuration or some UI exists, but the
  complete operator/configuration workflow is absent or different.
- **Missing:** the new desktop surface has no equivalent operator command/workflow.
  The underlying engine may still contain the legacy helper.
- **Changed deliberately:** the newer ownership, safety or consumer design replaces
  the legacy behavior; restoring the old mechanism is not the parity objective.

Locations below describe the intended consumer layout. Operational tools belong
on Live, compactly below the reference and speech output. Configuration belongs
in Settings. Technical diagnostics and low-level tuning stay in Developer Mode.
This avoids recreating the old settings wall on Live.

## Operational feature matrix

| Legacy surface / handler | Current status and evidence | Destination / remaining work |
| --- | --- | --- |
| Start / Stop: `_start`, `_stop`, `_on_stopped` | Implemented: `EngineRuntime` + `DesktopControl`, session-scoped actions and states | Keep persistent listening controls |
| Primary language/provider: `_on_lang_changed`, `_stt_engine_code` | Implemented: typed stopped-only Live speech settings | Keep Live speech setup; preserve valid provider choices |
| Dual STT enable, secondary language/provider: `_on_dual_stt_toggle`, `_build_dual_stt` | Implemented: five speech settings cover both streams | Keep Live; do not combine stream identities |
| Primary/secondary transcript boxes and headers: `_append_log`, `_set_dual_log_view` | Implemented equivalents: separated speech, translation disclosure, Focus/Full and Jump to live | Retain clean speech views; full original-language display choices remain partial |
| Show Malayalam / transliteration | Partial: saved flags reach engine; observed speech/translation view exists | Compact Live display options; Settings defaults |
| Draggable transcript/suggestions splitters: callbacks at 463/567 | Changed deliberately: responsive panels and independently scrolling transcripts | Verify normal/narrow window usability; literal Tk pane geometry is unnecessary |
| Current reference and delivery diagnostics: `_update_delivery_diagnostics` | Implemented equivalents: reference result and structured outcomes | Simple result on Live; IDs/attempt details in Developer diagnostics |
| Manual approval: `_user_confirm_callback`, `_desktop_confirm` | Implemented: held candidate, Approve/Dismiss, session/candidate guards | Keep readily reachable on Live |
| Worship: `_toggle_worship_mode` | Missing desktop command/state; engine delivery gate remains | Live toggle, acknowledged active state; see delivery findings below |
| Pin: `_toggle_pin` | Missing native operator action | Live Always on top; apply only to Detector window |
| Clear presentation / panic: `_panic_shortcut` | Implemented Clear output and in-app Shift+Escape | Keep separate from stopping or saving recognition |
| Record panic key: `_record_panic_key` | Partial: saved engine key can feed Windows listener; no new recorder | Settings shortcuts; distinguish single-key Windows listener from in-app Mac shortcut |
| Emergency Quit: `_emergency_quit` | Missing dedicated save/quiesce/quit workflow; normal Stop/checkpoint exists | Persistent Emergency Stop & Save; explicit Save & Quit variant |
| Verse history/status badges: `_update_history_loop`, `_history_badge` | Partial: History is a structured event projection | Live Verse tools plus History view; add selectable prior references |
| Clear verse history: `_clear_verse_history` | Missing desktop action | Verse tools; state clearly which history/context is cleared |
| Manual verse entry / Enter: `_send_manual_verse` | Missing local normal UI; managed bot already has a guarded normalized goto path | Verse tools; parser validation and shared delivery controller |
| Current book/chapter/verse, Set Context: `_set_context`, `_refresh_context` | Partial: context exists/restores; no user editor | Verse tools; editing context alone must not present |
| Chapter browser / per-verse Send: `_update_chapter_browser_loop`, `_send_chapter_verse` | Missing desktop browse/lookup action | Verse tools; bounded preview and explicit guarded Send |
| Verse popup / Send Again: `_open_verse_popup` | Missing desktop verse-text popup; current feed reference does not supply verse text | Translation-aware lookup, honest unavailable state and guarded resend |
| Suggestions/status/expiry/send: `_build_suggestions_panel`, `_send_suggestion`, `_expire_suggestions_loop` | Implemented equivalent: suggestions inbox, expiry and guarded send | Keep compact on Live; technical cycle/provider counts in Developer |
| Clear suggestions: `_clear_suggestions` | Missing desktop action | Live suggestions tool; explicit clear without altering sermon memory |
| Clear Log: `_clear_log` | Missing equivalent view-only clear action | Live More; do not silently clear stored transcript or parser memory |
| Clear Memory: `_clear_sermon_memory` | Missing safe bounded reset workflow | Live More; protect work and reset both streams/context deliberately |
| Generate Sermon Notes: `_generate_summary` | Partial: automatic session summary exists, no normal on-demand command | Live Notes; existing free-cloud budgets and route restrictions apply |
| Notes preview / Save to File: `_show_summary_window` | Missing equivalent on-demand summary popup/export | Live Notes; native explicit export, generated vs saved status |
| Live Points AI enable: `LivePointsApp` | Partial: `SessionOutline.prepare` maps saved enable flag; no normal toggle | Live Notes/Outline enable with acknowledged state |
| Live Points prompt editor: `get_prompt`, `set_prompt` | Partial: saved prompt reaches engine; no new editor | Settings outline behavior |
| Editable Live Points preview / latest generated text | Implemented equivalent: `SessionOutline` editing and revision protection | Existing Outline page with a Live Notes entry point |
| Audience display open/close, screen/window choice, Escape | Implemented native output equivalent; legacy saved target not identical | Existing Outline output uses real monitor enumeration; Live shortcut and preference parity remain |
| Single crash-recovery prompt: `_check_restore_session` | Partial: validated recovery checkpoint and restore/discard card exist | Replace expanded card with small Saved sessions entry and browser |
| Multiple saved-session browsing | Missing in new app; legacy also had no full session catalogue | Add versioned catalogue; do not label dated text exports as restorable sessions |
| Autosave/recovery after abrupt exit: `_autosave_session_loop`, `_build_session_snapshot` | Partial: bounded atomic checkpoint every 15s and stop/error | Retain valid prior save; capture bilingual originals/outline explicitly; state crash-loss window |
| Emergency text file: `_emergency_save` | Partial: normal dated transcript/summary exports exist; no emergency command | Explicit AI-free save with truthful acknowledgement |
| Normal close / optional notes: `on_closing`, `_finish_close` | Partial: owned shutdown, stop checkpoint and normal-completion export/summary exist | Define save/summary/quit sequencing and failures; do not copy unconditional exit |
| Discord bot start/stop/log/status: `_build_bot_tab`, `_start_bot`, `_stop_bot` | Partial: managed bot controls exist in Developer Runtime | Configured integration controls on Live; token/guild setup in Settings |
| Bot launch with saved token at GUI startup: `_auto_start_bot` | Changed deliberately: managed bot requires explicit start | Do not restore automatic token-triggered launch silently |
| Discord live-log pause/resume/session message | Partial: engine logging works; recovery projection omits old message ID and old GUI resume call | Define resumed session logging; do not promise continuation of the old message |
| ATEM automatic integration: `_on_atem_toggle` and engine configuration | Partial: stored configuration reaches engine | Setup in Settings; operator state/actions on Live only when configured |
| ATEM IP scan / manual keyer: `_scan_atem_ip`, `_toggle_atem_keyer_manual` | Missing desktop discovery/manual action | Settings discovery; narrow acknowledged Live integration command |
| Microphone selection and Refresh: `_populate_mics` | Partial: selection exists; no equivalent explicit refresh workflow | Settings device refresh/status; avoid disruptive hot swap |
| Bible translation and VerseVIEW URL | Implemented typed Settings fields | Keep in Settings, preserve existing target validation |
| Options checkboxes/threshold: `_build_options` | Partial: stored values reach engine, forms absent | Settings detection; do not recreate uncontrolled direct global mutations |
| Advanced timing/providers/local models/watcher: `_build_advanced` | Partial: many values remain backend-supported; see all-field mapping | Settings setup and Developer tuning |
| Local model Test / Warm: `_test_local_llm`, `_warm_local_llm` | Partial: startup warmup exists, no manual Test/Warm actions | Settings Local models with bounded status/actions |
| Save Settings / Import / Export | Partial: narrow typed saves exist; arbitrary settings import/export UI absent | Settings; validate field subsets and explicit credential export choice |
| GCP credential import/status: `_import_gcp_credentials`, `_update_gcp_cred_status` | Partial: saved path/ADC and managed sync exist; picker/status absent | Settings Google credentials |
| Drive startup/manual sync: `_sync_settings_on_launch`, `_sync_settings_now` | Implemented equivalent: SettingsSync and connection status | Keep existing user-approved mechanism and allowed-field policy |
| Smart service schedule: `_get_scheduled_language`, `_apply_schedule_dual_stt` | Partial: shared `effective_start_settings` already runs on explicit Start | Settings schedule toggle/editor; not a missing engine feature |
| Auto-start recognition: `_check_auto_start` | Changed deliberately: new desktop launch stays stopped | Any future opt-in must be explicit; a saved legacy flag alone must not start listening |
| Automatic/manual update, dialog/progress/apply: `_manual_check_update`, `_show_update_dialog`, `_apply_update` | Missing Electron-equivalent release updater | Settings About/Updates; use production signing/release work, not legacy Python replacement logic |
| Log attachment, bot subprocess/bootstrap, Tk color/scroll helpers | Replaced by structured IPC, owned frozen backend/bot, CSS/native window architecture | Preserve functional outcome; do not port obsolete plumbing or every visual helper |

## Findings that affect implementation

### 1. Worship must have authoritative runtime state

The old GUI logs “verse detection suspended,” but
`vv_streaming_master.py:VerseController.send_verse` gates delivery after a reference
has been detected: Worship emits a suppressed outcome and returns before a
VerseVIEW command. Recognition/detection can continue. It does not clear existing
presentation content. The planned Detector preview must remain available.

There is also a static ordering defect: `vv_gui.py:_start` calls `configure` without
`worship_mode`; its default is false and configure assigns that value to
`WORSHIP_MODE`. A pre-Start legacy Worship toggle can therefore be reset while the
GUI toggle still appears active. This was found in source, not physically reproduced.
It is not evidence explaining the original intermittent incident.

The new command must publish acknowledged state, apply it before delivery starts,
cover manual/bot/queue/timer paths and never flush suppressed old candidates when
Worship is turned off. “Verse viewer” is interpreted as Detector preview. Selecting
VerseVIEW's control-page preview would be separate behavior: the old gate sends
no VerseVIEW command at all.

### 2. Port the verse tools through the guarded controller

Legacy `_send_manual_verse` and `_send_chapter_verse` write Selenium fields and click
Send directly. They bypass the shared delivery controller. The history popup calls
`deliver_verse(..., bypass_cooldown=True)` and logs “Re-sent” without checking the
return result; the suggestion handler does check acceptance before changing history.

The new manual, chapter, history and suggestion tools must share validation,
Worship, confirmation/queue rules, duplicate/staleness checks and honest acceptance
reporting. A request is not proof of visible output. Existing managed bot goto
already uses a guarded normalized path, so this is primarily a missing local UI
and command surface, not absence of all manual capability.

### 3. Clear output, Stop, Clear Log, Clear Memory and Emergency are different

Panic clears/closes presentation and cancels the Smart Amen timer; it is not an
emergency save or recognition stop. Clear Log only empties the two visible GUI
log boxes. Clear Memory calls `clear_sermon_buffer`, which clears the primary
transcript, cited verses and history; that helper does not clear the secondary
transcript/context in the same function. A new bilingual reset must define and
cover the whole intended session rather than copy this incomplete reset.

Legacy Emergency Quit attempts settings/snapshot saves, pauses Discord logging,
force-stops recognition, kills its bot and calls `os._exit(0)`. Save errors can be
logged and followed by exit anyway. The new workflow must block new delivery,
quiesce pending work, save without AI calls and report the save result. On failure,
retain the last valid checkpoint and leave an inspectable result. Emergency Stop &
Save and optional Save & Quit must stay distinct from Clear output and normal Stop.

The legacy Windows recorder stores one key name/character, despite chord-like
wording; the engine listener compares a single key. The Mac Shift+Escape binding
and new renderer shortcut are in-app, not verified system-wide shortcuts.

### 4. A recovery checkpoint is not a saved-session library

The legacy session store and current `Recovery/session.json` each hold one current
checkpoint. New dated files under `Sessions` are transcript/summary exports, not
full resumable records. Current recovery projects bounded bilingual transcript,
reference/history/context and a short raw preview, but excludes settings, keys,
old Discord message ID, command state and editable outline notes.

Normal checkpointing runs every 15 seconds and on stop/error. A hard kill can lose
work since the last successful write; an unsaved settings draft is not guaranteed
recoverable. Session browsing must distinguish full checkpoints from transcript-only
archives, preserve prior work before restore and never start recognition or present
merely because a record is selected. Full transcript history from the old session
is not automatically replayed into the new raw journal after checkpoint restore.

Legacy recovery embeds collected settings, including credentials, in its snapshot,
although its restore UI principally reapplies language and engine context. It tests
primary transcript/history for meaningful content, can overlook secondary-only work
and clears the old recovery file after the restore/discard decision even on restore
failure. The newer bounded projection should remain narrow. Do not copy these
loss/failure semantics into a multi-session library.

The new backend correctly stages engine restoration after configure. Legacy GUI
restoration happens before Start, while configure resets context and secondary
transcript. Keep the new ordering. Outline text survives a simple Stop in the same
backend object but is not included in the checkpoint and is lost on backend exit.
A versioned library needs explicit bilingual-original and outline/manual-edit data;
legacy text archives cannot supply data they never stored.

### 5. Backend support is broader than the editable new settings

`desktop_backend.configuration` intersects saved configuration with the engine's
configure signature. Profile updates preserve unrelated saved values. Therefore,
most absent fields are missing editors, not deleted functionality. Some legacy
checkboxes mutated running globals immediately; new stopped-only settings deliberately
avoid that pattern. New typed forms need explicit apply timing and acknowledgements.

Of the 75 explicit old collector fields, 16 currently have editable equivalents:
eight basic speech/device/VerseVIEW fields, seven credential fields and the Drive
URL. Fifty-six are partial and three intentionally changed. These are field counts,
not a feature-completion percentage. The four preserved profile fields add three
implemented entries and one partial free-cloud configuration entry.

Important exceptions to simple configure forwarding are recorded individually:

- Smart schedule already runs in `BackendHost.start` through
  `effective_start_settings`. It changes the effective Start configuration without
  saving it or starting recognition by itself. It retains the selected primary
  provider, then normal validation applies. A schedule editor/toggle is missing.
- Startup local-model warmup already runs through `SessionWarmup`; manual Test/Warm
  and the configuration editor are missing. Do not implement warmup again.
- Outline enable maps through `SessionOutline.prepare` and engine `live_points_enabled`.
- The old arbitrary bot `vv_host` / `vv_port` are replaced by an owned authenticated
  loopback bridge with a dynamic port; they are not settings to blindly restore.
- Recognition does not auto-start because an old profile contains `auto_start`.

The initial-load and language-change handlers in the old GUI expose inconsistent
provider lists. Use the new consistent language/provider policy rather than copy
those inconsistencies. Pin/Worship and old pane geometry were transient, not durable
fields in the collector; persistence for the new controls must be deliberate.

### 6. Notes, outline, integrations and connection management need distinct tools

On-demand summary/export is separate from AI live outline and normal-stop summary.
The old notes-generated flag can suppress later automatic summary even when the
notes were not exported; track generation and saving separately. Keep budget/free-only
rules when adding explicit Generate, and keep all AI calls out of emergency saving.

The new outline revision handling protects manual edits from an older AI result.
Keep this improvement. Opening the old audience window clears its preview via
`update_live_points("")`; opening a new output window must preserve current text.
Use Electron's real monitor selection instead of the old hardcoded second-screen
coordinate offset. Live should link to these tools without duplicating full pages.

Managed bot execution already exists in Developer Runtime, while token/guild setup
and consumer controls are missing. Automatic ATEM behavior can use stored settings,
but discovery and manual keyer controls require explicit narrow commands. Recovery
currently does not resume the old Discord live-log message ID. Do not claim that
integration lifecycle is fully restored just because speech/context resumes.

Settings export in the old GUI asks about portable GCP credentials, but other saved
API keys are normally in the exported dictionary. A future export flow needs an
explicit credentials choice. Existing Drive sync is unchanged: it transfers allowed
fields only; `gladia_api_key` is not currently in `SYNC_ALLOWED_KEYS`, even though
manual Gladia credential replacement exists. GCP has a separate managed transport.
Do not claim every credential is synced or silently change the user-approved sync
mechanism during this UI audit.

## Implementation order after this audit

1. **Saved sessions and core Live controls:** compact Saved sessions launcher/modal,
   versioned catalogue, preview vs resume, explicit Save, acknowledged Worship,
   native Always on top and Emergency Stop & Save / Save & Quit. Preserve existing
   recovery and text archives; do not move listening/output controls below tools.
2. **Verse tools:** context, validated manual entry, chapter lookup, selected history,
   verse preview, clear history/suggestions through the same delivery guards.
3. **Notes and configured integrations:** on-demand summary/export, safe reset tools,
   Live outline access/enable, configured bot/ATEM actions. Setup remains in Settings.
4. **Typed settings parity:** use the complete table below to add missing configuration
   surfaces in bounded groups; retain unknown saved values and existing free-cloud
   routes. Do not expose all raw model/audio knobs on normal Live.
5. **Verification and packaging:** focused command/state/storage tests as each feature
   lands; packaged normal/narrow-window and keyboard checks; settings/restart/disk-failure
   checks; real bilingual microphone and external-output checks when available.
   Windows native CI is separate from Windows physical verification. Existing production
   signing/release and approval requirements remain in force.

This audit is complete; implementation parity and physical verification remain
unfinished. Overall migration remains **6/8 milestones (75%)**. No progress percentage
is inferred from widget, method or settings-field counts. The original intermittent
delivery incident remains unresolved by this audit.

## Complete settings-field map

Documentation validation passed: all recorded source hashes and line counts match,
the AST inventory and appendix agree, all 79 CSV/JSON/report keys match and local
document links resolve. Whitespace checks also passed. No application test suite
was rerun for this documentation-only change; this audit adds no runtime pass claims.

All 75 explicit collector keys and four preserved profile keys appear below.
“Partial” usually means saved configuration is supported without a complete editor.
The CSV includes per-field source lines and runtime paths. Destination is planned
placement, not a claim that the missing form already exists.

| Field | Status | Destination | Gap / behavior |
| --- | --- | --- | --- |
| `language` | Implemented | Live Speech setup | Typed stopped-only setting |
| `bible_translation` | Implemented | Settings: microphone / VerseVIEW | Typed stopped-only setting |
| `display_screen` | Partial | Live Notes tool / existing Outline output | Native monitor/window selector exists on Outline; legacy screen preference is not the same persisted target |
| `remote_url` | Implemented | Settings: microphone / VerseVIEW | Typed stopped-only setting |
| `confidence` | Partial | Settings: detection behavior | Engine receives saved guard/behavior; editable control and legacy in-session toggle parity absent |
| `manual_confirm` | Partial | Settings: detection behavior | Engine receives saved guard/behavior; editable control and legacy in-session toggle parity absent |
| `verify` | Partial | Settings: detection behavior | Engine receives saved guard/behavior; editable control and legacy in-session toggle parity absent |
| `verse_interrupt` | Partial | Settings: detection behavior | Engine receives saved guard/behavior; editable control and legacy in-session toggle parity absent |
| `spoken_numeral_mode` | Partial | Settings: detection behavior | Engine receives saved guard/behavior; editable control and legacy in-session toggle parity absent |
| `smart_amen` | Partial | Settings: detection behavior | Engine receives saved guard/behavior; editable control and legacy in-session toggle parity absent |
| `auto_save_notes` | Partial | Settings: notes automation | Backend can generate summary on normal engine completion; legacy GUI generated on app close if notes had not been generated/saved |
| `auto_start` | Changed deliberately | Settings: Startup, if reintroduced | Stored value is not automatic recognition permission; current app launch stays stopped |
| `smart_schedule` | Partial | Settings: Startup / schedule | Backend applies shared timetable on explicit Start, without saving it; no editor/toggle in the new UI |
| `show_malayalam_raw` | Partial | Live speech display options | Raw observed speech and translation disclosure exist; legacy Show Malayalam switch is absent |
| `malayalam_transliteration` | Partial | Live language options / Settings default | Saved flag reaches engine; Sarvam transliteration toggle absent |
| `panic_key` | Partial | Settings: shortcuts | Shift+Escape exists; Windows engine may honor saved single key; no new key recorder and no verified global desktop shortcut parity |
| `dual_stt_enabled` | Implemented | Live Speech setup | Typed stopped-only setting |
| `secondary_language` | Implemented | Live Speech setup | Typed stopped-only setting |
| `secondary_stt_engine` | Implemented | Live Speech setup | Typed stopped-only setting |
| `stt_engine` | Implemented | Live Speech setup | Typed stopped-only setting |
| `assemblyai_api_key` | Implemented | Settings: Connections | Write-only replacement; saved key contents are not shown |
| `live_points_prompt` | Partial | Settings: outline behavior | Saved prompt reaches engine; new prompt editor absent |
| `live_points_llm_enabled` | Partial | Live Notes tool | Backend explicitly maps this flag to outline enabling; no normal UI enable toggle |
| `rate` | Partial | Developer: audio/timing | Saved value reaches engine configure; no typed editor in new UI |
| `chunk` | Partial | Developer: audio/timing | Saved value reaches engine configure; no typed editor in new UI |
| `cooldown` | Partial | Developer: audio/timing | Saved value reaches engine configure; no typed editor in new UI |
| `dedup_window` | Partial | Developer: audio/timing | Saved value reaches engine configure; no typed editor in new UI |
| `silence_timeout` | Partial | Developer: audio/timing | Saved value reaches engine configure; no typed editor in new UI |
| `aai_turn_cutoff` | Partial | Developer: audio/timing | Saved value reaches engine configure; no typed editor in new UI |
| `gcp_interim_flush` | Partial | Developer: audio/timing | Saved value reaches engine configure; no typed editor in new UI |
| `llm_enabled` | Partial | Developer: audio/timing | Saved value reaches engine configure; no typed editor in new UI |
| `deepgram_api_key` | Implemented | Settings: Connections | Write-only replacement; saved key contents are not shown |
| `groq_api_key` | Implemented | Settings: Connections | Write-only replacement; saved key contents are not shown |
| `gemini_api_key` | Implemented | Settings: Connections | Write-only replacement; saved key contents are not shown |
| `cerebras_api_key` | Partial | Settings: optional legacy connections | Preserved private values can feed legacy routing; no replacement field in new UI; do not replace reviewed free-only routes |
| `mistral_api_key` | Partial | Settings: optional legacy connections | Preserved private values can feed legacy routing; no replacement field in new UI; do not replace reviewed free-only routes |
| `sarvam_api_key` | Implemented | Settings: Connections | Write-only replacement; saved key contents are not shown |
| `sarvam_api_key_backup` | Implemented | Settings: Connections | Write-only replacement; saved key contents are not shown |
| `gladia_api_key` | Implemented | Settings: Connections | Write-only replacement; saved key contents are not shown |
| `gcp_credentials_path` | Partial | Settings: Google credentials | Existing private path/ADC and managed sync supported; no service-account import picker/status workflow |
| `local_whisper_endpoint` | Partial | Settings: speech connections | Provider can be selected and saved endpoint reaches engine; endpoint editor absent |
| `discord_webhook_url` | Partial | Settings: Discord/webhooks | Saved values and credential sync can supply engine webhooks; no new dedicated editor |
| `discord_log_webhook_url` | Partial | Settings: Discord/webhooks | Saved values and credential sync can supply engine webhooks; no new dedicated editor |
| `discord_notes_webhook_url` | Partial | Settings: Discord/webhooks | Saved values and credential sync can supply engine webhooks; no new dedicated editor |
| `mic_index` | Implemented | Settings: microphone / VerseVIEW | Typed stopped-only setting |
| `atem_enabled` | Partial | Settings: ATEM setup; Live integration actions | Automatic engine behavior can use saved values; setup/discovery/manual keyer controls are absent |
| `atem_ip` | Partial | Settings: ATEM setup; Live integration actions | Automatic engine behavior can use saved values; setup/discovery/manual keyer controls are absent |
| `atem_key_duration` | Partial | Settings: ATEM setup; Live integration actions | Automatic engine behavior can use saved values; setup/discovery/manual keyer controls are absent |
| `settings_sync_url` | Implemented | Settings: Connections | Drive download URL with startup/manual sync; supported formats are deliberately bounded |
| `local_llm_enabled` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_endpoint` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_auth_token` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_extra_headers` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_model` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_timeout` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_warm_at_start` | Partial | Settings: AI / Local models | Background warmup works from saved configuration; no editable toggle in the new UI |
| `local_llm_on_failure` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_role_verse` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_role_outline` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_role_summary` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_model_verse` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_model_outline` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `local_llm_model_summary` | Partial | Settings: AI / Local models | Saved configuration feeds engine; editor is absent; manual Test / Warm buttons are separately missing |
| `watcher_enabled` | Partial | Settings: watcher; Developer tuning | Engine receives saved setting; reviewed free-cloud routes/gap are not a replacement for this legacy toggle/parameter editor |
| `watcher_provider` | Partial | Settings: watcher; Developer tuning | Engine receives saved setting; reviewed free-cloud routes/gap are not a replacement for this legacy toggle/parameter editor |
| `watcher_batch_interval` | Partial | Settings: watcher; Developer tuning | Engine receives saved setting; reviewed free-cloud routes/gap are not a replacement for this legacy toggle/parameter editor |
| `watcher_auto_confidence` | Partial | Settings: watcher; Developer tuning | Engine receives saved setting; reviewed free-cloud routes/gap are not a replacement for this legacy toggle/parameter editor |
| `watcher_passive_confidence` | Partial | Settings: watcher; Developer tuning | Engine receives saved setting; reviewed free-cloud routes/gap are not a replacement for this legacy toggle/parameter editor |
| `watcher_window_lines` | Partial | Settings: watcher; Developer tuning | Engine receives saved setting; reviewed free-cloud routes/gap are not a replacement for this legacy toggle/parameter editor |
| `watcher_window_seconds` | Partial | Settings: watcher; Developer tuning | Engine receives saved setting; reviewed free-cloud routes/gap are not a replacement for this legacy toggle/parameter editor |
| `watcher_cooldown` | Partial | Settings: watcher; Developer tuning | Engine receives saved setting; reviewed free-cloud routes/gap are not a replacement for this legacy toggle/parameter editor |
| `discord_bot_token` | Partial | Settings: Discord setup | Managed bot reads these saved values; setup fields are absent from new forms |
| `vv_host` | Changed deliberately | Developer: integrations, if needed | Managed bot uses owned authenticated loopback bridge and a dynamic port, not these legacy arbitrary host/port fields |
| `vv_port` | Changed deliberately | Developer: integrations, if needed | Managed bot uses owned authenticated loopback bridge and a dynamic port, not these legacy arbitrary host/port fields |
| `vv_guild_id` | Partial | Settings: Discord setup | Managed bot reads these saved values; setup fields are absent from new forms |
| `free_cloud_enabled` | Implemented | Developer: Cloud tuning | Not a legacy editable widget; collector preserves this profile value. New editor exposes reviewed fields only. |
| `free_cloud_config` | Partial | Developer: Cloud tuning | Not a legacy editable widget; collector preserves this profile value. New editor exposes reviewed fields only. |
| `cloudflare_api_token` | Implemented | Settings: Connections | Not a legacy editable widget; collector preserves this profile value. New editor exposes reviewed fields only. |
| `cloudflare_account_id` | Implemented | Settings: Connections | Not a legacy editable widget; collector preserves this profile value. New editor exposes reviewed fields only. |
