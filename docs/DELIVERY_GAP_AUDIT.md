# Final delivery gap audit — 2026-10-18

**[████████████░░░░] 75% — 6 of 8 milestones complete.**
The original intermittent incident remains unresolved. Proven code defects were
fixed, and useful live behaviors were observed in earlier versions, but there
is no matched original-incident trace establishing a single cause. The current
Electron preview has isolated verification, not physical speech/output acceptance.

## Scope and evidence

This audit inspected source/history, existing reports and preserved evidence.
No suites/builds were repeated, application launched, provider contacted,
presentation command sent or setting changed. The reviewed repository HEAD was
`02653ac02bbd297a58a0bb0e6db7580cfafa82fd`; the final tested application source
is `af3334529cdfbb543b0083ab7949cbfa26bd204b` (preview 0.11.1). Later changes
in this audit are documentation only.

| Finding | Strongest support | Limit |
| --- | --- | --- |
| Old chapter suppression was defective | Historical source at `0d3bd38` compares only book/chapter, refreshes the timer on rejection, and sets presented state before later checks/send. Current `VerseController.send_verse` requires the exact prior reference and commits accepted history after the PRESENT click. Existing regression assertions cover changed verses, non-extending suppression and failed-send retry. | Establishes a defect and its correction, not that it caused the user's original incident. |
| Failed pre-click work no longer poisons delivered history | Current input/connection failure paths do not commit accepted state. Click exceptions use separate uncertain-send tracking; tests assert no blind retry and retained accepted state after an ancillary error. | Uncertain click delivery still requires inspecting the real output. No server/output acknowledgement exists. |
| Queue replacement and local routing have focused support | Current generation checks invalidate old range fetches; queue/VTC checks use `_role_has_llm`; existing tests cover delayed old workers, local-only routing, identity/stream retention, expiry and errors. | Actual local/cloud semantic release with real speech and visible output remains unverified. A configured model/client being available is not proof its semantic response will match. |
| Older source visibly changed John 3:16 → 3:17 | Preserved 32-event source trace contains acceptances at `04:46:27.531535Z` and `04:46:35.618144Z` on Oct 4: **8.086609 s** apart. The investigation records native output screenshot/AX observations of both references and verse text. Manual John 3:18 was also observed after approval. | Entered at the transcript callback, bypassing microphone/STT and normal Start orchestration. Original screenshots were returned in the earlier chat, not exported as standalone files; the event JSON alone does not prove pixels. This was source code, not the current Electron artifact. |
| Older packaged app used real microphone/STT | Preserved application log: `f18bae740e3d` accepted John 3:16 at `13:34:28.888018Z`; `1c71b4d67b84` accepted John 3:17 at `13:34:51.466562Z` on Oct 4. Packaged process/microphone evidence and reported Deepgram recognition support real speech transport. | **22.578544 s** apart, so the requested ten-second case did not pass. Visible output at those acceptances was not captured. Provider text is available, not an independent recorded waveform. This is the older Python test app. |
| Those repeated references were explained suppressions | `9f037adeb504` reports `chapter_dedup` with 0.340374 s remaining; `b935c4606b99` reports `DEDUP_WINDOW` with 39.591388 s remaining. | These are expected duplicate cases, not examples of the original unexplained non-delivery. |
| Historical connection/STT warnings have limited scope | The investigation records older ChromeDriver/connection-refused initialization errors. The later microphone log closes Deepgram at 08:35:40, after the accepted references. | Initialization errors are not a matched detected-but-undelivered example. The later shutdown trigger is unknown; it does not establish that an accepted reference failed downstream or that continuous listening passed. |
| Current preview contains and exercises the fixes | Native/source inventories and frozen callbacks, packaged candidate/approval/bilingual UI checks, 149 Python/49 Node tests and final three-platform native CI are recorded in the installation report. | Speech/providers/browser services were synthetic in these preview checks. Native Windows CLI execution is not Windows GUI or microphone acceptance. |
| Migration defects were repaired separately | Recovery validation, view/session acknowledgement, stale replies and setup/footer issues have saved failures and focused/package verification. | They arose in the new migration workflow; no evidence links them to the older intermittent incident. |

Evidence: [source events](evidence/2026-10-03-delivery/events.json),
[source actions](evidence/2026-10-03-delivery/actions.jsonl),
[older packaged log](evidence/2026-10-04-packaged/application.log),
[packaged process evidence](evidence/2026-10-04-packaged/process-microphone.json),
[investigation](DELIVERY_INVESTIGATION.md),
[current installation verification](../desktop-preview/INSTALLATION_VERIFICATION.md).

## Where non-delivery can correctly occur

Current code routes STT callbacks through `create_transcript_handler` or
`create_sarvam_transcript_handler`, `_process_transcript_blob` and the detection
paths, then `deliver_verse` and `VerseController.send_verse`. Range candidates
instead wait in `queue_verse_range` / `check_verse_queue`; Verse Interrupt uses
`_start_vtc` / `check_vtc` when configured.

| Last confirmed observation | Next stage to establish |
| --- | --- |
| User spoke, but STT text is missing/wrong | Microphone, selected device, transport/provider recognition. Do not label it a downstream delivery failure. |
| Correct reference appears only in transcript | Candidate extraction/filtering and normalization. Transcript text is not a detected candidate. |
| DETECTED followed by SUPPRESSED | Read the guard/reason and remaining time; compare with recorded settings/context. Worship, passage lock, confidence, hear-twice, duplicate and quarantine rules can be intentional. |
| MANUAL_CONFIRM_REQUIRED or QUEUED | Follow the same candidate ID to approval/rejection or queue release/cancellation/expiry/failure. Neither intermediate state is delivery. |
| DELIVERY_REQUESTED without COMMAND_ACCEPTED | Inspect controller/control availability and failure/uncertainty events. A missing event is not proof that no code ran. |
| COMMAND_ACCEPTED but wrong/no visible verse | Browser click returned; VerseVIEW target/routing/rendered output is the first unconfirmed stage. Capture the actual presentation reference and text. Do not infer a parser failure or blindly resend. |

`COMMAND_ACCEPTED` means Selenium returned from setting the reference and
clicking PRESENT. There is no emitted `PRESENTATION_CONFIRMED`. Failures during
click can be uncertain and are guarded separately for `max(20, DEDUP_WINDOW)`
seconds. No new retry should be added to bypass that uncertainty.

Range release requires fetched verse text, an available configured verse-role
model, a fresh nonempty excerpt, semantic match and successful guarded send.
Checks are paced at least three seconds apart. A missing model means waiting,
not successful delivery; range expiry is evaluated on later transcript callbacks
or cancellation on shutdown, not an independent wall-clock timer. The engine
checks return while semantic workers run; use the later correlated event rather
than a scheduling return value to determine delivery. The engine
keeps 300 events; legacy diagnostics displays 80, while the observer/feed bounds
are 192 delivery events and 48 transcript rows. Export the relevant private log
before bounded history rolls off. Do not copy API keys or unnecessary speech.

Current code references: `vv_streaming_master.py` lines 853–882 (events),
3554 (`deliver_verse`), 3993 (`check_vtc`), 4179 (`queue_verse_range`),
4225 (`check_verse_queue`), 4882 (`send_verse`), 6947 (transcript processing),
7150/7200 (callbacks); `vv_gui.py` 2672 (legacy diagnostics), and
`observer_feed.py` / `desktop-preview/engine-feed.cjs` (bounded projection).
Existing assertions are in `tests/test_delivery.py`; they were inspected, not
rerun by this audit.

## Historical settings cleanup requires review

The older packaged-test section explicitly ended with temporary settings and
build environment still in place. The later preview's clean QA shutdown does
not prove that older production-profile settings were restored.

A read-only hash on Oct 18 found the existing detector settings at
`~/Library/Application Support/VerseView/settings.json` differ from the recorded
Oct 3 baseline. Current SHA-256:
`e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`;
baseline: `67c625931f0b92d51156cc808b759005cdf79af7ff29eac7442544fc4e99df8b`.
The file modification time is `2026-10-05T05:06:16.951605Z`. Values were not
parsed or printed, and the file was not changed. A hash difference cannot
identify which settings changed or whether they reflect later user choices.

Before restoring anything, locate the earlier private backup and have the user
confirm the intended current settings. Review only the relevant temporary
changes: cleared webhooks/sync URL, automatic notes, inactivity timeout and
auto-start, plus any recorded test-specific values. Preserve a current private
backup and restore only agreed changes while affected apps are closed. Never
overwrite the whole current profile just because the hashes differ. The user's
2-minute battery / 10-minute adapter display preferences are permanent choices,
not detector-test settings to revert.

## Exact remaining user-action gates

1. **Resume physical acceptance (milestone 7).** The user must lift the physical
   test deferral and provide access to an unlocked Mac and an interactive Windows
   machine, their actual microphones/configured providers and VerseVIEW output.
   Resolve the current instance, URL, monitor and audience isolation. Obtain one
   scoped approval covering the resolved presentation target/test set before
   issuing commands; the old port/display description is historical evidence.
2. **One coordinated acceptance session on each OS.** Launch an identified
   native packaged artifact, record non-secret settings and process/build ID,
   and use actual spoken input. Speak John 3:16, then John 3:17 about four seconds
   later; repeat 3:17. Capture minimal STT output, stream/language, candidate ID,
   events/timestamps and actual visible reference/verse text. Observe both real
   English and Malayalam streams. Exercise a below-threshold contextual candidate
   for manual approval, retaining its ID; explicit FAST-PATH references normally
   bypass that hold. Check diagnostic scrolling/resizing and transcription,
   stop/recovery, native themes/accessibility and isolated outline routing during
   that same session. Record failures at the first failed/unknown stage.
3. **Live semantic queue only with working prerequisites.** Using the approved
   target and existing configured verse-role model, obtain a real queued range
   continuation and read its actual selected-translation verse text. Confirm
   fetch/client availability, fresh STT excerpt, same-ID release/send and visible
   output. The documented John 3:19–20 range is a starting scenario after suitable
   context, not a guaranteed reproduction. If no clear safe path or model is
   available, keep this case unverified; do not inject a match, disable guards or
   force a send to claim it passed. Test reversible connection recovery only on
   the isolated instance and inspect the screen before any uncertain resend.
4. **Agree production distribution (milestone 8).** After physical failures are
   addressed, obtain the user's chosen production identity/distribution scope
   and any required signing access/approval. Current ad-hoc Mac and unsigned
   Windows archives are development packages; OS trust prompts and Windows
   graphical install/update/rollback remain unverified. Do not weaken security
   or publish a release. Prepare and verify a side-by-side candidate using the
   existing process and the agreed profile migration/update/rollback plan.
5. **Replacement approval is last.** Present the exact accepted artifact/hash,
   destination, retained old app/private backup, restoration plan and remaining
   limitations. Request explicit approval before replacing the installed app.
   No current instruction grants that approval. Until then retain both artifacts
   and keep the operational app/profile intact.

To explain the original incident conclusively, obtain a recurrence or a matched
historical example: expected verse/time, minimal STT text and stream, candidate
ID, complete relevant stage/outcome trace, non-secret settings/build/adapter,
and actual output observation. Compare the last confirmed stage to the first
failed/unknown one. Successful demonstrations alone do not establish permanent
resolution of an intermittent problem.

These are the stopping gates. No further isolated feature migration or repeated
test run is justified solely by another continuation heartbeat. The
[installation guide](../desktop-preview/INSTALLATION_AND_ROLLBACK.md) and
[migration plan](DESKTOP_MIGRATION_PLAN.md) retain the detailed operational steps.
