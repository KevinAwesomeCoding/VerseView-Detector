# Consumer interface and Developer Mode — proposed plan

Inspected October20,2026: installed0.11.6 candidate and current renderer/settings
code. The consumer/Developer Mode cleanup is a plan only. The separately requested
Live transcript switch is implemented; see LIVE_TRANSCRIPT_VIEW.md for verification.
Overall migration progress remains6/8,75%.

## Default experience

Normal mode is the default on Mac and Windows. The Live screen should answer:
Are we listening? What was heard? Which reference was detected? Does it need my
approval? Was a presentation command accepted?

Keep these visible:

- One compact status row: Ready / Connecting / Listening / Stopped / Needs attention.
  One primary Start listening / Stop control, plus Clear output when applicable.
- English and Malayalam transcript panels when enabled, clearly separated. A
  disabled second stream does not occupy an empty panel. Interim speech remains
  visible but subordinate; timestamps can move to history/details.
- A focused reference result with a truthful status: detected, waiting for reading,
  needs approval, sent, blocked or failed. Do not equate command acceptance with
  verified VerseVIEW pixels. Explain screen verification briefly, without repeated
  warning panels or large diagnostic labels.
- Pending Approve / Dismiss actions and a short excerpt when available. Keep the
  reference, source language and uncertainty useful to the operator; move internal
  IDs, parser sources and raw stage names to Developer Mode.
- A compact recovery prompt only when needed: Resume saved session / Start new,
  with optional saved-text preview. Do not silently discard or restore context.
- Actionable failures and quota exhaustion in plain language, even with Developer
  Mode off. Technical detail can remain in Developer Mode; Stop stays accessible.

Normal navigation: Live, Outline, History, Settings. History shows useful reference
outcomes and concise reasons (for example Already sent recently), rather than the
complete internal event stream. Outline keeps note editing and explicitly opened
output/display controls. No placeholder sample output is presented as real output.

## Live transcript view switch

Keep a two-option switch directly in Live: **Focus** / **Full transcript**. Focus
retains the larger recent-speech/output layout. Full transcript uses smaller text
and independently scrollable English/Malayalam panels, loading final speech from
the beginning of the current listening session through current speech. Jump to
live resumes following new text; scrolling back keeps the reading position. View
changes do not restart listening or trigger presentation. Older sessions without
recorded history must be identified as recent-only, never labelled complete.

## Move out of the default interface

| Current UI | Proposed destination / treatment |
| --- | --- |
| Source: Live observer / sample selector | Developer Mode only; live is the normal source |
| Studio / Focus layout picker in outer chrome | Appearance settings; retain the choice without a permanent toolbar |
| Theme picker on every screen | Settings → Appearance |
| Standalone backend preview panel and lifecycle controls | Developer Mode → Runtime; normal Start manages preparation |
| Open backend settings folder | Developer Mode → Runtime |
| Observer feed panel, PID and detector-process picker | Developer Mode → Diagnostics |
| Candidate IDs, command IDs, raw stage/source codes and per-cycle counters | Developer Mode → Diagnostics |
| Full delivery activity stream | Developer Mode; normal History is a concise projection |
| Test area, sample controls and reset samples | Developer Mode → Test area |
| Source revision, build ID, platform/backdrop implementation and development footer | Developer Mode → Build information; ordinary version remains in About |
| Detailed model IDs, account confirmation checkboxes, watcher timing and request/token ceilings | Developer Mode → Cloud tuning |
| Repeated engine architecture descriptions, Local feed pills and duplicated connection notices | Remove redundant copies; use one compact normal status and relevant help |
| Empty No candidates / No reference outcome / Disabled stream blocks | Replace with one quiet empty state or show only when relevant |
| Discord bot internals and lifecycle telemetry | Developer Mode; optional integration setup belongs in Settings |

These are visibility/information hierarchy changes. Do not remove underlying
functionality, telemetry, guards or diagnostic access to achieve a cleaner screen.

## Normal Settings stays usable

Keep microphone, primary/secondary languages, enable-second-stream choice, speech
provider setup, VerseVIEW target, Bible translation and appearance accessible.
Keep a collapsed Connections section with provider connected/missing indicators,
write-only credential setup, Drive link, Sync now, last sync result and concise free
quota/error messages. Normal users must be able to set up their own machine without
editing JSON or enabling Developer Mode.

Advanced model routing and budget internals move behind Developer Mode. Preserve
the existing reviewed route selections, budgets and free-only behavior. Hiding
their controls does not change them or imply unlimited free speech transcription.

## Developer Mode behavior

- Add a clearly labelled toggle under Settings → Advanced, off by default and
  remembered per desktop profile. It reveals a Developer section for Runtime,
  Diagnostics, Test area, Cloud tuning and Build information.
- This is a presentation preference, not authentication or permission elevation.
  It cannot bypass delivery guards, quotas, account confirmations, stale-state
  checks or the stopped-engine requirement for configuration writes.
- Existing saved credentials remain hidden in both modes. Never add raw settings,
  raw HTTP exceptions or unfiltered logs to the renderer just for debugging.
- Turning it off returns a developer-only page to Live. If sample mode is selected,
  switch back to live observation and clear sample-specific presentation state;
  never send those samples into a live engine or infer actual output from them.
- Switching modes does not start/stop recognition, change providers, discard
  recovery or present anything. Keep Stop and pending approvals usable in both.

## Backend preparation behind a simple control

Normal Start listening should prepare the bundled service, wait for existing
credential sync, respect a saved-session choice and then use the existing guarded
Start action. Report progress accurately and do not claim Listening merely because
the backend launched. Missing configuration gets a Settings action; failed startup
gets a clear explanation and an explicit manual retry. No blind retries or
automatic listening on app launch. Developer Mode retains separate runtime tools.

## Implementation order and checks

1. Introduce the preference, gate sample/developer navigation and group existing
   runtime/diagnostic content. Preserve the diagnostic code paths.
2. Build the compact normal Live view, simplified History and basic/advanced
   Settings split. Connect the consumer Start flow to existing lifecycle gates.
3. Verify both modes in a separate packaged candidate with an isolated profile:
   normal launch, recovery, sync delay/failure, disconnected provider, dual/single
   streams, pending approval, duplicate/queue outcomes and Stop while changing
   screens. Technical identifiers must be absent in normal mode and available in
   Developer Mode; no actual keys may be exposed in either mode.
4. Inspect default and narrow windows, keyboard focus, scrolling and existing
   themes with Computer Use. Ensure transcript updates do not displace editing or
   selection. Run relevant regression/native build checks. Report Windows physical
   inspection as deferred if no Windows machine is available.

No production signing, installed-app replacement, new provider signup, dependency
installation or presentation/microphone test is part of planning this UI change.
