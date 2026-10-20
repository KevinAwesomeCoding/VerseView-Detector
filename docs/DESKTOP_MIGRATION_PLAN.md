# Desktop migration progress

Overall: **[████████████░░░░] 75% — 6 of 8 milestones complete**

This is an engineering milestone count, not elapsed-time estimation or a
production-readiness score. The scope below is the current working baseline;
changes to scope can change the denominator. Physical acceptance remains partial;
the user completed several Mac spoken checks. Cross-platform build support
continues; interactive Windows physical acceptance is now deferred at the user's
explicit request, and is not claimed passed.

| # | Milestone | State / completion requirement |
| --- | --- | --- |
| 1 | Dashboard design and themes | Complete: approved interactive prototype, separate bilingual panels and themes. |
| 2 | Cross-platform desktop shell | Complete with isolated checks: separate Electron packages; Windows execution remains in milestone 7. |
| 3 | Bilingual engine event connection | Complete with isolated checks: raw speech, translation, candidate IDs and delivery outcomes. |
| 4 | Engine controls and manual decisions | Complete with isolated checks: start/stop requests, lifecycle status, exact-candidate approval/rejection. |
| 5 | Non-secret settings in the dashboard | Complete with isolated checks: microphone, languages/providers, dual STT, Bible translation and VerseVIEW URL; stopped-engine saves, validation, conflict handling and package verification. |
| 6 | Standalone backend integration and packaging | Complete within isolated scope: frozen companion/private profile, core lifecycle/settings/confirmation, Smart Schedule, recovery, warmup, watcher suggestions, outline notes/output, owned Discord bot controls and credential sync. Preview 0.11.0 passes all three native CI targets and eight packaged Mac suites. |
| 7 | Physical acceptance | Partial: Mac rapid spoken delivery/duplicate and manual approval pass with user-observed output; dual-STT transport/panels pass with recorded backup-key limitation. Live semantic release and remaining Mac checks are open. Windows physical is explicitly deferred, not passed. |
| 8 | Installation and replacement readiness | In progress: isolated Mac portable install/update/uninstall/reinstall and rollback pass; migration/rollback guide is written. Production identity/signing/distribution, remaining Mac acceptance and explicit replacement approval remain open. Windows graphical lifecycle is deferred and remains unverified. |

Completed milestones have the limits recorded in their verification reports.
They do not establish real speech transport, visible presentation, Windows
runtime correctness, or the cause of the original intermittent incident.

Milestone 6 final source `b2555dd5228d08930e5f5448aa922c9429eb7699` passes
149 Python tests, 48 Node tests and eight same-artifact Mac packaged suites
covering 252 layout cases. Windows x64, Mac ARM64 and Intel Mac native CI
build/frozen-smoke/package/extracted-archive checks pass in run 39124243081.
See [settings sync verification](../desktop-preview/SYNC_VERIFICATION.md)
for exact artifacts, preserved failure evidence and synthetic transport limits.

Preview 0.11.1 verifies installation/update/uninstall/reinstall/rollback in a
separate Mac location and disposable profile, with actual packaged 0.10.0 and
0.11.1 applications. It fixes obsolete external-detector guidance and a stale
connection footer in the owned-backend view. See the
[installation report](../desktop-preview/INSTALLATION_VERIFICATION.md) and
[migration/rollback guide](../desktop-preview/INSTALLATION_AND_ROLLBACK.md).
The installed detector remains intact. Milestone 7 remains partial; see the later
physical checkpoint. Production replacement and a release are not authorized; the open gates above prevent
counting milestone 8 complete.

Final 0.11.1 native CI run 39139494109 passed on all three targets, with 149
Python and 49 Node tests, frozen feature checks and extracted archives. Local
readiness, core backend and sync packaged checks passed on the exact final app.
No additional isolated feature migration is currently scheduled. Do not repeat
completed builds/suites without a source change, failure or unresolved concern.
The next acceptance work requires coordinated spoken input and Windows access;
production distribution/replacement decisions
remain separate. Do not start live services or replace the installed app merely
because an automation asks to continue.

See the [final incident/gap audit](DELIVERY_GAP_AUDIT.md) for the supported
findings and exact remaining user actions. It also records an older packaged
test's unfinished settings-restoration claim; current QA cleanup must not be
treated as proof that those historical settings were restored. Any restoration
needs review of the user's intended current values before changing them.

Update this file and include the bar in future progress updates and completion
reports. Count a milestone only after its implementation and scoped verification
are complete. Latest completed milestone: standalone integration (preview 0.11.0).
Two milestones remain; 25% remains by milestone count. Preparation for milestone
8 can proceed now; physical acceptance and replacement approval remain release gates.


October 18 physical checkpoint: [report](../desktop-preview/PHYSICAL_VERIFICATION.md).
The user approved the resolved isolated Mac target and microphone access. The actual
0.11.1 microphone/provider connected, but the user is away and synthetic acoustic
playback produced no text. Speech cases remain explicitly unverified. Native UI,
windowed bilingual outline and 0.11.2 closed-feed status checks passed. Temporary
preview settings were restored; all owned hosts are closed. Progress stays 75%.

Final 0.11.2 native CI 39147884519 passed all three targets (149 Python / 50 Node,
frozen features and extracted archives). This supports the status correction,
without closing the human speech, visible verse or Windows graphical gates.

Later October 18 user-spoken 0.11.2 checkpoint: real microphone/Deepgram recognition
and PRESENT command execution for 3:16/3:17 passed, 23.564752 seconds apart.
A colloquial spoken-number phrase parsed chapter-only, and a split 3:17 transcript
was held by verification. Native populated Activity scrolling passed while stopped.
Actual visible verse output, rapid timing and remaining physical gates stay open;
see the latest investigation entry. No guard was disabled. Progress remains 75%.

15:12 CDT repeat: actual packaged 0.11.2 English STT recognized all three full
phrases. John3:16/3:17 commands were accepted9.475974s apart; repeat3:17 was
suppressed by exact-reference cooldown without another send. The user confirms
both visible verses worked and repeat did not retrigger. These cases pass within
that evidence scope; exact verse-text capture and remaining physical cases stay
open. Progress remains6/8,75%; original incident unresolved.

October 19 manual test: real speech held contextual John 3:18 for30.197168seconds
before user approval; same-ID PRESENT command accepted afterward. Hold/approval
command path passes; the user explicitly confirms visible 3:17 while held and
3:18 only after approval. Visible reference behavior passes by user observation.
Temporary preview confidence90%→75% restored, all other values preserved, production
profile untouched, recognition stopped. Other physical gates remain; progress75%.

October19 bilingual follow-up: real concurrent English/Deepgram and Malayalam/Sarvam
transport, source attribution and native panels pass with a recorded limitation:
Sarvam primary quota errors caused the existing automatic saved-backup fallback.
No reference commands were generated; bilingual shared delivery/dedup and accurate
translation are unverified. Recognition stopped; all8temporary key changes restored
to exact prior semantic values/presence. Review primary quota before another provider
run. Windows/semantic/remaining gates stay open; progress6/8,75%.

October20: semantic readiness exposed an unavailable hardcoded Groq model (404,
missing from account listing).0.11.3 compatibility fix and151 Python/50 Node,
all3nativeCI/package checks pass. The actual new Mac app is prepared, stopped,
awaiting human semantic queue speech. See the semantic preparation report. Windows
physical checks are now deferred by the user; retain that limitation rather than
blocking all Mac production preparation. Progress remains6/8,75%.

Later October20: the real semantic queue release passed by command evidence and
the user's visible-output confirmation; see the latest investigation entry for
its screenshot limitation. A separate0.11.4 Mac ARM64 free-cloud LLM candidate now
passes169 Python/50 Node checks, frozen startup/package/archive and fake-provider
watcher guard checks. Verified account plans and bilingual probes select different
English/Malayalam watcher routes with shared budgets. This adds no completed
overall milestone: candidate microphone/outline acceptance, recurring-free STT,
and production replacement/signing remain open. The installed app and active
settings were not changed. Details: [free-cloud audit](FREE_CLOUD_API_AUDIT.md).
