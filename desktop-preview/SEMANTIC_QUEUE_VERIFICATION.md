# Semantic queue preparation — October 20, 2026

**[████████████░░░░] 75% — 6/8 milestones complete.** Live spoken semantic release
remains **UNVERIFIED**; the user has deferred physical Windows testing. Native
Windows build checks continue, without claiming graphical/hardware acceptance.

## Demonstrated blocker and minimal correction

The actual saved verse-role route is cloud, with a configured Groq client. Queue
matching prefers that client; the separate Cerebras HTTP402 is not proof that Groq
is unusable. An existing-code preflight fetched **John3:20 KJV** successfully, then
received **HTTP404** for the hardcoded `llama-3.1-8b-instant`. The bounded probe
stopped on that response without retrying or switching accounts. A read-only
configured-account model listing returned200 and omitted that model.

A separate disposable-process compatibility probe used an available model,
`qwen/qwen3.8-27b`, with `reasoning_effort=none` and the production48-token bound.
The actual semantic prompt returned YES for the full verse and NO for an unrelated
microphone greeting (both HTTP200). It used public verse text/test text, not a
microphone or private sermon. Groq documents instruct mode with reasoning disabled
for this model: [model documentation](https://console.groq.com/docs/model/qwen/qwen3.8-27b),
[reasoning parameters](https://console.groq.com/docs/reasoning).

The engine now uses one shared `GROQ_VERSE_MODEL` constant for existing Groq verse,
semantic and fallback call sites; the Groq request wrapper and direct translation
request specify the model's instruct mode. This replaces references to the
unavailable model without changing prompts, queue identity/expiry, confidence,
manual confirmation, verification or dedup guards. No new retry or account/provider
fallback was added. Existing retry behavior is unchanged. Two regressions verify
request model/mode/token bounds and semantic YES/NO routing.

## Exact artifact and validation

- Runtime source: **`a9d0314881aa647964d9da42789b23979644835a`**, branch `codex/desktop-backend`.
- Version **0.11.3**. Build commands: existing
  `python desktop-preview/scripts/build-backend.py`, then
  `node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64`.
- Frozen input: `desktop-preview/backend-build/20261020T082908Z-darwin-arm64/backend`.
- App: `desktop-preview/out/2026-10-20T10-37-03-019Z-a9d03148-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
- Archive: `desktop-preview/out/deliverables/2026-10-20T10-37-03-019Z-a9d03148-darwin-arm64.tar.gz`.
  SHA256 **`30dead739cf7e6333d1cec216599f536593db8b57355f8ea06b34c17973db4ec`**.
- Provenance: no uncommitted runtime changes; unrelated untracked `.DS_Store` excluded.
- **PASS:**151 Python tests,50 Node tests, syntax/offline-page and whitespace checks.
- **PASS:** actual packaged backend lifecycle regression, with isolated fake
  microphone/provider/controller; no claim of speech or visible output from it.
- **PASS:** packaged source/native inventory, ad-hoc signature, archive extraction
  and extracted frozen no-input startup. Original installed detector intact.
- **PASS:** [native CI39393732698](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39393732698)
  on Windows x64, Mac ARM64 and Intel Mac, including frozen features and extracted
  archives. Local API metadata: `desktop-preview/build/verification/ci-39393732698.json`.
- **PASS:** offline existing-engine/fake-browser scenario establishes that, with
  John3:19 active, “Let us read verses nineteen through twenty.” queues John3:20
  while verification stays enabled. No browser command was issued by that check.

## Actual normal packaged preparation

Computer Use gracefully quit the previous0.11.2 app and its stopped backend, then
launched the exact new bundle above: actual dashboard **PID19755**, frozen host
**PID19764**. Process executable paths resolve inside that artifact. Saved-context
recovery is staged; **Start is enabled and recognition remains stopped**. Nothing
was presented or recorded by preparation. This is the packaged app, not the source
script. Screenshot/readiness evidence is local under
`desktop-preview/test-results/semantic-queue-20261020/`.

Preview settings equal the restored pre-bilingual baseline, with English/Deepgram,
dual STT off, confidence0.75, manual/verification on, verse interrupt off and KJV.
Production settings hash remains
`e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`.
No persisted settings, credentials, system security or display timeout changes.
The lifecycle harness's synthetic QA Backend was removed after its children exited;
its temporary sources and extracted archive were cleaned by existing harnesses.
Separate artifacts, approved build environment, private profiles/logs and the
normal stopped host remain available for the next coordinated user test.

## Next live test — not yet a pass

On the previously approved isolated VerseVIEW target, the user will Start and say
“John chapter three, verse nineteen.” Once19 appears, say “Let us read verses
nineteen through twenty.” Allow the queue to fetch, then read the actual KJV20
text without announcing another explicit reference:

> For every one that doeth evil hateth the light, neither cometh to the light,
> lest his deeds should be reproved.

Capture real STT, the John3:20 QUEUED candidate ID, fetched translation, semantic
check and YES/NO, same-ID delivery request/acceptance and actual visible verse20.
A direct explicit20 reference would exercise the fast path instead. Reading must
occur inside the existing180-second queue expiry. Do not force a match, bypass
guards or inject a transcript. Stop after the bounded attempt and preserve a
failure at its last confirmed/first failed stage. No successful live queue release
or original-incident explanation is claimed by these preflight/build checks.
