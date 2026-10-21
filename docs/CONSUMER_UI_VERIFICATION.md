# Consumer workspace implementation — October 20, 2026

Version0.12.0 implements the approved consumer interface plan in the cross-platform
Electron application. The original `/Applications/VerseView Detector.app` is not
replaced. Developer Mode is a local appearance preference, off by default; it
cannot elevate permissions or bypass controller, recovery, settings or cloud guards.

## Result

Normal navigation is Live, Outline, History and Settings. The titlebar source and
layout pickers, technical runtime panels, IDs, event stages and sample tools are
absent from normal mode. Appearance/layout lives in Settings. Settings → Advanced
→ Developer Mode reveals Runtime, Diagnostics, Test area, Cloud tuning, Build
information and the existing diagnostic surfaces. Disabling it from a developer
page returns to Live and exits sample mode; sample state is cleared. Saved themes,
settings, credentials, recovery and engine state are preserved.

Live has a compact status and Start listening/Stop listening/Clear output. Stop
remains in the header on other screens, including when the sample source is open.
Normal output distinguishes detection, holding, queueing and command acceptance;
it never claims verified presentation pixels. Approve/Dismiss remain usable.
English/Malayalam stay separate, with a disabled secondary stream omitted. The
Focus/Full transcript switch and smooth Jump to live remain in Live. History
consolidates a candidate's stages into its most recent outcome.

Start prepares the bundled service once, waits for its matching fresh observer
and credential sync, then uses the existing guarded Start request. It pauses for
saved-session recovery choices or sync/configuration failures. Cancel preparation
prevents a later Start; leaving for samples also cancels pending preparation.
No listening occurs just because the app launches or Settings is prepared. There
are no blind retries. Connection loss never appears as Listening.

Normal Settings retains basic speech/presentation configuration plus collapsed
Connections, saved-key presence, write-only replacements, Drive link and sync
status/action. It never displays saved key contents. Supported Deepgram, Sarvam
(primary/backup), AssemblyAI and Gladia credential replacements now use the same
bounded write-only settings path as existing AI provider fields. GCP service-account
file provisioning and Discord integration setup remain advanced workflows; this
change adds no new account signup or file-picker flow. Basic connection saves
submit only replacement credentials and the sync URL, preserving hidden routes,
account confirmations and budgets. Model routing and quotas remain in Developer Mode.

## Verification

- PASS:178 Python tests, including speech-credential redaction and preservation;
  70 desktop tests, including developer preference/source gating, normal vs developer
  visibility, duplicate/held/queue projection, Stop across pages, history, cancellation,
  sync waiting, recovery/failure gates and basic saves preserving advanced settings.
- PASS: JavaScript syntax/offline checks and whitespace checks.
- PASS: first separate ARM64 package inventory (28 files), rebuilt frozen backend.
- PASS: Computer Use on the packaged candidate: default normal navigation, one-click
  preparation → synthetic recognition, bilingual speech, pending John3:18 approval,
  History with truthful outcomes, Stop from Settings, Developer Mode reveal, Runtime
  controls and stopped backend closure. Normal settings were read-only while running.
- UI inspection found extra approval-wrapper spacing and an inaccessible visual
  status notice. Both were corrected in the final candidate; final verification
  and build provenance are recorded below when completed.

These are isolated synthetic tests, not a new microphone/STT or VerseVIEW output
verification. Windows physical inspection remains deferred. The original intermittent
delivery incident remains unresolved. Overall migration remains6/8 (75%); publisher
signing/notarization, production replacement and outstanding physical checks are
not implied complete by this interface milestone.

Packaged long-history check:100 explicitly labelled synthetic journal rows were
added only to the disposable QA profile. Computer Use scrolled English back to
entries033–043 while Malayalam stayed at092–100, then Jump to live returned
English to089–099. Smaller Full transcript text and independent scrolling are
visually verified. Deterministic tests establish the ease-out timing; static
screenshots establish the ending position, not animation timing.

A long-page inspection exposed the listening header scrolling offscreen. The
header now sticks to the top of the scrolling surface, keeping Stop available.
The final package repeats this check. Packaged recovery also paused at Resume /
Start new with recognition stopped, staged Resume without starting, then began
synthetic recognition only on a second explicit Start.

The pinned header was verified through Computer Use while Settings scrolled far
below its initial viewport. Native Window → Move & Resize → Left also verified a
half-width window (about735 logical pixels), then Return to Previous Size restored
the window. Basic settings and the listening header remained readable. The glass
header was changed to an opaque theme background to prevent underlying text from
showing through it. A focused regression also covers preparation after a manual
backend close while its final observer snapshot is still fresh.

## Delivered artifact and cleanup

Final runtime revision: `52082eda` (neutral “No reference yet” placeholder when
stopped). Version0.12.0; build ID `2026-10-20T22-20-42-068Z-52082eda-darwin-arm64`.
Separate app: `~/Applications/VerseView Preview/0.12.0-52082ed/VerseView Desktop Preview.app`.
Archive SHA256: `3acdb7689a669ae163713e50fc6c2cdc1a6decc5bec9281a6b0273d92af1593d`.

Built with the existing process:

```sh
python desktop-preview/scripts/build-backend.py
cd desktop-preview
npm run package -- --platform=darwin --arch=arm64 --backend="$(cat backend-build/latest.txt)"
node scripts/verify-latest.cjs
python scripts/archive-latest.py
```

The backend was rebuilt after the credential-boundary change and reused for the
subsequent renderer-only polishing. Final package inventory28 files, ad-hoc signature,
archive extraction and extracted frozen startup all passed. No dependencies or
system security/signing settings were installed or changed.

Native CI39506618364 at bda6f4bf passed Windowsx64, MacARM64 and MacIntel. It includes
the consumer workflow, pinned opaque header and70 desktop tests; the final one-line
placeholder change is covered locally and awaits its own pushed CI result. These
native builds do not substitute for Windows physical UI/microphone testing.

Computer Use confirmed the prior normal-profile bda6f4bf package, source URL and
Focus screen with listening stopped. The Mac initially locked before the final52082eda
window could be opened. After the user unlocked it, Computer Use confirmed the
exact installed52082eda package URL, normal Live navigation, the neutral “No
reference yet” result, Focus/Full transcript controls and Stopped status. The
final app is left visible on Live; recognition was not started.

All isolated QA main/backend processes exited. Disposable QA profile, synthetic
journals and dummy source were removed; no real microphone/cloud/presentation was
used in those checks. Normal preview settings match the private pre-update backup
byte-for-byte. Previous app versions remain available. The original detector's
settings SHA256 remains `e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`.
The original installed detector remains intact. Publisher signing/notarization and
production replacement remain separate steps requiring the existing approvals.

##0.12.1 — Live ordering and speech setup, October20,2026

At the user's request, normal Live now orders the reference result first, then
transcript view controls and speech panels. Saved-session recovery, approvals,
suggestions and Live speech setup follow below the speech panels. Developer Live
also keeps its runtime/status sections below the output. Full transcript retains
its existing behavior of prioritizing the transcript rather than the result card.

Primary/secondary language and provider selectors plus the second-stream enable
switch are now on Live. Normal Settings retains microphone, Bible and VerseVIEW
connection controls. Both surfaces reuse the same validated settings draft,
revision checks and stopped-only save path. The global Start/Stop control remains
at the top. Window layout in Appearance is inset17px to align with the theme grid
and note, and its label no longer wraps unnecessarily.

PASS:71 desktop tests, syntax/offline checks, package inventory/signature and
archive extraction/frozen startup. No Python runtime changed; the already tested
backend is reused. Packaged Computer Use confirmed the new ordering, language
selectors, stream disabling and successful settings save in an isolated profile
without starting recognition, and visually confirmed Appearance label alignment.
The disposable QA app/backend exited and its settings were removed afterward.
No real microphone/STT or presentation test was performed for this layout change.

Runtime revision `fcac8c15`, version0.12.1, build
`2026-10-21T01-14-28-855Z-fcac8c15-darwin-arm64` using the existing package command.
Archive SHA256 `1dd0a556ecd263243fac8c387bd0214b53cbfc2e292ca17ab76aa5599d6a95ef`.
Separate installed app: `~/Applications/VerseView Preview/0.12.1-fcac8c1/VerseView Desktop Preview.app`.
The prior normal app had no unsaved form changes and recognition was stopped;
its settings were backed up before switching versions. The new packaged app was
opened through Computer Use and its Live speech setup prepared without starting
listening. The original installed detector and prior preview versions are retained.
Overall migration progress remains6/8 (75%). Native CI for this layout revision is
separate from the previously passed consumer milestone builds.

##0.13.0 — operator controls group, October20,2026

Four consumer controls are implemented: compact Saved sessions modal, persistent
Worship, native Always on top and Emergency Stop & Save. Reference/speech stay above
the tools and emergency remains in the sticky listening header. Final packaged Mac
checks cover normal/narrow popup bounds, bilingual originals/outline, rolling
autosave, pin readback, guarded stage-only Resume and emergency cancellation/save.
Computer Use confirmed popup scrolling and Escape/focus return. See
[OPERATOR_CONTROLS_VERIFICATION.md](OPERATOR_CONTROLS_VERIFICATION.md) for source,
artifact and evidence. No new real microphone, visible VerseVIEW or Windows physical
pass is claimed. Original installed app remains intact; progress6/8,75%.
