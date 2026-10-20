# Free cloud API audit — 2026-10-20

## Drive sync configured — October20 14:11 CDT

At the user's request, the normal0.11.5 preview backend was closed while stopped,
its private settings backed up, and settings_sync_url set to the existing Drive
file's download endpoint. Bundled backend33454 was relaunched. Its actual observer
sync status reports **applied**,4 credential fields updated, configured=true,
busy=false, completed2026-10-20T19:11:54.681380Z. Recognition remains stopped and
free-cloud routing is retained. Startup sync now runs when this backend launches;
this does not establish continuous polling or configure any other machine.
No microphone/presentation command or installed-app replacement occurred.
Local sanitized evidence: `/tmp/verseview-active-provider-check/drive-sync-result.json`.

## Active preview credential verification — October20 13:48 CDT

The user requested applying the obtained keys, then verifying the routes. The
normal preview profile now contains the candidate Groq/Gemini/Cloudflare
credentials and reviewed free-only routing; auto-start is off. A private pre-change
backup is retained beside settings.json. Packaged0.11.5 is running with frozen
backend31945; Computer Use shows backend ready, recognition stopped, and saved
session recovery awaiting a choice. No microphone/presentation was started.

The existing Drive file returned200 and all four recommended credential/account
fields matched this active profile, without exposing values. The preview's own
settings_sync_url is empty: this confirms the uploaded file matches, not that
automatic sync is configured in this particular preview profile. No sync setting
was changed in this verification.

Three bounded public/synthetic text requests used this profile's exact routes,
credentials and shared usage ledger. The source adapter/watcher hashes matched
the packaged provenance. Cloudflare English watcher identified Psalm23:1 (1.850s),
Groq extracted John3:20 (0.213s), and Gemini returned a faithful short synthetic
mercy summary (9.335s). All three succeeded without retry/provider substitution.
These were matching-source adapter probes, **not requests through the running
backend**, a fresh Malayalam evaluation, or a full live outline/speech test.
Local evidence: `/tmp/verseview-active-provider-check/result.json`. No keys were
printed; production settings and installed app remain unchanged.

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

## Implementation follow-up — verified account checks and candidate 0.11.4

**[████████████░░░░] 75% — 6/8 overall milestones.** The source implementation
and separate Mac ARM64 candidate are verified within the scope below. No production
installation or activation was performed. The original research-only audit follows
this section unchanged; its proposed routes are superseded by measured results.

### Selected routes

| Role | Selected provider/model | Evidence and limit |
| --- | --- | --- |
| Verse extraction / queued semantic check | Groq `qwen/qwen3.8-27b`, reasoning disabled, 48 output tokens | 10/10 fixed public English/Malayalam cases; 0.297–0.638s. Indirect scripture was correctly rejected by explicit-reference extraction, while positive semantic comparisons matched. |
| English watcher | Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8`, `/no_think`, 220 output tokens | All 6 English cases across the basic/extended suites matched expected references or negatives. Basic replies 0.706–1.137s; expanded English replies 0.700–0.968s. |
| Malayalam watcher, including Manglish on the Malayalam stream | Groq `qwen/qwen3.8-27b`, reasoning disabled, 220 output tokens | 6/6 Malayalam cases, including Psalm23:1 and spoken Romans8:28; 0.398–0.977s. Shares the Groq ledger with verse/translation calls. |
| Summary / outline | Gemini `gemini-3.5-flash-lite`, minimal thinking | The complete synthetic bilingual summary fixture (39,172 primary +10,612 secondary characters) used 12,330 input/196 output tokens and completed in27.883s. A separate Malayalam-only-detail fixture completed in20.427s and retained its family-forgiveness application in English. Outline transport uses this same adapter, with a1,500-token cap; a live outline generation was not exercised. |

These are small reproducible comparisons, not a production accuracy estimate.
Cloudflare Llama8B missed the Malayalam John3:16 paraphrase (5/6 basic cases).
Cloudflare Qwen30B passed all6 basic cases but only4/6 expanded cases: it missed the
Malayalam Psalm23:1 paraphrase and returned Romans8:21 for spoken8:28. It is therefore
**not** the default Malayalam route. Gemini Flash-Lite returned correct content in
all6 basic watcher cases, but4/6 took longer than the existing20s watcher timeout
(13.254–27.895s overall), making it unsuitable for the current frequent watcher.

Gemini `gemini-3.8-flash` returned503 on the long summary attempt. A separately
planned short-fixture diagnostic also returned503, specifically at completion after
the token-count stage. No automatic retry or fallback occurred. These observations
do not establish bad credentials or permanently unavailable models. The initial
long-failure report also records a second cache-check invocation; its persistent
hold prevented another inference request. Flash3.8 remains an explicitly selectable
reviewed-free model, not the selected working summary route.

Summary limitations remain visible: the existing formatting duplicates the final
Verses Cited list, and the short fixture's Notable Quotes section said “Not covered”
despite retaining “Mercy takes time” in the body. No invented speaker, healing story,
fundraising request or extra verse was found in these two fixtures. Repeated prose
was condensed. This is not a comprehensive omission/hallucination audit, and no
private sermon or session transcript was uploaded.

### Accounts actually inspected

- The user resolved the personal Google account ambiguity, then approved
  the displayed Groq and Cloudflare terms. The university account's initial AI
  Studio denial was **not** treated as a denial for the personal account.
- Groq Personal / Default Project shows **Free, $0, Current Plan**. The saved key's
  masked suffix matches a key in that account. Qwen limits shown there are30RPM,
  1,000RPD,8,000TPM,200,000TPD, agreeing with the [official limits](https://console.groq.com/docs/rate-limits).
- AI Studio's selected Gemini Project shows **Free tier** and its saved-key suffix
  matches that project. Its displayed Flash-Lite3.5 limits are15RPM/250KTPM/500RPD;
  Flash3.8 is5RPM/250KTPM/20RPD. No billing was linked. Model limits are1,048,576
  input and65,536 output tokens, per the [Flash-Lite model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).
- Cloudflare shows **Workers Free, Current plan**. At the user's explicit request
  to complete token creation, a token limited to this account's Workers AI Read/Edit
  was created, verified active, and exercised successfully. It is stored privately
  in the inactive candidate profile, not in this repository. The official daily
  allocation is10,000 neurons; paid-only models are excluded from the adapter's
  allowlist. See [pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/).
- OpenRouter was evaluated from [official pricing](https://openrouter.ai/pricing):
  20RPM/50RPD without purchasing credits. No account/key was created or tested.
  The working Gemini allowance does not justify a fourth provider at present.
  No claim is made about this user's OpenRouter account entitlement.
- Deepgram/Sarvam credit balances were not inspected in this follow-up. Their
  signup grants remain finite; no recurring-free STT entitlement is established.

Read-only account screenshots are private under `/tmp/verseview-provider-review/`.
One browser sign-in observation exposed a temporary Cloudflare authentication token
in a redirect URL before filtering was applied. Subsequent observations filtered
redirect tokens; no such URL or credential was saved in repository evidence. The
new Workers AI API token was not printed or included in screenshots.

### Implemented budgeting and behavior

`free_cloud.py` adds an **opt-in** profile (`free_cloud_enabled=false` by default).
`free_cloud_config.routes` selects provider/model per role, with a separate
`watcher_malayalam` route. The watcher passes its actual stream language. Existing
private credentials/settings are not migrated or activated automatically. The
legacy GUI preserves these private fields during saves; the standalone backend
maps them through its existing settings path. Credential sync cannot change routing
or opt a profile into this behavior.

Free mode bypasses local clients, legacy Mistral/Cerebras cascades and the Cerebras
startup inference ping. A provider must be explicitly listed in
`verified_free_providers`, have its own credential, and use a reviewed model. Missing
setup stops the role; no provider switch, paid model, key rotation or automatic retry
is introduced. Sarvam's saved quota-backup key is suppressed **at runtime in free
mode**; the saved value and legacy behavior are retained. This does not make Sarvam
STT itself recurring-free.

One SQLite ledger per profile reserves requests, input/output tokens and neurons
atomically across streams, roles and processes. It survives engine restarts. It
uses conservative rolling24h caps, rather than refilling at differing provider
calendar resets. Groq remaining-request/token headers further constrain available
capacity. Actual returned token usage reconciles reservations; failed/missing-usage
responses keep the conservative reservation. Local ledgers cannot observe every
other application's usage; the provider's free-account hard limit remains authoritative.

The watcher has a **20s global dispatch floor by default**, applied before either
timer or volume triggers dispatch and enforced again at the shared ledger. Both
streams alternate priority. An explicitly configured floor may be lowered to10s,
with reduced service duration. The probes used10s and paced distinct cases11s apart;
one overlapping probe was correctly stopped by this global budget before inference,
then its remaining distinct cases were run sequentially. No successful case was
repeated to work around a provider limit. A still-finishing timed-out watcher call
cannot accumulate additional queued HTTP calls behind its lock.

Groq optional work leaves200 daily requests/40K daily tokens and10RPM/3KTPM for verse
checks. These are independent reserves, not a guarantee of200 verses of any size.
Optional feature caps are1,200 watcher calls,300 translations,120 outlines and20
summary attempts per rolling24h. Cloudflare has a9,000-neuron local budget, leaving
10% below its published allocation. Cloudflare30RPM/2,000RPD/100KTPM/1MTPD and
Gemini2MTPD are **application safety ceilings**, not additional advertised allowances.
Private limit overrides can only lower the reviewed ceilings.

Identical work is cached in bounded process memory; prompts/replies are not stored
in the ledger. Unchanged complete bilingual summaries use a stable input/reference
cache key even if the display timestamp changes. Complete summary input is retained;
Gemini `countTokens` checks it before inference, and oversized input is rejected
without dropping text. Watcher/verse requests use a conservative UTF-8-byte token
bound, avoiding the unsafe chars/4 estimate for Malayalam. Truncated/empty/invalid
outputs are not accepted. Authentication, permission, model, quota, rate, transport,
context and busy failures have safe actionable messages in the existing backend
status area. Holds prevent repeated dispatch after server failures; auth/model/quota
holds are conservatively24h, ordinary rate/transport holds respect at least60s.

### Expected capacity: one or two streams

At20s globally, the ceiling is180 watcher calls/hour **total**. One stream gets up
to180/hour; two continuously active streams share about90/hour each. The40s/10-line
context bounds remain. This is deliberately slower than the old5s timer/2.5s volume
path; it is a real global budget, not a timer-only change.

| Workload | Illustrative capacity with selected routes |
| --- | --- |
| One English stream |1,200/day feature cap gives up to6h40 at180/hour. The measured English request costs are well below the9K-neuron cap at that count. Longer windows/output or other account usage can reduce it. |
| One Malayalam stream | Measured mean433 tokens/call; Groq's160K optional-token budget gives about369 calls, roughly2h03 at180/hour before optional translation/other Groq work. Verse reserves remain. |
| English + Malayalam streams | Same180/hour total, split90/90. The same Malayalam budget is about4h06 of concurrent elapsed listening, subject to both streams' actual prompt sizes and other usage; no promise of independent full quotas. |
| Five long bilingual summaries | At the measured12,330+196 tokens each, about62,630 combined tokens/day. Five fit the observed15RPM/250KTPM/500RPD allowance if other traffic leaves capacity. |
| Ten or more summary tests | The local20-attempt cap supports typical5 summaries plus10 tests. Large simultaneous inputs can hit the minute budget; they must be spaced rather than retried blindly. At20K input +6K reserved output,9 requests fit a250K combined local minute budget; the next waits. |

These are arithmetic from measured fixtures and configured ceilings, **not** a
guaranteed service duration or an estimate of unseen transcripts. At10s the same
token allocation lasts approximately half as long. Weekly inactivity does not bank
unused daily capacity. Continuous Malayalam translation can materially shorten the
Groq budget; raw source text is retained when translation is stopped by the budget.

### Privacy and STT decision

The [Groq data policy](https://console.groq.com/docs/your-data) describes no default
inference-content retention, with reliability/abuse exceptions up to30 days and
optional ZDR. Account ZDR settings were not changed. [Workers AI data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/)
states no model training on customer content and standard inference retention only
as needed, subject to its exceptions. Gemini's unpaid-service terms permit product
improvement and human review and instruct against submitting confidential/sensitive
material; see [API terms](https://ai.google.dev/gemini-api/terms). Public/synthetic
test text was used throughout. A saved key does not authorize uploading private
sermons or override these terms.

Gemini `gemini-3.5-transcribe-live` remains the strongest documented next STT
candidate: the inspected project lists20KTPM and unlimited RPM/RPD entries. These
are displayed metrics, not proof of unlimited session concurrency/duration. The
[official streaming guide](https://ai.google.dev/gemini-api/docs/live-api/live-transcribe)
supports English/Malayalam, language detection/code mixing, interim/final events
and16kHz mono16-bit PCM. At the pricing page's25 audio tokens/second, one/two streams
would use approximately1,500/3,000 input audio tokens/minute before transcript and
other accounting. Concurrency, session lifetime/reconnection and real recognition
quality still need a bounded coordinated test. No STT adapter, audio upload or live
microphone session was added in this LLM-provider milestone. The current Deepgram/
Sarvam path therefore remains a finite-credit dependency, not a proven perpetual
zero-payment end-to-end service. Local models remain deferred.

### Verification and inactive candidate

- Branch `codex/desktop-backend`, inspected HEAD `e039a0d2`; runtime changes are
  **uncommitted**, with exact hashes in the backend manifest. Prior uncommitted
  reports and unrelated `.DS_Store` were preserved.
- **PASS169 Python tests**, including18 focused free-cloud checks for shared atomic
  budgets, reserves, persistence, server remaining capacity, per-language routing,
  both dispatch triggers/fairness, cache, large UTF-8 input/token count, no retry,
  sanitized failures and guarded engine integration. **PASS50 Node tests**, syntax/
  offline-page checks and whitespace checks.
- **PASS** separate0.11.4 frozen startup; native bundled inventory and existing
  ad-hoc package verification; archive extraction and extracted frozen startup.
  **PASS** existing frozen bilingual watcher/manual/duplicate/stopped-action suite,
  with fake models/STT/browser. It does not establish real speech or presentation.
- Source public probes are reproducible with
  `desktop-preview/scripts/probe-free-cloud.py`, which requires an explicit free
  account assertion and uses only fixed text. Local ignored result files are under
  `desktop-preview/test-results/free-cloud-20261020/`, including measured checks and
  preserved failed/blocked probes. The private ledger is not a public evidence file.
- App: `desktop-preview/out/2026-10-20T16-58-31-120Z-e039a0d2-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
  Archive: `desktop-preview/out/deliverables/2026-10-20T16-58-31-120Z-e039a0d2-darwin-arm64.tar.gz`.
  SHA256: `6fa811f0de3e3ea38691a5f2dafad2a66c6b9da08d3b07b8d3180abfc49fb2d2`.
- An **inactive** private candidate configuration is prepared at
  `~/Library/Application Support/VerseView Free Cloud Candidate/Backend/settings.json`
  (700 directory/600 file). It contains the confirmed routes/credentials, no copied
  session transcripts, auto-start off, watcher off, and disabled automatic settings
  pulls/Discord outputs. It is a staged configuration; the desktop shell still uses
  its existing profile unless activation is explicitly arranged. Do not launch a
  new instance into the existing normal backend profile casually.
- Active production settings still hash to
  `e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`.
  The active preview settings were not written. `/Applications/VerseView Detector.app`
  was not replaced. No dependency installation, payment method, paid plan, signing
  configuration change, release publication or real microphone/presentation command
  occurred. No new Windows/Intel native CI run is claimed for this change; Windows
  physical acceptance remains explicitly deferred.

Next gates: arrange a bounded candidate microphone/outline test with the user,
review Gemini free-service privacy before private transcript use, and separately
evaluate/integrate recurring-free streaming STT. Production replacement/signing
still requires its own tested rollback/replacement approval. The original
intermittent delivery incident remains unresolved; overall milestone count stays75%.

---

## Original research-only audit (preserved)

Research and source inspection only. No new inference requests, credential changes,
account creation, billing enrollment, dependency installs or presentation commands.
Published allowances are not proof of this user's account entitlement or capacity.

## Recommendation

Keep Groq for bounded verse/semantic calls. Evaluate Cloudflare Workers AI for the
frequent context watcher, Gemini for occasional complete-sermon summaries, and
OpenRouter free models as a low-volume summary fallback. These new routes need
adapters, account-specific quota checks and English/Malayalam evaluation before
being enabled. A saved key field alone does not establish an implemented route.

| Service | Verified public offering | Suitability / limitation |
| --- | --- | --- |
| Groq | Qwen `qwen/qwen3.8-27b` and GPT OSS 20B/120B: 30 requests/minute, 1,000/day, 8,000 tokens/minute, 200,000/day | Recurring free plan; reserve capacity for verse delivery. Limits are organizational; exact account limits may differ. |
| Cloudflare Workers AI | 10,000 neurons/day, reset 00:00 UTC; Workers Free rejects excess usage | Strong watcher candidate; small-model accuracy must be measured. Avoid models requiring paid billing. |
| Gemini | `gemini-3.5-flash-lite`, `gemini-3.8-flash` have free input/output; `gemini-3.5-transcribe-live` also lists free input/output | Summary and streaming-STT candidates. Actual model quotas are project-specific in AI Studio; no universal call count promised. Free-tier content may improve Google products. |
| OpenRouter | Free models: 20 requests/minute and 50/day without buying credits | Appropriate for 5–10 summary attempts/day if context limits fit. 1,000/day requires a $10 purchase and fails this user's strictly free requirement. |
| Deepgram | New-account $200 credit, usable until consumed | Finite signup grant, not replenishing free allowance. Existing account balance unknown. |
| Sarvam | Signup ₹100 credit; published streaming STT ₹30/hour | Finite grant, approximately 3h20 if spent solely on this STT rate. Prior primary-key quota error remains relevant; a backup key does not create more credit. |
| Cerebras | Current pricing explicitly describes a one-time $5 promotion requiring payment method, expiring in 30 days | Do not budget as recurring free production capacity. Pricing table extraction is incomplete; no claim that this lists every possible account entitlement. |
| Mistral | Official help describes Free mode for evaluation/prototyping and directs users to organizational limits | Current production entitlement/model availability not established; exclude from dependable free routing until the account confirms it. Do not infer removal solely from community reports. |

## Workload and budget

`contextual_watcher.py` keeps up to 10 lines / 40 seconds, skips unchanged or
insufficient speech, defaults to a 5-second timer, and can dispatch sooner on
25 new words / 3 lines subject to a 2.5-second minimum gap per stream. Two streams
can increase load. Changing only the timer would not impose a global request cap.
The watcher is experimental and disabled by default.

A timer-driven 5-second workload is 720 requests/hour per stream; volume triggers
can increase that. Illustratively, 500 input + 100 output tokens per request would
consume 432,000 tokens/hour. Groq's daily token limit would arrive before its
request limit, even before verse/translation/outline calls. This is arithmetic,
not a measurement of the user's actual token usage.

Cloudflare lists its fast Llama 3.1 8B at 4,119 neurons/million input tokens and
34,868/million output tokens. The same illustrative 500+100-token request costs
5.5463 neurons: about 1,803 calls per daily allocation if no other model consumes
it. At 720/hour this is about 2.5 hours for one stream, or 1.25 hours for two.
Longer prompts, other features and outputs reduce that. Quality is unverified.

Summaries send the complete primary transcript plus the complete secondary
transcript when present. Five calls/day can still exceed token-per-minute or
per-request limits. For example, five 20,000-input-token summaries consume at least
100,000 input tokens; Groq's 8,000 TPM is a poor match for those requests.
Weekly inactivity does not multiply a daily allowance on the service day.

Groq Whisper free-plan published limits are 20 requests/minute, 2,000/day,
7,200 audio seconds/hour and 28,800/day. Its documented interface accepts uploaded
audio files/URLs; integrating microphone chunks requires buffering, overlap
deduplication and latency testing. It is not a drop-in replacement for the current
Deepgram/Sarvam streaming transports. Parallel transcription and translation can
consume additional quota. Gemini Transcribe Live is a separate promising streaming
candidate, pending access, quotas and actual Malayalam/English tests.

## Existing compatibility findings

- Recent packaged verse matching uses `qwen/qwen3.8-27b`; previous bounded account
  model listing and positive/negative probes established availability for that
  saved Groq credential at that time, not free-tier status or broad quality.
- `vv_streaming_master.py` still requests `llama-3.3-70b-versatile` for live
  outlines and summary fallback (lines 2363 / 2501 at inspected revision). It was
  absent from the previously captured account model list. Fix these routes before
  describing all Groq-dependent features as compatible.
- Watcher standalone defaults retain older model names; engine-injected Groq
  routing uses the updated constant. Cerebras/Mistral fallbacks need explicit
  availability checks, not assumptions based on key presence.
- Gemini is accepted by configuration, but the inspected summary and watcher
  routes do not implement Gemini selection. Cloudflare and OpenRouter need
  explicit integration too.

## Proposed implementation acceptance criteria

1. Separate provider/model choice for watcher, verse/semantic, outline and summary.
2. Validate model access without exposing keys; distinguish authentication, missing
   model, quota/balance exhaustion, rate limit and transport errors in the UI.
3. Shared request/token budgets across streams and features; reserve verse capacity.
   Meter actual usage and impose a global dispatch floor, not just a watcher timer.
4. Strict free-only provider/model allowlist; never automatically switch to paid
   routes or enroll billing. Stop optional features visibly when limits run out.
5. Cache identical work, bound watcher context, and avoid regenerating unchanged
   summaries. Keep all delivery confirmation/dedup/semantic guards intact.
6. Evaluate English/Malayalam explicit references, paraphrases and negative cases;
   test long bilingual summaries for omissions/invention before claiming quality.

## Official sources and key creation

- [Groq limits](https://console.groq.com/docs/rate-limits),
  [speech interface](https://console.groq.com/docs/speech-to-text),
  [create own key](https://console.groq.com/keys).
- [Cloudflare pricing and model neuron rates](https://developers.cloudflare.com/workers-ai/platform/pricing/),
  [account dashboard](https://dash.cloudflare.com/).
- [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing),
  [project-specific limits](https://ai.google.dev/gemini-api/docs/rate-limits),
  [AI Studio keys](https://aistudio.google.com/apikey).
- [OpenRouter pricing](https://openrouter.ai/pricing),
  [keys](https://openrouter.ai/settings/keys),
  [free model catalog](https://openrouter.ai/models?max_price=0).
- [Deepgram pricing](https://deepgram.com/pricing),
  [key instructions](https://developers.deepgram.com/guides/fundamentals/make-your-first-api-request).
- [Sarvam credits](https://docs.sarvam.ai/api/getting-started/ratelimits),
  [pricing](https://www.sarvam.ai/api-pricing),
  [shared billing](https://docs.sarvam.ai/api/platform/billing).
- [Cerebras current pricing](https://www.cerebras.ai/pricing).
- [Mistral official rate-limit guidance](https://help.mistral.ai/en/articles/698531-why-am-i-hitting-api-rate-limits-and-how-do-i-increase-them).

Keys must be generated in the user's own account and stored privately. Multiple
keys under a shared organization/project do not multiply its allowance. No leaked
or shared credentials are needed. Terms, capacity and model catalogs can change.
