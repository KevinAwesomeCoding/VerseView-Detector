# Dashboard settings verification — 2026-10-17

Preview **0.4.0** adds non-secret speech and VerseVIEW settings to the desktop
dashboard. It uses the existing Python GUI/backend and settings store. Physical
microphone/STT and presentation tests remain deferred at the user's request.

Project progress is tracked in [the migration plan](../docs/DESKTOP_MIGRATION_PLAN.md).
The count measures implemented milestones with their scoped checks; it does not
mean the app is ready to replace the installed detector.

## Build provenance and exact artifacts

Branch `main`, base commit `3a4349be57099c0c130800300b335d98f611d11a`, with the
uncommitted desktop migration work, settings adapter, GUI/store changes and tests.
These are dirty-source development builds, not clean builds of that commit.
Commands from `desktop-preview/`:

```sh
npm run package:mac
npm run package:windows
```

Mac ARM64 artifact actually executed:

```text
out/2026-10-18T01-49-53-851Z-3a4349be-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app
```

Windows x64 artifact, built and archive-verified on Mac:

```text
out/2026-10-18T01-50-27-527Z-3a4349be-win32-x64/VerseView Desktop Preview-win32-x64
out/VerseView Desktop Preview 0.4 Windows x64.zip
```

Electron 44.9.0, official packager 20.3.0, Lucide 1.59.0, Node 24.19.0. No new
dependencies were installed. The separate Mac test artifact has verified ad-hoc
signing under the previous approval. Windows remains unsigned.

Each build records provenance, dirty working-tree state, source hashes and build
command. Executable and archive SHA-256 records are beside the artifacts. All
four packaged UI reports identify the Mac executable above, version 0.4.0,
`app.isPackaged: true`, and its matching build ID. Both archives passed allowlist,
runtime-manifest and source-byte verification for 17 runtime files, including
the settings scripts and command boundary.

Python is still a separate backend, not embedded in these Electron packages.
The tested Python source/fixture hashes are recorded separately in the Mac
build's `verification/adapter-source.sha256`. Documentation/progress reports
were finalized after packaging; verified runtime bytes are unchanged.

## Verified results

| Check | Result | Evidence / limits |
| --- | --- | --- |
| Packaged Mac app / both archives | PASS | Exact executable/build ID and all intended runtime files verified. Windows execution remains unverified. |
| Settings save round trip | PASS with synthetic devices | Packaged form → narrow IPC → session-bound local command → production settings adapter and GUI binding → temporary atomic settings file → acknowledged values. Widgets and lifecycle were mocked. |
| Supported editable fields | PASS | Microphone index, primary language/provider, dual STT, secondary language/provider, detector Bible translation and VerseVIEW URL. |
| Credentials and unrelated data | PASS | Stored credentials and unknown fields are preserved. Unrelated unsaved GUI credentials/safety options remain unsaved and intact. Neither credentials nor credential-bearing URLs enter snapshots/renderer. |
| Validation | PASS | Typed allowlist rejects extra fields, invalid microphone changes, unsupported language/provider pairs, invalid Bible settings, file URLs, embedded credentials, query parameters and bad ports. No network/device probe occurs. |
| Stopped-engine and revision checks | PASS | Renderer/main/backend checks prevent saves while running or stale. GUI binding checks stopped state again. External disk or GUI edits invalidate the revision. |
| Failure recovery | PASS | Simulated write rejection is shown as failure; production binding restores widgets and leaves the draft available. An explicit later save succeeds. Atomic replacement failure leaves original file bytes intact and cleans up temporary files. |
| Corrupt settings store | PASS (unit) | Becomes unavailable; a save cannot overwrite it with defaults. |
| Drafts, focus and conflicts | PASS | Incoming events preserve the focused URL field and draft. External settings changes preserve the draft but disable Save until Reload. |
| Device inventory / hidden selection | PASS (unit) | Unknown devices cannot be newly selected; an unchanged unavailable microphone may be retained. Hidden secondary-language/provider choices survive unrelated saves. Inventory is cached from the existing detector. |
| Thread boundary | PASS (unit) | Settings refresh/save run on the GUI thread. Confirmation-worker refresh reads only cached metadata. |
| Persistence and sample separation | PASS | Settings remain after dashboard restart; sample mode exposes no backend settings fields. This is dashboard restart, not a real device/backend restart test. |
| Settings layout / access | PASS | 36 width/layout/theme cases. Fields and save/reload controls remain accessible by scrolling. Stale/closed state disables editing even while settings text is selected. |
| Earlier milestones | PASS (isolated regression) | 36 control, 24 observer and 24 sample layout cases; approval IDs, bilingual raw/translation, stale feed, scrolling, keyboard and sandbox checks retained. |
| Unit / syntax / whitespace | PASS | 75 Python tests, 25 desktop unit tests, Python compilation, JavaScript syntax/offline CSP and `git diff --check`. |
| Real GUI/device/provider lifecycle | DEFERRED | The production GUI constructor, actual audio inventory, microphone and configured provider were not run. |
| Visible VerseVIEW reference and verse text | DEFERRED | Format validation and command acceptance do not establish connectivity, isolation or actual visible output. |
| Live semantic queue release | DEFERRED | Existing regressions remain; no live semantic test. |
| Windows runtime / native glass comparison | UNVERIFIED | Windows package built/checked on Mac. No Windows execution or physical desktop-compositing comparison. |

The four final UI suites report no JavaScript errors; the sample suite also has
no unexpected console errors. The 120 layout cases comprise 36 settings,
36 controls, 24 observer and 24 samples.

Evidence in the Mac build's `verification/` includes all four UI JSON reports,
archive reports, source hashes, a check summary, and screenshots of settings
drafts, failed saves, conflicts, narrow layout, controls, observer activity and
scrolling. These establish frontend rendering, not microphone transport or
physical VerseVIEW output.

## Implementation and scope

`desktop_settings.py` projects only an explicit public-field allowlist and
maintains opaque revision tokens. Internal comparison includes GUI state and the
settings-file revision; full settings and private hashes are never exported.
The existing GUI's indexed microphone inventory is reused, without refreshing
hardware from the dashboard. `GuiSettings` updates the existing widgets on the
GUI thread and uses the current settings file as the source for unrelated data.

`settings.save()` now writes a sibling temporary file, flushes it, then replaces
the original atomically and returns success/failure. Existing callers can ignore
the return value; the dashboard checks it. A dashboard save commits the displayed
non-secret settings, not unrelated legacy GUI drafts or stored credentials.

The new preload method is specifically `saveSettings(sessionId, revision,
changes)`. The main process validates payload shape and the selected source;
the backend rechecks host/session, request age, state, revision and values before
saving. No arbitrary filesystem API, credential editor, connection-test endpoint,
automatic retry or delivery bypass was added. Renderer networking stays blocked.

A Save submission is distinct from an acknowledged successful save. A missing
acknowledgement becomes Outcome unknown; it is not silently retried. Changes
apply when the engine next starts. The form does not start that engine.

See [settings setup](README.md#dashboard-settings). Running the updated backend
later retains its normal saved auto-start and integration behavior. It still
requires the legacy GUI; standalone backend integration is the next milestone.

## Files, cleanup and remaining work

This stage adds `desktop_settings.py`, its Python tests, the shared settings
policy/frontend scripts and Node/UI tests. It extends `settings.py`,
`desktop_control.py`, `vv_gui.py`, the reader/command/preload/main/frontend,
package version/verification, isolated fixture, workflow, ignore rules and docs.
The project roadmap records progress and completion requirements. Earlier work
and the unrelated `.DS_Store` remain preserved.

Automation closed its own app/backend instances and removed temporary feeds,
settings files and the QA profile. Final packages, evidence and existing approved
dependencies remain. No installed application, production settings, display
timeouts or system security settings were changed. No commit, push, release,
new dependency installation or installed-app replacement was performed.

Remaining milestones: standalone backend integration/packaging; physical
microphone/STT/output and recovery checks on both OSes (deferred); installation,
migration and replacement readiness. Replacement still requires explicit approval.
The original intermittent incident remains unresolved.
