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
  69 desktop tests, including developer preference/source gating, normal vs developer
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
