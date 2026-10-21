# Verse delivery investigation

## October20: committed candidate, native CI and separate Mac installation

Provider and consumer Settings changes were committed/pushed on the existing
`codex/desktop-backend` branch as1e01b24fddc65e9e000b08335f891b7470b3006e;
unrelated.DS_Store stayed excluded.174 Python/53 Node checks passed, and
[native CI39494833854](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39494833854)
passed Windows x64, Intel Mac and Apple Silicon Mac package/archive/frozen checks.
The exact-commit0.11.6 Mac build was independently verified and installed in a
separate versioned user Applications directory. Its actual packaged app/backend
run from that location; recognition remains stopped and Drive sync is up to date.
A private profile backup was verified; original installed app and production
settings are intact. No new live speech/presentation test was claimed.

Per the user's direction to skip unavailable work, Apple distribution signing/
notarization was skipped after a read-only check found0valid signing identities;
Windows publisher signing is unconfigured and physical Windows acceptance stays
deferred. Ad-hoc signature checks passed; no security protections were weakened.
The production workflow still targets the legacy app; main/release publishing were
not changed. See [release readiness](../desktop-preview/RELEASE_READINESS.md) for
artifact digests, local install/rollback details and remaining acceptance limits.
Original intermittent incident remains unresolved; no installed-app replacement
was performed.

## October20: cloud Settings integrated in packaged0.11.6

The managed dashboard now exposes reviewed per-feature cloud routes, masked
write-only credential updates, lower-only usage controls and Drive credential-sync
configuration.174 Python/53 Node tests and package/archive/frozen startup checks
pass. Computer Use exercised saved Drive settings, a fixture sync and dummy-key
save against the actual isolated packaged backend while recognition stayed stopped.
No real inference, microphone or presentation was started for this integration.
See [Cloud Settings verification](../desktop-preview/CLOUD_SETTINGS_VERIFICATION.md)
for exact build provenance, limitations and scoped test evidence. Existing provider
work is still uncommitted; original installed app and production settings remain
intact. Overall6/8,75%; original incident unresolved.

## October 20: revised Drive credential JSON and Cloudflare sync support

Validation: all 170 Python tests, page checks, package verification and extracted frozen startup passed for 0.11.5. Archive `2026-10-20T18-23-18-934Z-e039a0d2-darwin-arm64.tar.gz`; SHA-256 `f997a4dbc4437ff1d6d812a03bcb2c492c0b376a3af07b3a90b1aea8acd0b40f`. Runtime manifest source hashes match; no microphone or presentation started.

A private revised JSON was saved outside the repository in Downloads. All 52
existing Drive fields are preserved; the two added fields are the scoped
Cloudflare API token and account ID. Existing Groq and Gemini credentials match
the verified candidate profile. The Drive download succeeded without signing in:
anyone possessing that link can read the credentials. No Drive upload or sharing
permission change was performed.

Credential sync now permits the two Cloudflare fields. A regression test verifies
that syncing these credentials neither enables free-cloud mode nor replaces local
provider routes. The replacement JSON therefore carries credentials; activating
the reviewed provider configuration remains a separate local action. Production
and normal preview settings remain untouched. Candidate version 0.11.5 includes
this sync compatibility update; the earlier 0.11.4 artifact is retained.

## October20: free cloud LLM routing and isolated candidate verified

**[████████████░░░░] 75% —6/8 milestones, unchanged.** An opt-in free-only LLM
profile now selects Groq Qwen3.8-27B for verse/semantic checks and the Malayalam
watcher, Cloudflare Qwen3-30B-A3B for the English watcher, and Gemini
Flash-Lite3.5 for summaries/outlines. The language split follows measured failures:
Cloudflare Qwen missed a Malayalam Psalm paraphrase and returned Romans8:21 for
spoken8:28; Groq passed all6 Malayalam watcher cases and10/10 verse/semantic cases.
Flash3.8 returned503 for long and short summary probes; this is preserved as a
transport result, not an invalid-key claim. Two synthetic bilingual Flash-Lite
summaries retained the tested content, with recorded quote-section/formatting
limitations. No private sermon or session transcript was uploaded.

Actual personal-account recurring free plans, model quotas and saved-key suffixes
were checked. The user approved the displayed Groq/Cloudflare terms and explicitly
requested creation of an account-scoped Workers AI Read/Edit token. It is stored
privately in an **inactive separate candidate profile**. No billing/payment was
added. One browser sign-in result included a temporary authentication token in a
redirect URL before filtering; the newly created API token was kept private, and
no credential or such URL was saved in repository evidence.

The implementation shares request/token/neuron budgets across streams/features,
reserves Groq verse capacity, applies a20s global watcher floor to timer **and**
volume triggers, alternates stream priority, caches unchanged work, checks complete
bilingual summary token counts and surfaces safe actionable failures. No automatic
paid/provider fallback or retry was introduced. Free mode suppresses Sarvam's
quota-backup-key rotation at runtime. Saved production provider settings, local
model opt-in state and delivery/manual/verification/dedup/semantic guards remain
intact; local clients are bypassed in the explicit free profile.

**PASS169 Python/50 Node tests**, syntax/offline-page and whitespace checks;
separate0.11.4 Mac ARM64 frozen startup, package inventory/existing ad-hoc
verification, archive extraction/extracted startup, and existing frozen fake-provider
bilingual watcher/manual/duplicate/stopped-action checks. Runtime hashes match the
frozen manifest. HEAD remains`e039a0d2`, with uncommitted runtime changes and prior
uncommitted reports preserved. The prior all-platform CI pass is not extended to
this source state. No real microphone or presentation command occurred.

The [updated audit](FREE_CLOUD_API_AUDIT.md) records exact artifacts/hash, account
checks, public fixtures, failures, privacy and capacity arithmetic. At20s globally,
180 watcher calls/hour are shared by both streams: the measured sizes suggest up
to6h40 English, about2h continuous Malayalam alone, or4h English+Malayalam before
other optional Groq use. These are conditional estimates, not promised duration.
Five usual summaries plus ten tests fit the configured20-attempt feature cap when
token/minute/account capacity remains.

Production settings retain hash
`e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`;
active preview settings and `/Applications/VerseView Detector.app` were not written.
The candidate was not activated or installed. A coordinated candidate microphone/
outline test and recurring-free streaming STT integration remain separate gates:
Deepgram/Sarvam signup grants do not establish perpetual free operation. Windows
physical testing remains deferred; original intermittent delivery incident remains
unresolved. No dependency install, signing configuration change or release.

## October20 09:43–09:45 CDT: real spoken semantic queue release passed

The user approved testing on the Mac's main screen with no external display and
completed the actual microphone test, then stopped the engine. Deepgram recognized
“John chapter three verse nineteen.” at09:43:21.138; candidate006ec6480792 was
command-accepted at09:43:21.165227. The spoken contextual range queued John3:20.
Repeating the range cancelled/replaced the first queue candidate as designed;
replacement215db52966d4 reached semantic-ready QUEUED at09:43:49.749181.

Groq rejected the range announcement and the first partial verse excerpt (NO).
Deepgram then recognized “For everyone that doeth evil,”, “hateth the light,” and
“neither cometh to the light,” at09:44:47.436,48.749 and50.772. Semantic matching
returned YES at09:44:53.005. The same queue candidate215db52966d4 emitted
DELIVERY_REQUESTED at09:44:53.010580 and COMMAND_ACCEPTED at09:44:53.021304,
within its180-second lifetime. The remaining spoken text “lest his deeds should
be reproved.” arrived at09:44:54.886. Shutdown completed at09:45:12.387.

**PASS:** real microphone/STT → contextual range → ready queue → semantic match →
same-candidate command acceptance. The user independently reports that reading
the verse visibly worked. **Visual evidence limitation:** retrospective Computer
Use reached VerseVIEW's controller, whose history includes John3:20 and3:19, but
did not capture the actual presentation window/text during the transition. This
is user-confirmed visible success, not an automated screenshot-confirmed transition.
Do not equate controller history or command acceptance with presentation pixels.

Scoped logs are preserved locally at
`desktop-preview/test-results/semantic-queue-20261020/spoken-queue-events.log`;
unrelated captured conversation is excluded. Recognition remains stopped; no
settings changed during this inspection. The unrelated Cerebras402 startup result
did not prevent the Groq semantic path. Discord empty-URL errors followed accepted
commands and are a separate integration configuration issue. The aggregate
“LLM calls:0” shutdown line contradicts detailed semantic calls and must not be
used to infer zero semantic usage. Original intermittent incident remains unresolved.

## October20: semantic queue blocker corrected; live test prepared

The user explicitly deferred interactive Windows physical testing and asked to
proceed with semantic release before production installation/signing. Read-only
inspection found cloud verse matching prefers configured Groq, independently of
Cerebras billing. A single bounded old-model request returned404; account model
listing omitted the hardcoded model. Verse-text fetch passed. An available Groq
model passed positive/negative semantic probes with bounded instruct-mode output.
The minimal0.11.3 compatibility correction passes151 Python/50 Node tests, native
CI39393732698 on all3targets, packaged lifecycle, inventory/signature/archive and
frozen startup checks. No delivery guards or retry policy changed.

The actual rebuilt normal app19755 and frozen backend19764 are running from the
new artifact, with recognition stopped and saved recovery staged/Start enabled.
Preview settings equal the restored baseline; production settings unchanged,
installed app intact. Actual spoken queue release is still UNVERIFIED and requires
the user's next coordinated test. Windows physical is deferred, not passed; it does
not block preparing a Mac production candidate. See the
[semantic preparation report](../desktop-preview/SEMANTIC_QUEUE_VERIFICATION.md)
for exact provenance, preflight limits and live phrases. Original incident remains
unresolved; progress6/8,75%.


## 2026-10-19 23:47–23:51 CDT: physical bilingual transport and panel results

The user completed actual spoken English/Malayalam checks in the normal packaged
0.11.2 app, source `e54b905fabe60ebfcf60f61916a15ab67079bb11`, build
`2026-10-18T17-04-40-349Z-e54b905f-darwin-arm64`, backend PID **72557**.
Latest recognition session: `733a9222c7f74894906b89db808d8190`. UTC events are
October20; local times here are October19, America/Chicago (CDT).

**PASS for concurrent real provider transport, stream attribution and native
panel rendering, with the Sarvam backup-key limitation below.** The latest
snapshot contains two primary final transcripts, eight secondary final transcripts,
and one primary interim. Computer Use observed actual English/Deepgram and
Malayalam/Sarvam panels, with the configured stream/provider identities retained.
No transcript injection or synthetic audio was used.

| Local time / stream | Recognized provider output |
| --- | --- |
| **23:50:34.896467**, primary/en/Deepgram | “Hello, everyone. This is an English microphone test.” |
| **23:50:45.037703**, secondary/ml/Sarvam | “എല്ലാവർക്കും സ്വാഗതം ചെയ്യുന്നു.” |
| **23:51:24.544042**, secondary/ml/Sarvam | “ഇത് മലയാളം ശബ്ദ പരിശോധനയാണ്.” |

Other Malayalam fragments were imperfect, and Sarvam also transcribed the English
phrase using Malayalam script. Deepgram attempted English phonetics for Malayalam
speech. Both engines receive the same microphone audio; this is **provider/stream
separation**, not automatic routing that guarantees only one language appears in
each pane. Translation accuracy is **UNVERIFIED**: secondary `translation` fields
repeat the source Malayalam. Do not claim a correct English translation from them.
Zero candidate/delivery events occurred, as intended for the non-reference test;
shared bilingual verse delivery/dedup and semantic release were not exercised.

### Preserved provider failure and automatic fallback

The logs show three Start/Stop sequences in this interval. In each, the Sarvam
primary key connected, then the provider handler reported a **quota error** and
existing application code automatically selected the previously saved backup key.
For the latest session: primary connected **23:50:27.474**, quota/fallback logged
**23:50:27.737**, backup connected **23:50:28.605**. Deepgram connected
**23:50:26.787**. The successful Malayalam text therefore establishes operation
with the **backup**, not a healthy primary-key quota. Earlier sequences show the
same fallback at23:48:05 and23:49:16. No further provider run, account/provider
substitution or retry was initiated by this inspection. Do not conceal this as an
unqualified primary-provider pass. Review the primary quota before another run;
no billing, credentials or retry policy was changed. Cerebras startup still reports
HTTP402/payment_required separately; semantic-model prerequisites remain unresolved.

### Stop and complete temporary-settings restoration

The last Stop request `d7ab61717f48493a9b90e7a92a27d41e` is acknowledged.
Inspection confirmed recognition and both streams stopped, no pending candidate.
All **eight** changed keys were restored to their prior value **and presence**:
three intentional dual-STT/language/provider changes plus the five default keys
materialized by the existing settings-save path. All saved values now equal the
private pre-test baseline; byte-for-byte equality is not claimed because JSON
serialization differs. Unrelated edits were preserved; confidence0.75 and existing
manual/verification guards remain unchanged. Primary English/Deepgram, secondary
disabled, and previous secondary settings are restored for the next explicit Start.
The stopped UI retains the last bilingual session's text; that is historical output,
not evidence that recording continues or that temporary settings remain enabled.

Both local/private preparation records are now
`TEST_INSPECTED_ALL_TEMPORARY_SETTINGS_RESTORED`. Production settings hash remains
`e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`;
installed app intact. Baseline/full raw log remain private under
`/tmp/verseview-bilingual-20261019/` (700 folder,600 files). Local snapshots,
results, filtered provider timeline and CUA captures are under
`desktop-preview/test-results/bilingual-20261019/`.
[Actual separated panels](evidence/2026-10-19-bilingual/result-panels.jpg).

No runtime code change, rebuild or full suite was needed. Current bilingual
transport/UI check is complete within this scope. Windows physical acceptance,
semantic prerequisites/release, shared bilingual reference behavior and other
remaining physical/distribution gates retain **6/8,75%** progress. Original
intermittent incident unresolved. The previous pending restoration entry is resolved.


## Bilingual physical check prepared — restoration pending

The user explicitly approved preparation of a bounded English/Deepgram plus
Malayalam/Sarvam test. Recognition was stopped in the same normal packaged0.11.2
backend PID72557, with no pending candidate. A private baseline was recorded at
`/tmp/verseview-bilingual-20261019/settings.before.json` (700 folder,600 file).
Computer Use changed the existing Settings form and received saved acknowledgement
`ebbc37e1f2f047a7be348d5b6ececcc9`: `dual_stt_enabled=true`,
`secondary_language=ml`, `secondary_stt_engine=sarvam`. Primary English/Deepgram,
confidence0.75, manual confirmation and verification remain as saved.

The existing ProfileStore save merges defaults, so it also materialized five
previously absent local-model default keys: `local_llm_host`, `local_llm_port`,
and the verse/outline/summary `local_llm_keep_alive_*` keys. Their saved values
match the defaults in settings.py. No model service was started. These incidental
keys and their prior absence are recorded for restoration too; do not leave them
behind or overwrite unrelated later edits. All eight changed keys must be restored
to their baseline presence/value after recognition is stopped. Credential values
were not exposed. Production profile and installed app unchanged.

The app is left on Live session with Start enabled, recognition stopped. Provider
connections and bilingual recognition remain UNVERIFIED until explicit user Start
and actual spoken input. First test uses ordinary non-reference English/Malayalam
phrases, so no presentation is requested by the plan. If Sarvam fails, stop and
preserve evidence without provider/account substitution or blind retry.
Local preparation/evidence: `desktop-preview/test-results/bilingual-20261019/`.
No runtime changes, build or full test suites. **TEMPORARY SETTINGS RESTORATION
PENDING.** Overall remains75%6/8; Windows/semantic/other physical gates remain open.


## 2026-10-19 23:36 CDT: real speech manual hold and approval command pass

The user completed the prepared test in normal packaged **0.11.2**, source
`e54b905fabe60ebfcf60f61916a15ab67079bb11`, build
`2026-10-18T17-04-40-349Z-e54b905f-darwin-arm64`, frozen backend PID **72557**,
recognition session `bd586e48aaf54e32a3d9533e2149e58d`. UTC events are October 20;
local America/Chicago dates/times below are **October 19 CDT**.

| Real Deepgram final input | Candidate | Result / local time |
| --- | --- | --- |
| “John chapter three verse seventeen.” 23:36:12.125397 | `bcc879eeaf50` | DETECTED .127668 → DELIVERY_REQUESTED .138130 → COMMAND_ACCEPTED **23:36:12.153834**. |
| “Verse eighteen.” 23:36:18.524402 | `9e94a92b2567` | CONTEXTUAL DETECTED .529910 → MANUAL_CONFIRM_REQUIRED **23:36:18.530202**. No presentation request while held. |
| Dashboard approval, request `01632a1e04fe4d46b7a888f5433d313d` | same `9e94a92b2567` | Decision acknowledged `answered`; DELIVERY_REQUESTED **23:36:48.727370** → COMMAND_ACCEPTED **23:36:48.745815**. |

**PASS for the real microphone/STT → contextual candidate → manual hold → user
approval → browser command path.** The same reference/candidate identity is retained
throughout. The hold lasted **30.197168 seconds** before a presentation request.
The user explicitly confirmed that the actual presentation stayed on **John 3:17**
while held, then changed to **John 3:18 only after Approve**. **PASS for visible
reference behavior by user observation**, combined with the same-ID event trace.
No contemporaneous automated output screenshot or exact verse-text capture was
obtained. Manual rejection remains a separate untested case.

The user stopped recognition; Stop request
`e09d297d6c8e4acb9d2c5dee00f53582` is acknowledged. Inspection confirmed state
`stopped` with no pending candidate. The temporary preview **confidence threshold
is restored 0.90 → 0.75**, with `manual_confirm=true` and `verify=true` retained.
Only the recorded field was changed back, preserving all other current fields;
all resulting settings values equal the pre-test baseline. The JSON serialization
is not byte-identical, so byte-for-byte restoration is not claimed. The next
explicit Start rereads these persisted values through `ProfileStore.load`; no
microphone restart was needed to verify restoration. Both local/private preparation
records now say `TEST_INSPECTED_CONFIDENCE_RESTORED`.

Production settings hash remains unchanged:
`e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`.
Original installed application intact. Local snapshots/results:
`desktop-preview/test-results/manual-approval-20261018/`; full raw log and settings
backup remain private under `/tmp/verseview-manual-approval-20261018/` (700 folder,
600 files). No runtime source changes, rebuild, blind retries or guard disabling.
The prior “temporary setting pending restoration” entry below is resolved by this
checkpoint. Remaining dual-STT/semantic/active-layout/Windows physical checks keep
milestone progress **6/8, 75%**. The original intermittent incident is unresolved.


## 2026-10-18: manual approval test prepared — temporary setting pending restoration

After the user confirmed closing the backend, its PID68579 had exited. The private
preview profile confidence threshold was recorded and raised **0.75 → 0.90** to
reproduce a held short contextual phrase. `manual_confirm=true` and `verify=true`
remain enabled. The production profile was not changed. Full private settings
backup: `/tmp/verseview-manual-approval-20261018/settings.before.json` (600 file,
700 folder). Preparation record: local
`desktop-preview/test-results/manual-approval-20261018/preparation.json`.

An isolated existing-engine/fake-browser check established that John3:17 context
plus “Verse eighteen.” produces `MANUAL_CONFIRM_REQUIRED` for John3:18 at0.75
confidence below0.90, without a browser command. This is preparation only, not a
real microphone/manual-approval pass. Computer Use relaunched the same packaged
0.11.2 host PID **72557**, recognition **stopped**. Saved context is staged for
Start after acknowledged restore request `0bb72037106c474eaace8d83de7ece7e`;
nothing was presented and no microphone was opened by this preparation.

The user will Start, say the full John3:17 phrase to establish context, then
“Verse eighteen.” and approve the held reference. **RESTORATION PENDING:** after
the user stops this test, restore only `confidence`0.90→0.75 in the preview
profile, preserving other edits; confirm actual current values before restoring.
Do not report temporary settings restored until that is verified. No runtime
code/build changed. Manual physical result is still unverified; progress75%6/8.


## 2026-10-18 15:12 CDT: rapid spoken transition and duplicate repeat pass

The user repeated the planned English test in the same normal packaged **0.11.2**
application (source `e54b905fabe60ebfcf60f61916a15ab67079bb11`, build
`2026-10-18T17-04-40-349Z-e54b905f-darwin-arm64`, dashboard PID **62977**,
owned frozen backend PID **68579**, fresh recognition session
`5491c40b74384ba68a67f44d55b56954`). Actual Deepgram final transcripts preserve
the three full spoken references; this was not callback replay.

| Recognized phrase / CDT time | Candidate | Stage timestamps and outcome |
| --- | --- | --- |
| “John chapter three verse sixteen.” **15:12:04.105655** | `56f3d2d957af` | DETECTED .107107 → DELIVERY_REQUESTED .116335 → COMMAND_ACCEPTED **15:12:04.132218**. |
| “John chapter three verse seventeen.” **15:12:13.590509** | `491f7290f08b` | DETECTED .591819 → DELIVERY_REQUESTED .597708 → COMMAND_ACCEPTED **15:12:13.608192**. |
| “John chapter three verse seventeen.” **15:12:24.073479** | `a14c0f5c96ed` | DETECTED .074330 → SUPPRESSED **15:12:24.075213**, dedup: “Previously accepted reference is within exact-reference cooldown.” No DELIVERY_REQUESTED or COMMAND_ACCEPTED for this candidate. |

**PASS:** real English microphone/STT, explicit-reference detection and browser
command execution for 3:16 then 3:17, accepted **9.475974 seconds apart**, within
the requested ten seconds. **PASS:** the repeated reference was recognized and
intentionally suppressed before sending, not missed by STT. This repeat occurred
outside the short chapter cooldown but inside the exact-reference cooldown.

**Visible reference behavior: PASS by explicit user observation.** The user
reported that John 3:16 worked, John 3:17 worked, and the third repetition did not
trigger output again. This supports the intended visible transition/duplicate
behavior for this run. There was no contemporaneous automated capture of either
presentation, and exact visible verse text was not quoted or independently
verified; those evidence limits remain explicit. Do not describe log acceptance
alone as a captured-screen pass or frame-accurate display latency measurement.

The backend is now recognition **stopped**, after acknowledged Stop request
`445858e50d0843c4b26be6f760a77d34`; the host remains available. This inspection
sent no commands and changed no settings. Local evidence:
`desktop-preview/test-results/spoken-repeat-20261018/{observer.json,results.json}`;
full raw log is retained privately at
`/tmp/verseview-spoken-repeat-20261018/verseview.log` (700 folder / 600 file).
No rebuild or repeated suite was needed for this evidence-only update.

Manual approval on real speech, dual English/Malayalam recognition, semantic queue
release, diagnostic scrolling during active transcription and Windows physical
acceptance remain open. Milestone progress stays **6/8, 75%**. This successful
repeat does not establish the cause of the original intermittent incident, which
remains unresolved.


## 2026-10-18: spoken-number configuration clarification

A follow-up offline audit found that the first no-PRESENT case above follows an
existing explicit parser setting: saved **`spoken_numeral_mode=false`**, also the
default in `settings.py` and `configure()`. `parse_reference_eng.py` deliberately
expects “John three sixteen” to be chapter-only when this mode is off; its existing
self-test documents that expectation. The frozen backend maps persisted configure
parameters without replacing this value. Earlier wording calling this a “parsing
gap” describes the observed mismatch with the user's intent, not an established
regression in this code path.

The pure parser, without loading the engine or launching services, reproduced the
exact recognized phrase as **John 3 with the mode off**, **John 3:16 with it on**.
Twelve expected comparison results matched across both modes, also covering explicit
chapter/verse speech, colon syntax, a chapter-only phrase and a chapter range.
This bounded comparison does not establish broad false-positive safety or a real
speech/presentation pass. Evidence: local
`desktop-preview/test-results/spoken-20261018-1937/parser-mode-audit.json`.

No runtime change, build, settings toggle or live test was made. Verification
remains enabled, and the separate split-transcript 3:17 hold is unchanged. Keep
“chapter three, verse sixteen” as the explicit test phrasing under the current
configuration. A deliberate choice to support shorthand can use the existing mode;
that choice has not been applied automatically. The remaining presentation question
still needs the user's observation or contemporaneous capture of the output screen.
Original incident unresolved; progress remains **6/8, 75%**.


## 2026-10-18 14:36–14:38 CDT: actual user-spoken preview checkpoint

The user launched the normal packaged 0.11.2 backend (PID **68579**, dashboard
**62977**, exact source/build `e54b905fabe60ebfcf60f61916a15ab67079bb11` /
`2026-10-18T17-04-40-349Z-e54b905f-darwin-arm64`) and supplied actual speech.
MacBook Air Microphone opened **14:36:42.363**, configured English Deepgram Nova-3
connected **14:36:42.645**. This now establishes **PASS for real microphone/STT
recognition in this packaged artifact**, without transcript injection. It does
not establish visible output. Secondary STT is disabled in the current settings.

| Recognized input / CDT time | Candidate | Last confirmed result |
| --- | --- | --- |
| “Let us turn our attention to John three sixteen.” **14:37:03.237764** | `8bbcaac7b99a` | Parsed **John 3**, DETECTED .244329; SUPPRESSED .253875 at chapter_context, “Chapter-only reference updates context without display.” No PRESENT request. This exposes a spoken-number parsing gap for this phrase; the actual STT text includes “sixteen.” |
| “John chapter three verse sixteen.” **14:37:15.498749** | `b37187defb15` | FAST-PATH DETECTED .499801, DELIVERY_REQUESTED .509284, COMMAND_ACCEPTED **14:37:15.531784**. |
| “…John” **14:37:29.052247**, then separate final “chapter three verses seventeen.” **14:37:30.640065** | `c14a86963067` | PARSER DETECTED John 3:17 .640976; SUPPRESSED .642435, “Awaiting second detection.” Saved `verify=true` applies on this contextual parser path; no PRESENT request. The book and chapter/verse arrived in separate STT segments. |
| “John chapter three verses seventeen.” **14:37:39.079409** | `bd9a05d83316` | FAST-PATH DETECTED .080526, DELIVERY_REQUESTED .086288, COMMAND_ACCEPTED **14:37:39.096536**. |

The two accepted commands are **23.564752 seconds apart**. The requested
within-ten-seconds transition remains **UNVERIFIED**. The final 3:17 is the first
accepted 3:17 in this session; the earlier held detection does not make this a
passing duplicate-suppression case. Manual approval and semantic release remain
unverified. The verification guard is deliberately retained, not disabled to
make the test pass. No runtime code or settings changed during this inspection.

The user reported something did not go right. Logs explain the two no-command
cases above, but **COMMAND_ACCEPTED means the browser executed a PRESENT click**,
not that VerseVIEW rendered it. Current control-window recent references list
John 3:17/3:16; the browse pane is Genesis 1. That browse pane is not the actual
presentation output, and cannot establish what was displayed at the earlier
acceptance times. Computer Use confirmed Main enabled on Screen 1 1920×1080,
Stage/AUX disabled; routing was not changed. No new presentation command was sent.
The user has been asked what the actual screen showed at those two times.

The normal dashboard is connected with recognition **stopped** after an acknowledged
Stop request `44e3ed9474b34779acd1d40eca4b09b9`. WebSocket warnings start at
**14:37:52.714** during the stopped session; preserve them separately from the
accepted references. Computer Use inspected and scrolled the populated native
Activity view to the held chapter/verification outcomes: **PASS for access and
scrolling while stopped**, not yet a simultaneous-transcription layout pass.
The page is left on Activity for the user to inspect. VerseVIEW's original VERSES
tab is restored. No engine start/stop was issued by this read-only inspection.

Local snapshots, filtered timeline and screenshots are preserved at
`desktop-preview/test-results/spoken-20261018-1937/`. Full raw logs are private
at `/tmp/verseview-spoken-20261018-1937/verseview.log` (folder 700, file 600),
not committed. Production settings remain at the earlier recorded hash. The
installed app remains intact. Progress remains **6/8, 75%**. This explains two
misses in the current run; the original intermittent incident is still unresolved.


## 2026-10-18: partial native microphone/UI checkpoint and status correction

The user lifted the Mac physical deferral, confirmed VerseVIEW 11 #2 at localhost
50010 / Main Screen 1 1920×1080 isolated, and accepted microphone permission.
Actual packaged 0.11.1 opened the physical MacBook microphone and connected its
configured Deepgram Nova-3 provider on a fresh process. An earlier permission-time
PortAudio open failed; both outcomes are retained. With the user away, a single
OS-generated speaker playback attempt produced zero recognized text/candidates.
Speech, within-ten-second delivery, duplicates, manual approval, bilingual STT,
semantic release and actual VerseVIEW verse output therefore remain unverified.
This is not evidence of a downstream delivery failure or an explanation of the
original intermittent incident.

Computer Use verified settings scrolling, native window zoom/restore and a real
windowed outline child showing English/Malayalam operator-entered notes. Glass
selected native mode, but see-through comparison is unverified. It reproduced a
closed/stale backend announcement that incorrectly claimed connection. The minimal
0.11.2 frontend correction passes 149 Python / 50 Node checks, packaged crash/close/
relaunch tests, package/archive verification and a normal packaged Computer Use
close check. Native CI 39147884519 passes Windows x64, Mac ARM64 and Intel Mac,
including extracted archives; Windows graphical acceptance stays open. No
recognition was started in that final check. Production settings
are unchanged, temporary preview settings restored byte-for-byte, all owned hosts
closed, installed detector intact. The earlier Oct 4 cleanup question is separate.
Progress remains **6/8, 75%**. See the [physical checkpoint report](../desktop-preview/PHYSICAL_VERIFICATION.md)
for exact artifacts, times, failures, screenshots, cleanup and remaining gates.


## 2026-10-18: final read-only incident and acceptance gap audit

The [consolidated gap audit](DELIVERY_GAP_AUDIT.md) rechecked historical/current
delivery guards, existing regression assertions and preserved source/microphone
events without launching services or repeating completed suites. The old source
replay's accepted transition was 8.086609 seconds with reported visible output;
the later packaged real-speech transition was 22.578544 seconds without captured
visible output. These cannot be combined into a current-preview physical pass.
The original incident still lacks a matched failure trace establishing cause.

The audit also identifies an earlier cleanup gap: the Oct 4 packaged report left
temporary detector settings pending. Today's read-only settings hash differs
from the recorded baseline, but values were not inspected and this cannot
distinguish test changes from later user choices. No settings were restored or
changed. Review the private backup and intended settings with the user before
any restoration. Current preview QA cleanup does not establish historical
production-profile restoration. The permanent display timeouts remain untouched.

Milestones 1–6 are complete within documented scope; 7 is physically deferred
and 8 retains distribution/acceptance/replacement gates. Progress remains 75%.
The audit gives the smallest coordinated manual sessions and final approval
steps; no installed-app change, signing change or release occurred.

## 2026-10-18: isolated preview install, update and rollback

Preview 0.11.1 source `af3334529cdfbb543b0083ab7949cbfa26bd204b`, Mac build
`2026-10-18T15-13-24-202Z-af333452-darwin-arm64`, passes an actual packaged
0.10.0-to-0.11.1 lifecycle check: copy-once private migration, relocation into
a path with spaces, preservation through update/app-only uninstall/reinstall,
previous-version reading and complete Backend-backup rollback. The copied app
and QA profile were disposable. Both original test artifacts retain their
file/link inventories and all owned children exited.

The check exposed obsolete external-detector setup guidance and a footer that
did not refresh when bundled ownership arrived. A focused view test, explicit
packaged message assertions and the corrected run pass. Core backend and sync
regressions pass on the same artifact, as do extracted inventory/signature and
frozen no-input startup. Python runtime hashes match verified 0.11.0. Final
native CI 39139494109 passed Windows x64, Mac ARM64 and Intel Mac, including
149 Python and 49 Node tests, frozen feature checks and extracted archives.

The new guide covers equivalent Mac/Windows installation and rollback; Windows
graphical execution and OS trust prompts are unverified. Real microphone/STT,
visible output and semantic queue acceptance remain deferred. Production
identity/signing/distribution and explicit replacement approval remain open;
the installed detector and production profile were not modified. Progress stays
**6 of 8, 75%**. The original intermittent incident remains unresolved.
Final native CI, exact artifacts, preserved failure evidence and limits:
[installation report](../desktop-preview/INSTALLATION_VERIFICATION.md).

## 2026-10-18: standalone credential sync and integration milestone complete

Preview 0.11.0 performs opt-in saved-URL credential sync through a bounded
worker, with a stopped-state commit, storage-conflict checks, atomic settings
save and private content-addressed Google credential files. Only the shared
legacy credential whitelist is accepted. The renderer receives fixed status,
count/time and an explicit Pull action; credentials/URLs remain private.

Final runtime source `b2555dd5228d08930e5f5448aa922c9429eb7699`, Mac build
`2026-10-18T15-00-34-620Z-b2555dd5-darwin-arm64`, passes 149 Python and
48 Node tests, eight packaged suites/252 layout cases and extracted archive
inventory/signature/frozen startup checks. Native CI 39124243081 passes Windows
x64 and both Mac architectures. Initial CI 39123891275 failed an uncanonicalized
credential-path assertion in the test harness; the corrected path comparison
passes and original evidence is retained.

The standalone integration milestone is complete within this isolated scope:
**6 of 8 milestones, 75%**. Sync downloads were fake; recognition, provider,
Discord and presentation services were not contacted. Physical microphone/STT,
visible output, semantic queue and graphical Windows acceptance stay deferred.
Installation/update/rollback readiness is next, using a separate target/profile.
The original intermittent incident remains unresolved. Exact artifacts, secret
handling, cleanup and limits: [sync verification](../desktop-preview/SYNC_VERIFICATION.md).

## 2026-10-18: standalone Discord bot controls

Preview 0.10.0 runs the existing Discord bot through the owned frozen backend,
with explicit connection, a private ephemeral bridge and guarded manual verse
delivery. Local regressions pass: 137 Python tests, 46 Node tests, seven packaged
suites and 216 layout cases on source `a6c6146a6cb67635bd2d4dbf78d96614a95fff39`,
build `2026-10-18T11-14-23-016Z-a6c6146a-darwin-arm64`. Final native CI
39122401057 passed on Windows x64 and both Mac architectures. All presentation, Discord and speech inputs were mocked;
real Discord login and physical microphone/STT/visible output remain unverified.

Packaged checks found and repaired remote-Start session selection and Settings
acknowledgement defects. Focused checks also cover private session file saving,
incomplete settings JSON, shutdown draining and unknown late acknowledgements.
Those findings do not explain the original intermittent delivery incident,
which remains unresolved. Exact artifacts, evidence and limits:
[bot verification](../desktop-preview/BOT_VERIFICATION.md).

## 2026-10-18: standalone outline notes and explicit display implementation

Preview 0.9.0 connects the existing outline loop to revision-bound editable
notes. Captured dispatch routing and callbacks, stale-reply checks, typed text
limits and executor draining on Stop prevent an old generation from overwriting
new operator notes or starting a later fallback after Stop. A separate plain-text
outline window requires explicit selection/opening and closes on lost session,
feed or monitor; its real window/fullscreen output has not been exercised.

Source `b62103e4fba8868b9d677ad304154582392641a0`, local build
`2026-10-18T10-22-51-380Z-b62103e4-darwin-arm64`: 122 Python tests, 42 Node
tests, six packaged Mac suites and 180 layout cases passed. Actual frozen
outline processing used mocked models/STT/browser services. Native CI
39118943718 passed Windows x64 and both Mac architectures. Physical speech,
model quality, audience/VerseVIEW output and live queue release remain deferred.
The original intermittent delivery incident remains unresolved. Details:
[outline verification](../desktop-preview/OUTLINE_VERIFICATION.md).

## 2026-10-18: standalone watcher suggestions

Preview 0.8.0 adds six expiring, stream-attributed watcher suggestions and
session-bound operator sends through the existing guarded manual-delivery
path. Passive advice is separate from actual command acceptance. An automatic
watcher candidate is never labeled accepted solely because it appears.

Source `cb5b9c31c43ff25fa53aaf1ddfd392d70f1e7e78`, packaged build
`2026-10-18T10-00-16-633Z-cb5b9c31-darwin-arm64`: 117 Python tests, 36 Node
tests, four packaged Mac suites and 108 layout cases passed. With mocked speech,
models and controller, actual frozen bilingual watcher processing produced
passive advice; explicit John 3:19/20 sends reached COMMAND_ACCEPTED with exact
candidate IDs and primary/secondary attribution. Physical output is unverified.

The first packaged test found stale DETAILS expansion across a session change.
Evidence was preserved; the focused identity fix and same-artifact regressions
passed. This UI defect does not explain the original intermittent incident,
which remains unresolved. Native CI run 39117499861 passed Windows x64 and both
Mac architectures. Precise artifacts are recorded in
[suggestions verification](../desktop-preview/SUGGESTIONS_VERIFICATION.md).

## 2026-10-18: opt-in standalone local-model warmup

Preview 0.7.0 reuses configured per-role local-model clients on a background
worker, with typed progress/outcome status and private error details. It never
warms on idle launch, blocks recognition on warmup, or changes delivery guards.
Stop cancels later roles/results; an in-flight synchronous call can still
finish under its existing transport timeout. Quick Start skips overlapping
warmup and rejects stale results.

Source `6242886cd2033ea074e1fdf5dc2c900019cf0fee`, local packaged build
`2026-10-18T03-45-45-542Z-6242886c-darwin-arm64`: 109 Python tests, 34 Node
tests, three packaged Mac suites and 72 layout cases passed. Actual frozen
engine callback replay accepted John 3:16/17 while slow mocked local-model
completions ran; a deliberate warmup failure left recognition running. Native
CI `39094733176` passed Windows x64 and both Mac architectures, including frozen
warmup/recovery and extracted-archive checks. No real model/STT/VerseVIEW
request or physical output was exercised. The original delivery incident
remains unresolved. Details: [warmup verification](../desktop-preview/WARMUP_VERIFICATION.md).

## 2026-10-17: explicit standalone session recovery

Preview 0.6.0 adds private 15-second checkpoints and an explicit Restore/Discard
decision on companion relaunch. Both engine buffers, recent raw-speech previews
and verse context survive a killed verification child. Restore prepares context
while stopped; the next explicit Start configures then restores with the engine's
existing quarantine. Pending approvals, queues, commands, settings/credentials,
provider logs and Discord message IDs are excluded. Historical text stays separate
from live STT and accepted commands. Legacy GUI checkpoint files are untouched.

An initial packaged autosave failed because validation expected integer context,
while the real engine stores digit strings. The evidence was preserved, the
validator corrected, and focused unit/native frozen regressions added. The final
Mac artifact is `2026-10-18T03-22-21-039Z-6dc51858-darwin-arm64`, source
`6dc51858eaf90f6d9d209224e22a371f0d64bc2d`. All 105 Python tests, 33 desktop tests,
six packaged suites and 156 layout cases passed. Native CI run `39093309837`
passed on Windows x64, Mac ARM64 and Intel Mac, including actual frozen-host
autosave, deliberate QA-child termination, explicit restore, and extracted
archive verification with mocked services.

This does not establish real microphone/STT, visible VerseVIEW output, live
semantic queue release, graphical Windows behavior, or the original incident's
cause. Those physical checks remain deferred. The installed app, production
settings and system preferences were not changed. Project progress remains
5/8 milestones because other backend features still need migration. See the
[recovery report](../desktop-preview/RECOVERY_VERIFICATION.md) for artifacts,
limits, failure evidence and cleanup.

## 2026-10-17: authorized preview branch and schedule migration

The migration was committed and pushed to `codex/desktop-backend` inside the
existing `KevinAwesomeCoding/VerseView-Detector` repository after explicit user
approval. `main`, production release publishing and the installed app remain
unchanged. The preview-only native build matrix is running on GitHub Actions.
Initial Windows tests exposed test-file CP1252 decoding and a test that cleared
Windows home variables; their tracebacks were preserved and the test harness
was corrected without changing delivery guards or provider logic.

Preview 0.5.1 migrates Smart Schedule through a shared service timetable. It
resolves at explicit Start, applies the legacy stream policy, retains saved
settings, and rejects incompatible providers. The affected packaged Mac suite
passed with a fixed isolated QA clock, fake services and a frozen companion;
92 Python and 31 Node tests passed. Exact artifacts, commits, CI run and limits
are in the [standalone report](../desktop-preview/STANDALONE_VERIFICATION.md).
Native Windows x64, ARM64 Mac and Intel Mac CI build, frozen smoke, archive integrity and
extracted-deliverable checks subsequently passed on run `39091168118` at
`f8fba2e`. The final Windows verifier issue was native path separation in its
ASAR lookup; required-file/license/hash checks remain in place. The complete
three-platform run finished successfully. Milestone 6 is in progress because feature
parity is incomplete; physical tests remain deferred and the original incident
is unresolved.

## 2026-10-17: standalone companion preview; physical checks still deferred

Preview 0.5.0 now packages a native frozen Python companion alongside the Mac
dashboard, using the existing PyInstaller spec with an optional headless entry.
The packaged dashboard launched its included companion with no legacy GUI or
external Python command. Its verification report identified `frozen: true`,
`guiImported: false`, and PID 23124; the native build input was temporarily
hidden to check independence from that source directory.

The final Mac artifact is build
`2026-10-18T02-17-35-299Z-3a4349be-darwin-arm64`, based on revision
`3a4349be57099c0c130800300b335d98f611d11a` plus the uncommitted migration work.
85 Python and 31 desktop unit tests passed, as did all five packaged suites,
120 layout cases, archive/runtime inventory and ad-hoc signature checks.
Mocked speech/controller interactions exercised real engine callbacks,
bilingual events, exact-candidate approval, clear-output requests, settings,
crash reporting, explicit relaunch and owned-child shutdown. These checks did
not use actual microphone/STT transport or visible VerseVIEW output.

The preview copies settings into its own private profile, never auto-starts
recognition, and preserves stored credentials/unknown values. Advanced feature
migration and native Windows packaging remain incomplete; named compatibility
gates block Start when unsupported saved features are enabled. Milestone 6
remains in progress, with 5 of 8 milestones complete. Physical tests and live
semantic queue release remain deferred; the original incident is unresolved.
The installed app and production settings were left intact.

See the [standalone verification report](../desktop-preview/STANDALONE_VERIFICATION.md)
for exact commands, artifacts, evidence, fixes, cleanup and remaining limits.

## 2026-10-17: non-secret dashboard settings; physical checks deferred

Preview 0.4.0 adds microphone selection, primary/secondary language and provider,
dual STT, detector Bible translation and VerseVIEW URL settings. Saves require
a stopped, fresh backend and a current revision; external edits cause a
conflict. The settings writer now replaces files atomically. Stored credentials,
unknown fields and unrelated GUI drafts are preserved; credentials are not
exported to the renderer.

The actual packaged Mac preview passed the settings workflow against production
binding/store code with fake widgets, synthetic devices and temporary files.
75 Python tests and 25 desktop unit tests passed, plus 120 packaged layout cases
across settings, controls, observer and samples. Both package archives were
verified. Windows execution, microphone/STT, visible VerseVIEW output and live
semantic queue release remain deferred/unverified. The installed detector and
production settings remain unchanged; the original incident is unresolved.

See the [settings verification report](../desktop-preview/SETTINGS_VERIFICATION.md)
for exact artifacts and limits, and the
[migration progress plan](DESKTOP_MIGRATION_PLAN.md) for overall milestones.

## 2026-10-17: opt-in desktop controls; physical tests deferred

Desktop preview 0.3.0 now has a local command adapter for start/stop and exact
manual-candidate decisions. It delegates to the existing Python GUI/engine;
credentials, provider configuration and delivery guards remain there. Control
requires both observer export and an explicit desktop-control opt-in. The
installed detector remains unchanged.

The actual packaged Mac preview passed command round trips against mocked
lifecycle callbacks and real confirmation/delivery code with a fake browser.
Candidate IDs survived approval; rejection, stale/session/replay checks,
sample separation, and command availability while copying transcripts passed.
62 Python tests and 19 desktop unit tests passed, plus 36 packaged control,
24 observer, and 24 sample layout cases. Both Mac and Windows archives were
verified; Windows was not executed.

At the user's request, real GUI/device lifecycle, microphone/STT, physical
VerseVIEW output, and live semantic queue checks are deferred. These results
do not explain the original intermittent incident. See the
[control verification report](../desktop-preview/CONTROL_VERIFICATION.md) for
exact artifacts, provenance, evidence, setup and limits.

## 2026-10-17: read-only dashboard observer

The separate desktop preview now reads an opt-in, local snapshot feed from the
updated Python source. The actual engine transcript/parser/delivery callbacks
were exercised with isolated replay and mocked services through the packaged
Mac preview. Candidate IDs, stream/language, timestamps and outcomes survive the
boundary. Raw Sarvam text is exported before translation, and a focused test
confirms a translation exception does not hide that received text. Delivery and
exception behavior remain unchanged.

All 50 Python tests and 13 desktop unit tests passed, plus 24 packaged observer
layout cases and 24 packaged sample cases. The Windows package built and its
archive was verified, but it was not executed on Windows. This stage did not
start microphone/STT transport, verify a visible VerseVIEW screen, replace the
installed detector, or explain the original intermittent incident. The installed
detector does not publish the new feed until an observer-enabled build/source
is run. See [the observer report](../desktop-preview/OBSERVER_VERIFICATION.md)
for artifact provenance, replay evidence, setup, and remaining checks.

Investigated the working tree at `/Users/kevinanil/VerseView-Detector`, branch
`main`, starting commit `0d3bd38`. The only pre-existing change was untracked
`.DS_Store`; it was preserved. The initial code investigation sent no live
commands. The separately approved live verification below used the installed
VerseVIEW instance and its isolated output.

## Confirmed findings

The strongest demonstrated cause is in `vv_streaming_master.py`,
`VerseController.send_verse`:

- The previous chapter guard compared only book/chapter. It blocked **changed
  verse numbers** within ten seconds, despite its comment saying “unless verse
  changed.”
- It wrote `_last_presented_book_chapter` and `_last_presented_time` before
  cooldown checks or the browser command. A failed connection therefore marked
  the chapter as presented.
- Blocked detections refreshed that timer, allowing frequent detections to keep
  extending suppression.

Before editing, an isolated replay against the actual engine produced:

| Sequence | Previous result |
| --- | --- |
| `John 3:16` at synthetic time 100, then `John 3:17` at 105; explicit bypass | First accepted; changed verse rejected |
| `Romans 8:1` at 200 with connection failure, then valid mock browser at 201 | Retry rejected; zero browser calls |

Both sequences now pass. The chapter guard checks the exact last reference,
blocked candidates do not refresh it, and accepted-command state is committed
immediately after the PRESENT click returns. Exact-reference deduplication,
configured deduplication, and the global cooldown remain active.

Additional findings supported by code and focused regression tests:

- `queue_verse_range` cleared the list without invalidating the previous fetch
  worker. A deliberately delayed old fetch could append into a replacement
  range. Generation checks now prevent this and record cancellation.
- `check_vtc` and `check_verse_queue` required cloud clients even though
  `_llm_semantic_match` supports local routing. They now use the existing
  `_role_has_llm` helper; local-only matching is tested.
- Scripture-reading and ONWARDS progression could advance before, or despite,
  failed delivery. They now advance after command acceptance.
- Chapter-only context updates returned success without a browser command, and
  the GUI suggestion action reported “sent” without checking the outcome.
  These now report context-only suppression or pending/blocked delivery.
- SDK callback threads could lose stream context. Transcript callbacks now bind
  their actual stream and restore prior context, including when they raise.

These are demonstrated defects, but there is **no matched production
undelivered-reference example proving which one caused the reported incident**.

## Existing runtime evidence

Read only selected delivery/connection lines from
`~/Library/Application Support/VerseView/verseview.log`:

- Line 549: `2026-08-21 01:08:24,997` — FAST-PATH explicit ref `John 3:16`.
- Line 550: `2026-08-21 01:08:25,018` — previous `PRESENTED` log for that ref.
- Lines 267–375: August 20 connection failures report ChromeDriver supporting
  Chrome version 152.
- Lines 675 and 707: `2026-09-20 18:07:30,626` and `18:07:36,193` —
  `net::ERR_CONNECTION_REFUSED` during connection.

The successful sequence's last confirmed stage is the browser-command path;
its old “PRESENTED” wording does not prove visible output. The other failures
stop at initialization and do not establish a detected-but-undelivered incident.
The old chapter suppression and ordinary cooldown messages were DEBUG-only, so
absence from the INFO log cannot establish that a function never ran.

## Actual trace and intentional stops

| Path / implementation | Relevant stops or intermediate states |
| --- | --- |
| STT provider callbacks → `create_transcript_handler` / `create_sarvam_transcript_handler` | Empty/partial/noise handling; Sarvam translation; callback errors |
| `_process_transcript_blob` → `_detect_explicit_reference`, `detect_verse_hybrid`, `_detect_from_translation` | Self-correction, scripture filters, book/person/narrative guards, structural/range validation, insufficient translated evidence |
| Hybrid contextual, sequential, range, read-intent, and threaded LLM paths | Anchor/progression rules, stale LLM results, LLM pacing and context deduplication |
| `deliver_verse` | Validation, scripture passage lock, system-action quarantine; explicit/LLM/watcher/queue exceptions retained |
| `_start_vtc` → `check_vtc` | Verse Interrupt waits for semantic match; same pending reference suppressed; replacement, 60-second expiry, fetch failure/fallback |
| `queue_verse_range` → `check_verse_queue` | Range text fetch; semantic-match release; replacement, three-minute expiry, book/verse/chapter abandonment, shutdown cancellation |
| `_check_onwards_advance` | Semantic or existing keyword match; mismatch limit; progression only after accepted send |
| `VerseController.send_verse` | Worship, chapter-only context, confidence/manual approval, hear-twice verification, exact/chapter/global cooldowns, controller/control availability |
| `VerseController.connect` and browser command | V10/V11 detection, primary/legacy selectors, reconnect after send failure; command exceptions |

`settings.py` retains its defaults: confidence 0.75, manual confirmation enabled,
hear-twice verification enabled, cooldown 3 seconds, dedup window 60 seconds,
Verse Interrupt disabled. Manual confirmation applies to below-threshold
candidates on paths that do not bypass that confidence check; it does not hold
all detected references. Watcher passive suggestions remain operator actions.
Watcher suggestion deduplication and LLM request deduplication describe emitted
suggestions/requests, not proof of delivery, and have not been removed.

`bible_fetcher.py` supplies verse text/translation fallbacks for deferred matching;
immediate browser reference delivery does not require that fetch.
`session_state.py` stores session metadata and has no presentation acknowledgement.
`vv_bot_bridge.py` routes direct operator actions separately from automatic
transcript delivery. `vv_remote_control.py` remains unchanged; the automatic
Bible path uses the controller's shared V10/V11 selectors rather than its
version-specific song/schedule adapters.

## Changes and diagnostics

- `vv_streaming_master.py`: focused delivery-state fixes, correlated metadata,
  deferred candidate identity, queue replacement safety, and safe thread errors.
- `vv_gui.py`: small read-only diagnostics panel and accurate suggestion outcome.
- `tests/test_delivery.py`: isolated engine/browser/routing/queue regression tests.
- `.gitignore`: retain this regression suite while leaving scratch test ignores.
- This report: evidence, trace, commands, and verification limits.

Events use `VERSE_DELIVERY` followed by JSON in the existing log. Fields include
candidate ID, normalized reference, source, stream, configured language, UTC
ISO timestamp, stage, outcome, reason, and applicable guard/countdown/adapter
context. IDs persist through range fetching, semantic workers, and manual
confirmation. SDK callbacks explicitly identify primary/secondary streams.
No new event includes transcript content, credentials, or exception messages;
errors include their type. These diagnostic records are excluded from the
normal transcript widgets and Discord live-log handler.

The engine retains 300 events. **Verse Delivery Diagnostics** shows the most
recent 80, refreshes through Tk `after(500, ...)`, and stays read-only. Find a
reference, then follow its ID in the panel or search the log for that ID. Follow
`QUEUED` and `MANUAL_CONFIRM_REQUIRED` to their later outcome; neither means
successful delivery. Guard names and cooldown remaining are in the JSON log.
Range expiry is checked on subsequent transcript callbacks; an idle pending
range stays in memory until another callback or engine shutdown records its
outcome. A semantic worker error keeps the candidate pending and records ERROR.

## Meaning of success and uncertain delivery

`COMMAND_ACCEPTED` means Selenium returned from setting the input and executing
the PRESENT button click. There is no server acknowledgement or output-screen
verification in this integration. **It does not confirm visible presentation.**
No `PRESENTATION_CONFIRMED` event is emitted.

A failure before clicking leaves delivered-reference history untouched. A
failure *during* the PRESENT click may have delivered despite the exception;
its event includes `delivery_uncertain=true`. Repeated automatic candidates are
held for `max(20, DEDUP_WINDOW)` seconds, independently of delivered history, to
limit duplicate presentation. There is no new automatic retry loop. Later
spoken detections may try again after that window; inspect the screen before
any operator resend when delivery is uncertain.

## Verification

Executed from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q vv_streaming_master.py vv_gui.py vv_remote_control.py vv_bot_bridge.py settings.py session_state.py bible_fetcher.py parse_reference_eng.py parse_reference_ml.py parse_reference_hindi.py contextual_watcher.py stt_providers tests
git diff --check
```

Results: **39 tests passed**; compilation passed; diff whitespace checks passed.
No pre-existing test suite was found. Tests use the actual engine functions,
fake Selenium modules/browser controls, mocked fetch/semantic results, and an
HTTP-request prohibition. V10, V11, and legacy selectors run through the actual
connect/version-detection code with a fake browser. English, Hindi, Malayalam,
stream attribution, callback failures, manual hold/rejection/cancellation,
concurrency, queue lifecycle, failed-send state, and GUI bounded-refresh behavior
are covered. GUI refresh tests execute the actual method with fake widgets.

At the initial investigation stage, no real browser/VerseVIEW end-to-end test,
cloud/local LLM response test, or visual GUI layout inspection had been performed.
The subsequent live verification below supersedes the browser/output and layout
limitations where explicitly stated. Direct remote/manual presentation controls retain
existing behavior and are outside the new automatic-delivery correlation path.

## Safe operator verification

Use a separate VerseVIEW test instance and non-live display, with outbound
webhooks and ATEM disabled. Point the detector at that test instance. Do not
use a service presentation screen for this check.

1. Announce `John 3:16`, then `John 3:17` within ten seconds. Check the diagnostics
   and the isolated output separately; both commands should be accepted.
2. Repeat the second reference immediately; confirm suppression and its guard.
3. Exercise an inferred candidate with hear-twice/manual confirmation enabled;
   confirm that a pending outcome is distinguished from command acceptance.
4. Test a range with Verse Interrupt/semantic matching as appropriate. Confirm
   queue entry, release, replacement, or expiry is traceable by ID.
5. Interrupt the test connection before a command, restore it, and provide fresh
   spoken evidence. Check the failure and subsequent attempt. If the click
   itself is uncertain, inspect the isolated output and respect the cooldown.
6. Inspect the diagnostics panel at your usual window size and verify that the
   transcript, suggestions, and history controls remain usable.

## Approved live verification — 2026-10-03, America/Chicago

**John 3:16 → John 3:17 visibly worked on the actual presentation output.**
The browser commands were accepted **8.086609 seconds apart**. Computer Use
captured both references and the correct English verse text in the native
`THEME 1` window, whose document was
`app.asar/presentation/presentation1.html`. This was the audience presentation
window, distinct from the control application's Genesis preview. Malayalam
text also appeared under the existing bilingual theme; its translation was
not independently audited.

### Environment and isolation

- Repository: same working tree, `main`, HEAD `0d3bd38`; existing delivery fixes
  and unrelated `.DS_Store` preserved. No commit, push, or deployment.
- Installed VerseVIEW: `/Applications/VerseVIEW11.app`, version **11.0.0**.
  Target: `http://127.0.0.1:50010/control.html`; Main enabled on
  **Screen 1 → 1470×956**, Stage and AUX disabled. Existing theme:
  **Blue stars motion background**. Routing/theme were not changed.
- Before sending, the user answered the explicit isolation/approval request
  with “it isnt do not worry,” confirming no audience connection in context.
  The user separately approved a temporary dependency environment.
- The installed detector reports `build-0d3bd38-230`; that bundle does not
  contain the uncommitted fixes. It was not used as evidence for the fixes.
- Ran Python **3.13** from a disposable venv with customtkinter **6.0.0**,
  Selenium **4.50.0**, webdriver-manager **4.1.2**, requests **2.34.2**, and
  certifi **2026.7.22**. Chrome **154.0.8037.93** worked with the already cached
  ChromeDriver **153.0.8010.52** in this session. No driver was downloaded and
  no existing cache was reconciled or deleted. This does not establish general
  compatibility of those different major versions.
- Live `VerseController.connect` detected `verseview11` and selected fallback
  IDs `remote_bibleRefID` / `remote_bible_present`. The missing first-choice
  input selector incurred about 15 seconds of wait during connection.
- The real source GUI was titled `VerseView Detector — SOURCE DELIVERY
  VERIFICATION`. Import paths and SHA-256 fingerprints were recorded in
  [actions.jsonl](evidence/2026-10-03-delivery/actions.jsonl). Engine hash:
  `3ed212223c53c0fb9e2a7525678c28033e44385107b4f32c205d24e7248bf95e`;
  GUI hash: `4208cbb0747beac61a1fe6c90698bdc2f5db953f4e14d837a55874319bfcf87b`.

### Entry point and settings

A disposable runner invoked the existing
`create_transcript_handler(controller, False, '[TEST-REPLAY]', parse_eng)`
callback with final transcripts. That callback ran queue checks, transcript
logging, `_process_transcript_blob`, parsing/contextual detection,
`deliver_verse`, and the actual Selenium controller. No mock browser or final
send shortcut was used for the live scenarios.

Microphone capture, audio transport, STT recognition/provider SDKs, and normal
GUI Start/engine-thread orchestration were bypassed. The GUI's streaming status
therefore remained **Stopped**, despite its attached live controller. The
history polling logic that requires an active streaming session, the chapter
browser fetch loop, and full Start/Stop behavior were not verified.

Test-process settings: English, KJV, primary stream only; cooldown **3 s**,
dedup window **60 s**, manual confirmation **true**, hear-twice verification
**true**, confidence threshold **0.75**, Verse Interrupt **false**. Explicit
FAST-PATH references retain their existing confidence/verification bypass;
manual confirmation does not hold every explicit reference. For the manual
test only, the threshold became **0.90**, then returned to **0.75**.

Settings/session writes and substantive test logs were redirected to the
temporary directory. Credentials, sync, bot, ATEM, watcher, cloud/local LLMs,
and notes saving were disabled through sanitized test-process settings; saved
credentials were not loaded. Microphone enumeration and update checks were
disabled in the runner. Queue verse text used the existing real fetch path.

### Test evidence

Times below are local CDT on October 3; JSON events contain UTC timestamps on
October 4. The [32-event snapshot](evidence/2026-10-03-delivery/events.json),
[source log](evidence/2026-10-03-delivery/source.log),
[input/action record](evidence/2026-10-03-delivery/actions.jsonl), and
[disposable source runner](evidence/2026-10-03-delivery/source-runner.py.txt)
preserve the test evidence. Native screenshots were returned inline in the
verification chat; no standalone screenshot files were exported.

| Input / time / candidate | Expected | Actual diagnostics | Direct output evidence / verdict |
| --- | --- | --- | --- |
| `John chapter three verse sixteen`, 23:46:27.508, `1e3e8d4883f7` | Normalize and present John 3:16 | DETECTED → DELIVERY_REQUESTED → COMMAND_ACCEPTED at .532 | Native THEME 1 screenshot and AX text showed John 3:16 and “For God so loved the world…”; **PASS, visible** |
| `John chapter three verse seventeen`, 23:46:35.601, `625d03a3fa99` | Changed verse accepted within 10 s | Same three stages; COMMAND_ACCEPTED at .618, 8.09 s after first | Native presentation screenshot and AX text changed to John 3:17, “For God sent not his Son…”; **PASS, visible** |
| Repeat John 3:17, 23:46:50.926, `a443c38b94e7` | Suppress exact duplicate | SUPPRESSED by `exact_reference_dedup`, 15.3 s after acceptance; no new browser command | **PASS, live suppression trace**; output pixels after the repeat were not separately recaptured |
| `verse eighteen`, threshold .90, 23:46:58.792, `ab28b741c172` | Hold contextual 75% candidate until approved | MANUAL_CONFIRM_REQUIRED; last accepted reference stayed John 3:17. CUA observed actual Low Confidence Verse dialog and clicked Yes. Same ID reached COMMAND_ACCEPTED at 23:47:25.716 | Settled native output showed John 3:18 with “He that believeth on him…”; **PASS, hold/approval trace and visible approved result**. Output pixels during the hold were not separately captured |
| `verses nineteen through twenty`, 23:47:43.654; first `9aa405b7bbc7`, queued `37b82ec608e7` | Hold first inferred verse under hear-twice verification; queue continuation | John 3:19 awaited second detection. John 3:20 fetched and QUEUED, semantic client unavailable | **PASS, real queue/verification trace**; no presentation command for either candidate |
| `verses twenty one through twenty two`, 23:47:51.318; first `1552f6d9dfcb`, queued `0e9ff666a541` | Replace old range with correlated cancellation | John 3:20 CANCELLED under original ID. John 3:21 awaited second detection; John 3:22 fetched/QUEUED | **PASS, live replacement trace**. John 3:22 later EXPIRED at 23:51:31.359; final queue length zero. Semantic release **UNVERIFIED live** |
| `Romans chapter eight verse one`, unavailable test-only URL, 23:49:02.283, `7a5cb712fa34` | Explain connection failure without poisoning delivered state | ERR_CONNECTION_REFUSED; DELIVERY_FAILED at 23:49:03.371; last accepted reference remained John 3:18 | **PASS, real connection failure trace**; failed-attempt output pixels not captured |
| Restore URL, fresh same transcript at 23:49:11.610, `a523faba058d` | Retry fresh evidence without false chapter suppression | Candidate arrived 8.24 s after failure event; real reconnect succeeded and COMMAND_ACCEPTED at 23:49:27.616 | **PASS, live recovery trace**. Initial recovery pixels were not captured before GUI inspection. A later replay at 23:51:31.360 (`ad939211c79b`) was accepted and native THEME 1 screenshot/AX text confirmed Romans 8:1, “There is therefore now no condemnation…” |

The input record contains only the deliberate synthetic test phrases. Each
accepted attempt had its own candidate identity; the manual approval retained
its original identity. The later Romans replay was deliberate, after more than
the configured dedup window, not an unexplained retry. No unrequested accepted
commands appeared in the captured event trace. Continuous screen recording
was not performed, so this is not a proof against every possible delayed
external presentation.

### Diagnostic UI observations

Computer Use directly inspected the real CTk GUI at its default **1060×700**
size and after native window zoom (screenshot **2940×1718** physical pixels).
The diagnostics title and populated event text were readable, with wrapped
long lines and a visible scrollbar. Normal transcript/status logging continued
above it, including the replay inputs, without diagnostics JSON flooding that
pane. Start/Stop and bottom action controls remained visible. Diagnostics state
was `disabled` in a live snapshot, consistent with read-only operation.

The default size is cramped: the transcript shows only a few lines and the
history/chapter sidebar headers are substantially clipped by the available
height. Zooming provides readable sidebar headers and more transcript area.
This is a **layout limitation**, not a clean pass for every supported window
size. The runner did not populate the sidebar because streaming remained
stopped. No speculative layout refactor was made.

Scrolling older diagnostics is **UNVERIFIED**: native scroll/drag attempts
either produced no demonstrated movement or Computer Use errors
(`noWindowsAvailable`, invalid ScreenCaptureKit parameter, and an off-screen
window-position error). A native menu also temporarily impeded input and was
explicitly dismissed. These results do not isolate a scrollbar code defect.
The remaining manual check is to open the source GUI, zoom it, scroll the
diagnostics thumb to the top and back, then test the normal small window and
divider with populated history while streaming.

The bounded history is established independently by code and tests:
`deque(maxlen=300)`, locked copied snapshots, last **80** GUI events, and
500 ms main-Tk polling. The unit tests cover truncation/copy behavior and the
actual refresh method with fake widgets. The live run generated 32 events;
it did not reach the cap. No `PRESENTATION_CONFIRMED` event was added; observed
pixels are test-report evidence only.

### Cleanup, checks, and verdict

The test-only target was restored to port 50010 before recovery. Confidence
returned to .75; manual confirmation, cooldowns, and verification were preserved.
CUA clicked Close Main Presentation and restored the VERSES tab. The control
preview again showed Genesis 1:1. Routing and theme were never edited. VerseVIEW
recent-reference chips now include the test references; they were left intact
instead of deleting application history. The source runner and its owned
headless browser were stopped. Temporary environment cleanup is recorded below.

The created `/tmp/verseview-delivery-verify-20261003` directory, including the
venv and temporary settings/session files, was removed after copying the safe
evidence into this repository. System Python packages and installed application
bundles were not modified. Pip may retain ordinary downloaded-package cache
entries; existing caches were not purged.

Saved detector settings were byte-for-byte unchanged: SHA-256 before and after
`67c625931f0b92d51156cc808b759005cdf79af7ff29eac7442544fc4e99df8b`.
The isolated import smoke check appended one SSL-bundle startup line to the
existing detector log before the runner redirected logging; no existing log
content was removed. Blank test webhook URLs generated Invalid URL errors in
the old notification helper; these were configuration-side ancillary errors,
not delivery failures, and did not transmit to a webhook.

The **39 unit tests**, compilation command, and whitespace check listed above
passed again during verification. Worker replacement/local-only matching remain
focused automated-test results; neither was promoted to a live LLM claim.
This verification changed the investigation document and added the safe evidence
files; it made no further production-code changes.

**Verdict:** the modified source delivered the requested same-chapter transition
to the real installed VerseVIEW output, with additional live safeguard traces
and approved manual delivery. Mock-tested internals remain distinct from live
behavior. Microphone/STT transport, live semantic release, V10 output, full
streaming orchestration, scrolling, small-window usability, and long-run
intermittency are not fully verified. The original production incident still
lacks matched detection/delivery/output evidence and is **not conclusively
explained or proven permanently resolved** by this session.

## Packaged application and microphone verification — October 4, 2026

This stage treats the preceding live-source results as reported evidence, rather
than repeating transcript injection. No transcript callback injection or source
runner is used in this stage. Live speech results below will be filled from the
packaged app's own microphone/STT logs and observed VerseVIEW output.

### Build provenance

- Branch `main`, source revision `0d3bd382a291d77b16f181cb189eadcdd7295ba4`.
- Included the existing working-tree changes in `vv_streaming_master.py` and
  `vv_gui.py`, plus the small layout correction described below. `.gitignore`
  changes were copied but do not affect runtime. The unrelated `.DS_Store` was
  preserved and excluded from staging. Reports/tests are validation material,
  not executable application inputs.
- Used the existing `verseview.spec` and the repository's macOS workflow:
  PyInstaller, then an ad-hoc signature on the separate artifact. No packaging
  specification, signing policy, or system security setting was changed.
- User explicitly approved a temporary PyPI build environment, Homebrew
  PortAudio, and test-artifact signing. PortAudio 19.7.0 was installed; Homebrew
  also performed its ordinary automatic update/cache cleanup. System Python
  packages were not installed or changed.
- Local interpreter: python.org **Python 3.13.15**, Apple Silicon arm64; the
  existing CI workflow selects Python 3.11. PyInstaller **6.22.3**. Exact package
  versions are in `docs/evidence/2026-10-04-packaged/dependencies.txt`.
- Build command:
  `/tmp/verseview-package-build-20261004/bin/pyinstaller --clean -y verseview.spec`
  from `dist/verification-20261004/source`, a copy of the current tracked files.
  Only the staged `version.txt` was assigned a verification build tag.
- Artifact:
  `/Users/kevinanil/VerseView-Detector/dist/verification-20261004/VerseView Detector Test.app`.
  Tag: `verify-0d3bd38-dirty-20261004-531a2b2d`.
- Executable SHA-256:
  `e828065b6ecf445b9a6e39951be3000417d3a0894dd311cfe400afcd2fe2f35a`.
- `codesign --force --deep --sign -` and
  `codesign --verify --deep --strict --verbose=2` succeeded on this artifact.
  This is an ad-hoc signed local test bundle; no notarization was performed.
- Extracted the executable's `vv_gui` code and PYZ archive's
  `vv_streaming_master` code. Recursive comparisons of bytecode, constants,
  nested functions, argument/closure metadata and exception/line tables match
  freshly compiled staged source exactly, omitting only build-specific filenames.
  `verify_archive.py` and `provenance.json` preserve the check and hashes.

CUA launched the **packaged bundle**. Its title shows the verification tag.
At 00:12:06 CDT, PID **11745**, parent PID 1, ran
`.../VerseView Detector Test.app/Contents/MacOS/VerseView_Detector`.
`process-final.json` records the full process path. No `vv_gui.py` or source
runner process was used. The startup log resolves certifi inside the bundle's
Frameworks directory. The existing `/Applications/VerseView Detector.app` was
not replaced or modified.

### Target, settings, and approval

CUA inspected `/Applications/VerseVIEW11.app`, control window
**VerseVIEW 11.0.0 #2**. The resolved remote endpoint is
`http://127.0.0.1:50010/control.html`. Main Presentation is enabled on
**Screen 1 → 1470×956**; Stage and AUX are disabled. Theme is Blue stars motion
background. The user explicitly confirmed isolation from projectors, broadcasts,
livestreams and audiences, and approved the spoken transition, duplicate, manual
and semantic-queue tests. Display routing and themes have not been changed.

Original detector settings SHA-256:
`67c625931f0b92d51156cc808b759005cdf79af7ff29eac7442544fc4e99df8b`.
An original byte-for-byte backup is held in a private temporary directory outside
the repository. No prior session file existed. Provider **Deepgram**, language
**English**, microphone index **2**, verification **on**, manual confirmation
**on**, confidence **.75**, cooldown **3 seconds**, deduplication **60 seconds**,
verse interrupt **off**. Configured cloud/local LLM choices and STT credentials
are retained. Webhook URLs and settings-sync URL were temporarily cleared and
automatic notes saving disabled to keep test activity local; these changes must
be restored after testing.

Device-index enumeration changed between launches: the first artifact listed
index 2 as Kevin's iPhone Microphone; the rebuilt artifact lists index 2 as
**MacBook Air Microphone**. The actual opened device must be confirmed in the
provider log before speech testing; an index alone is not a stable device name.

### Packaged diagnostic layout

The first artifact reproduced clipping at the default **1060×700** window:
both history headers were cut off and only a short transcript region remained,
while the Suggestions region occupied much of the available height.
`default-before.png` preserves the screenshot. Enlarging the window exposed
both headers, separating a geometry problem from absent widgets.

The smallest correction reserves a **200-pixel minimum** for the existing
transcript/history grid row. No panels, controls or delivery guards were
redesigned. The rebuilt packaged artifact visibly shows both history headers,
manual reference entry and a readable transcript region at the same default
size (`default-after.png`). Start, Stop and essential toolbar controls remain
visible at default and enlarged sizes. Diagnostics are still a separate bounded
text panel below Suggestions.

Added a focused real-Tk geometry regression. At a constrained 470-pixel region,
the old row configuration allocates only **68 pixels** to transcript/history and
fails the usable-height check; the corrected configuration passes. Negative
control evidence is in `layout-regression-control.log`. All **40 tests**,
compilation, and `git diff --check` passed after the change.

CUA successfully scrolled the packaged settings sidebar down to Options,
Advanced Settings and Save/Export/Import, then back upward. Evidence:
`settings-scroll.png`. Diagnostic-event scrolling, outcome accessibility while
events arrive, transcription interference, and spoken end-to-end delivery
remain pending at this checkpoint. CUA coordinate
clicks on Start produced no engine-start log or status change even after raising
and enlarging the window. This is not yet attributed to the application: the
user was asked to click Start directly while monitoring continues.

### Real microphone startup checkpoint — 07:39–07:49 CDT

The user clicked Start in the packaged artifact. Its normal engine connected
to VerseVIEW at **07:39:56.533**, opened **[2] MacBook Air Microphone** at
**07:40:01.777**, and connected English **Deepgram Nova-3** over WebSocket at
**07:40:02.070**. PID 11745 remained the packaged executable. This confirms
microphone initialization and provider connection; no speech transcript was
captured in that first startup, so it is not a completed speech-delivery test.
The default 60-second inactivity timer stopped it at **07:40:58.535**, closing
the browser and provider connection. The WebSocket close/send warnings occur
during this shutdown and are not evidence of a missed detected reference.

The stopped app was closed and its normal saved inactivity timeout temporarily
increased from **60 to 600 seconds** for test coordination. After an idle
relaunch, its existing **Auto-Start** preference was temporarily enabled to
avoid another manual Start step. The same unchanged packaged artifact then
auto-started, connected VerseVIEW at **07:48:04.934**, opened the MacBook Air
microphone at **07:48:05.073**, and connected Deepgram at **07:48:05.298**.
These two additional settings must also be restored from the original backup.
No callback injection, microphone substitution, code patch or new delivery
retry was introduced. Explicit-reference FAST-PATH already bypasses hear-twice
verification by its existing design; the verification preference itself stays on.

Startup also reported **Cerebras HTTP 402 / quota required** for the outline
service. This is separate from the successfully connected Deepgram STT and
VerseVIEW controller. No provider billing/account setting was changed.

The user has been asked to speak John 3:16, then John 3:17 after four seconds,
then repeat John 3:17. Two 45-second native-output monitoring intervals captured
zero command acceptances, and no speech text appeared in the provider log at
the checkpoint. Whether the user spoke during those intervals is not established;
do not attribute this absence to an STT failure without that fact. Spoken
transition, duplicate, manual and semantic-queue cases remain unverified.

Separately, at the user's request, CUA changed and verified macOS Lock Screen
preferences: display off after **2 minutes on battery** and **10 minutes on the
power adapter**, both previously Never. These are requested permanent user
preferences, not temporary detector-test settings.


### Actual spoken-reference checkpoint — 08:34–08:41 CDT

The user started the same packaged application again. PID **22495**, parent 1,
started at **07:47:43 CDT** and runs the exact test bundle executable; the
process evidence is in `process-microphone.json`. The microphone log confirms
**[2] MacBook Air Microphone**, opened **08:34:18.761**, and configured
English **Deepgram Nova-3**, connected **08:34:18.971**. No transcript injection
was used. Times below are October 4 CDT; structured events preserve UTC times.

| STT output and time | Candidate | Delivery result |
| --- | --- | --- |
| “Let's give our attention to John chapter three verses sixteen.” 08:34:28.852 | `f18bae740e3d` | DETECTED 08:34:28.860110; DELIVERY_REQUESTED 08:34:28.869601; COMMAND_ACCEPTED 08:34:28.888018 |
| “Let's give our attention to John chapter three verses seventeen.” 08:34:51.424 | `1c71b4d67b84` | DETECTED 08:34:51.451802; DELIVERY_REQUESTED 08:34:51.459056; COMMAND_ACCEPTED 08:34:51.466562 |
| “Let's read John chapter three verses seventeen.” 08:35:01.077 | `9f037adeb504` | DETECTED 08:35:01.093621; SUPPRESSED 08:35:01.116702, exact-reference chapter guard, 0.340 s remaining |
| “John chapter three verses seventeen.” 08:35:11.857 | `b935c4606b99` | DETECTED 08:35:11.862020; SUPPRESSED 08:35:11.865717, configured dedup guard, 39.591 s remaining |

The user supplied speech; the quoted text is the provider's recognized text,
not an independently recorded waveform. **PASS**: real microphone/STT transport,
explicit-reference detection and command acceptance for both references;
**PASS**: duplicate suppression at both guards. Commands were accepted
**22.578544 seconds apart**, so the requested within-ten-seconds condition is
**UNVERIFIED**, not a passing timing test. Visible verse text for either
acceptance was not captured while those commands arrived. CUA subsequently
observed the control window's recent references, which does not establish
actual presentation output. A repeat with a four-second spoken gap is requested.

At **08:35:40.200** the log reports Deepgram WebSocket closure, followed by
sender stop and normal controller shutdown at **08:35:40.959**. The next observed
GUI is Stopped. There is no recorded inactivity message for this shutdown and
its trigger is not established. These warnings occurred after the accepted
references; they do not establish a failed downstream delivery. Preserve them
as a transport/shutdown observation rather than silently treating it as success
for continuous listening. Blank local-test webhook URLs cause ancillary
Invalid URL messages after acceptance; no outbound webhook request succeeded.

CUA observed populated diagnostic outcomes and separate transcription at the
default window, including both SUPPRESSED reasons and candidate IDs. It currently
returns `noWindowsAvailable` for native detector window actions, preventing
verified diagnostic scrolling and approval-button interaction through automation.
This is a Computer Use interaction limitation; no evidence-supported application
change has been made for it. Manual confirmation and semantic queue release
remain **UNVERIFIED** in this packaged microphone stage.


At the user's request, verification was paused for a repository commit and push.
The 40-test suite, compilation and whitespace checks passed again at 08:44 CDT.
Configured credential values were absent from the evidence text being committed.
The original installed application's **588 regular non-symlink files** match the
pre-test manifest exactly (`installed-app-preservation.json`). Temporary detector
settings and the build environment remain in place for the pending verification;
cleanup has not yet been claimed. The separate test bundle remains the artifact
identified above; committing its source does not rebuild or replace that bundle.


## October20,2026 — consumer interface implementation

The separate Electron app now implements normal/Developer Mode and guarded
one-click backend preparation. Detailed provenance, checks and limits are in
[CONSUMER_UI_VERIFICATION.md](CONSUMER_UI_VERIFICATION.md). Packaged synthetic
recovery, approval, bilingual transcript/history and independent scrolling checks
passed. This introduces no new evidence explaining the original intermittent
incident and does not claim a new physical microphone/STT or VerseVIEW output pass.
The original installed detector was not replaced.

## October20,2026 — consumer operator controls, isolated packaged checks

Preview0.13.0 implements Saved sessions, Worship, native Always on top and Emergency
Stop & Save. Desktop revision `66dc11b`, frozen core `0503132`: 194 Python and74
desktop unit checks passed; final Mac package bytes/provenance, extracted archive
startup, frozen crash recovery and the group-of-four packaged UI checks passed.
Computer Use confirmed the final packaged window, session popup/scrolling and
Escape/focus return. Tests used explicit QA callback replay and mocked services/
browser; they did not use real microphone/STT or establish actual VerseVIEW output.

Mode transitions invalidate old approvals, queued/timed work and model dispatches.
Emergency holds delivery before stopping, saves without initiating summarization,
retains old files on failure and blocks queued pre-emergency Start commands from
restarting recognition. These are scoped consumer-control guards, not proof of the
original incident's cause. The original intermittent incident remains unresolved.
Detailed provenance, evidence, CI state and limits are recorded in
[OPERATOR_CONTROLS_VERIFICATION.md](OPERATOR_CONTROLS_VERIFICATION.md). Installed
production app and normal settings remain untouched; overall progress6/8,75%.

## Guarded verse-tools follow-up — October 20–21, 2026

The second four-feature parity group is implemented in a separately packaged 0.14.0
preview: context editing, manual reference entry, selectable accepted history and
chapter browsing/preview. See [VERSE_TOOLS_VERIFICATION.md](VERSE_TOOLS_VERIFICATION.md)
for provenance, candidate evidence, screenshots, tests and CI disposition. Explicit
manual sends retain delivery/epoch, Worship, verification and duplicate guards;
context changes and all previews present nothing. Initial harness requests correctly
hit context quarantine and global cooldown; the harness was corrected without
changing those guards. These findings do not connect the original incident to a
proven cause. Microphone/STT transport, live VerseVIEW output and live semantic
queue release were not retested in this isolated fixture-based feature group.
