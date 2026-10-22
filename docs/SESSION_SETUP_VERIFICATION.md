# Group 5: Languages, startup, timetable and panic shortcut

October 22, 2026 (Chicago). Items 17–20 in the consumer parity plan.
**20/32 implementation packages complete (62.5%)**. This counts scope items, not
elapsed work or physical-platform certification.

## Separate packaged artifact

- Branch `main`, base `62c990b213cbf997d61745670073a016937ca22d` with uncommitted
  Groups 1–5 changes. Existing edits and unrelated `.DS_Store` files are retained.
- Version **0.15.6**, build `2026-10-22T05-17-09-895Z-62c990b2-darwin-arm64`.
- App: `/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-22T05-17-09-895Z-62c990b2-darwin-arm64/VerseView Detector-darwin-arm64/VerseView Detector.app`.
- Frozen companion: `desktop-preview/backend-build/20261022T051212Z-darwin-arm64/backend`.
- Existing workflow: `python desktop-preview/scripts/build-backend.py`,
  `node desktop-preview/scripts/package-native.cjs`,
  `node desktop-preview/scripts/verify-latest.cjs`.
- The old temporary build environment no longer had its virtual-environment
  configuration/dependencies. Under the user's earlier build-dependency approval,
  `/tmp/verseview-group5-build-20261022` was recreated using the exact dependency
  freeze from Group 4's companion manifest. No additional dependency or Homebrew
  installation was introduced. This environment is retained for subsequent builds.
- Sibling `provenance.json` records the dirty source, command, dependencies and
  hashes. **30 companion inputs and shipped frontend runtime hashes match current
  source**. Excluded verification harnesses/documentation can change afterward.
- Existing strict package verification passes with **59 packaged files** and the
  production frozen companion, using the already approved separate-artifact
  ad-hoc signing. No installed-app replacement, security-setting change, commit,
  push, release publication or paid signing/notarization occurred.

## Implemented choices and limits

1. **Language/display:** normal Settings exposes provider transcription, existing
   English translation, or supplied transliteration. Primary/secondary language,
   provider and enable controls stay on Live. Views make no extra provider calls;
   unavailable representations are explicitly labeled and retain supplied text.
   Original source remains accessible when displaying English translation.
   A Sarvam Malayalam transliteration request applies on the next Start and is
   constrained to the Malayalam stream. Manglish is labeled as provider
   transliteration, never reconstructed Malayalam script. Journal, full-history
   paging, saved-session capture/restore and text export retain that provenance.
   The existing STT/translation/detection algorithms are reused.
2. **Auto-start:** a separate, typed local preference requires a fresh opt-in on
   each computer. Legacy `auto_start` and credential sync cannot enable it. On the
   next launch, microphone permission must already be granted; preparing the
   owned backend does not capture audio. Recovery choices, missing microphone,
   missing credential presence and unsupported scheduled provider combinations
   pause automatic listening. An eight-second countdown offers Cancel; editing
   speech/schedule settings cancels it. Readiness/sync guards still apply when
   sending the single Start. Stop does not re-arm it. Permission unknown/denied or
   an interrupted connection requires explicit operator attention, not a retry.
   Credential presence is not proof that a cloud key is valid.
3. **Smart Schedule:** editor for up to 16 weekday/start-time/language entries,
   reset to the original timetable, duplicate/invalid-slot rejection, system/UTC
   or available IANA zone selection, and effective next-Start preview on Settings
   and Live. The latest entry lasts until midnight; before the first entry and on
   unscheduled days, saved speech choices apply. English selects one stream;
   Malayalam/Hindi add the supported English secondary configuration. The primary
   provider is retained; incompatible scheduled combinations block Start with an
   error rather than silently changing providers. No timer starts recognition or
   changes live streams. Named-zone availability is validated on the computer;
   use system/UTC if its runtime lacks IANA data (not yet certified on Windows).
4. **Panic shortcut:** typed custom shortcut and Reset to Shift+Escape on both
   desktop platforms. Exact modifier matching, key-repeat/composition protection,
   known quit/debug conflicts, dialogs and letter shortcuts during typing are
   guarded. Scope is the focused detector window; no OS global registration or
   new accessibility permission is requested. The legacy Windows background key
   listener is disabled only for the desktop host. Panic clears presentation
   while listening continues; Emergency Stop & Save remains distinct.

## Verification and evidence

- **245 Python regressions pass:** schedule boundaries/day expiry/time zone,
  source immutability, missing readiness inputs, typed preference validation,
  shortcut conflicts, stream-limited Sarvam configuration and transliteration
  journal/capture/export provenance, alongside prior suites.
- **94 desktop regressions pass:** typed boundaries, source/translation labeling,
  local consent schema/persistence/claim-once/cancel, permission and recovery
  pauses, no repeat after Stop, and focused shortcut guards.
- Syntax/offline checks and `git diff --check` pass.
- Packaged verification uses explicit disposable QA profiles. Actual owned frozen
  backend, actual renderer/main preference and command paths are exercised.
  Speech, translation, microphone permission, controller and network services
  are explicit QA substitutes. They prove workflow behavior, not real speech
  recognition or pixels on VerseVIEW.
- The initial UTC timetable test expected the 12:00 local fixture to stay 12:00
  after selecting UTC. Correct conversion selected the later Hindi entry at
  17:00 UTC. Only the fixture's later Sunday entry was adjusted to English;
  runtime conversion was retained. The failed run's screenshot/log are preserved
  as `initial-utc-fixture.*`.
- **Final packaged workflow PASS**, actual packaged executable and frozen owned
  companion recorded in `results.json`: legacy startup opt-out, supplied Manglish
  and English translation, original text access, focused panic/typing/dialog
  guards, editable UTC timetable and single-stream next Start, saved dual-stream
  preference unchanged, duplicate slots/reserved keys rejected, local opt-in
  persistence, recovery pause, one automatic Start, Stop remaining stopped and
  countdown Cancel sending no Start. No renderer errors.
- **36 size/layout/theme combinations PASS**, widths 1180/900/660, Studio/Focus,
  six themes; no horizontal overflow and emergency controls remain reachable.
  Bounds do not establish every Glass backdrop's text contrast.
- **Computer Use PASS** on the exact final packaged `app.asar`: styled timetable
  and shortcut fields, page scrolling with safety controls visible; typed and
  saved a custom shortcut, then reset it to Shift+Escape and confirmed the saved
  default in the owned QA settings file. Initial native typing began before the
  focused field was observed; explicitly selecting the focused field retained the
  entire typed value. No app text-editing defect was reproduced.
- The first Computer Use pass showed cramped browser-default controls. New fields
  now use the established themed input styling, and technical descriptions were
  shortened. The final package repeated the acceptance/layout checks.
- **Existing Live regression PASS in the final package**, another 36 size/layout/
  theme cases: drafts/caret and preview, pin/Worship, bilingual saves, dialog focus,
  emergency save and restart recovery. Its executable identity is recorded in
  `desktop-preview/test-results/live-layout/results.json`.

Evidence lives in `desktop-preview/test-results/session-setup/`: `results.json`,
`source-hashes.json`, `settings-narrow.png`, `computer-use-styled-fields.png`,
`computer-use-shortcut.png`, `computer-use.json`, and the initial fixture/styling
evidence. Temporary execution logs remain in `/tmp/vv-group5-*`.

## Remaining acceptance scope

Real provider transliteration accuracy, microphone/STT, real OS permission prompt
behavior and actual visible VerseVIEW output are **unverified for this group**.
Native Windows/Intel packages/keyboard/hardware behavior are **unverified**; shared
code and native path policies do not establish physical platform acceptance.
Prior Glass navigation contrast and long-note inner-scrolling acceptance gaps
remain in the Group 8 list. The original intermittent delivery incident remains
**unresolved**.

Runtime changes: `desktop_setup.py`, `service_schedule.py`, shared desktop settings,
backend/control, observer feed, operator/session/notes provenance, engine provider
configuration/telemetry; `launch-preferences.cjs`, main/preload, feed decoder,
`src/session-policy.js`, `session-setup.js`, settings/observer rendering, HTML/CSS,
package manifests and build/verification allowlists. Extended existing regressions,
added focused setup tests/packaged acceptance, and retained their Python test in
the narrow `.gitignore` allowlist. No real settings, keys, saved sessions or
installed application files are edited by these QA checks.

Disposable setup/auto-start/cancel and Live regression profiles, their private
settings and owned test app/companion processes were removed/closed. The seed
source settings remained unchanged. Separate builds/evidence and the approved
temporary build environment are retained; no real settings needed restoration.
Next chunk is **Group 6 (items 21–24)**: Google credentials/import, ATEM controls,
local-model setup, and bounded Test connection/Warm selected model actions.
