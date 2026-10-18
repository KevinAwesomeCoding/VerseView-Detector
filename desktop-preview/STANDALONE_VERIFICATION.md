# Standalone companion verification — 2026-10-17 CDT

Preview **0.5.0** includes a frozen Python companion in the separate Mac app.
The supported core workflow no longer requires the legacy GUI or an external
Python command. Milestone 6 remains **in progress**: native Windows packaging
and legacy-feature parity are incomplete. Overall progress remains
**[██████████░░░░░░] 62.5% — 5 of 8 milestones complete**.

Physical microphone/STT and actual VerseVIEW presentation were deferred by the
user. Every engine interaction in this stage used isolated verification with
synthetic devices, callback replay, blocked HTTP and a fake controller.

## Exact artifact and build provenance

Repository branch `main`, base revision
`3a4349be57099c0c130800300b335d98f611d11a`, plus uncommitted desktop migration
work. This is a dirty-source development build; that commit alone cannot
reproduce it. The build records its working-tree listing, source hashes,
runtime inventory and dependency versions. Documentation was finalized after
packaging; the verified runtime bytes are unchanged.

Actual Mac ARM64 application executed:

```text
/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-18T02-17-35-299Z-3a4349be-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app
```

Native companion input:

```text
desktop-preview/backend-build/20261018T021715Z-darwin-arm64/backend
```

Build commands from the repository root (the approved isolated environment was
recreated because the earlier temporary environment had expired):

```sh
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/smoke-backend.py
node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64
```

The helper selects `VERSEVIEW_BUILD_HEADLESS=1` and reuses the existing
`verseview.spec` through PyInstaller; the default legacy GUI build stays
available. The outer package uses the existing Electron packager. Electron
44.9.0, official packager 20.3.0, Lucide 1.59.0 and Node 24.19.0 were retained.
The Python environment includes repository requirements and PyInstaller
6.22.3 under the earlier dependency approval. Its exact installed versions are
in the companion manifest. Only the separate artifact received approved local
ad-hoc signing; deep/strict signature verification passed.

`provenance.json`, embedded `build-info.json`, and the companion's
`backend-manifest.json` identify the build and source bytes. Final archive
verification passed for **18 dashboard runtime files** and the companion's
inventory, with `productionEngineIncluded: true`. Evidence and checksums are
preserved in this build directory's `verification/` folder.

## Results and limits

| Check | Result | Evidence / limit |
| --- | --- | --- |
| Packaged app and bundled companion | PASS | Reports identify the exact executable above, `app.isPackaged: true`, version 0.5.0 and matching build ID. The companion reported PID 23124, `frozen: true`, `guiImported: false`. |
| Independence from build source | PASS | The native companion build directory was temporarily renamed while the packaged app launched and exercised its included companion; restored afterward. No source-script backend was substituted. |
| Explicit launch / copied auto-start | PASS | Launch creates a host in Stopped state even when copied settings have auto-start enabled. Start remains a separate action. |
| Engine path and bilingual attribution | PASS with mocks | Actual engine configure/main and primary/secondary callbacks produced John 3:16 then John 3:17, with raw Malayalam separate from translation and candidate events. No microphone or provider transport was used. |
| Manual decision | PASS with mocks | Held John 3:18 was approved through the packaged UI and existing confirmation/delivery gate, retaining its candidate ID. Controller acceptance was simulated. |
| Clear output / keyboard | PASS with mocks | Button and Shift+Escape from Settings reached the existing panic action. The UI reports a request; physical output clearing remains unverified. |
| Private settings migration/save | PASS with synthetic settings | Copy-once migration retained fake credentials, unknown keys and saved auto-start; stopped-engine Bible changes persisted only to the preview profile. Source bytes were unchanged and fixture credentials were absent from the renderer. Managed GCP credential copying also passed focused unit tests. |
| Crash, explicit relaunch, shutdown | PASS | A deliberately killed owned verification child caused visible failure with no automatic restart. Explicit relaunch selected a new PID and remained stopped. Quitting during mocked recognition stopped and reaped the owned companion. |
| Profile ownership / error privacy | PASS (unit) | Exclusive profile lock rejects a second host. Unexpected start exceptions become a generic public notice with details in the private log. Secrets and arbitrary child stderr are not forwarded to the renderer. |
| Dashboard settings / earlier controls | PASS (isolated regression) | Five packaged suites passed. Settings/control fixtures still use mocked legacy GUI widgets/lifecycle, while the new companion suite uses the actual frozen host. |
| Layout, scrolling, essential controls | PASS in packaged automation | 36 settings, 36 controls, 24 observer and 24 sample size/layout/theme cases: **120** total. Scroll access, text selection, drafts, Stop and save/reload remain usable. The ready/settings screenshots were captured from the final app. Native appearance comparison remains deferred. |
| Python / desktop unit suites | PASS | **85 Python tests**, **31 Node tests**; JavaScript syntax/offline-page checks and whitespace checks passed. |
| Native Windows companion | UNVERIFIED / NOT BUILT | A native Windows runner is required. The preview workflow now describes native companion build, smoke, packaging and archive verification; it has not run remotely. Earlier Windows packages contain only the prior dashboard stage. |
| Real microphone/STT, visible verse text, live semantic queue release | DEFERRED | No spoken input or audience-facing output was used in this stage. Replay and sample queue results do not establish these outcomes. |
| Full legacy parity / installation readiness | INCOMPLETE | See gates below; the preview is not ready to replace the installed app. |

The five final reports are `backend-ui-checks.json`, `settings-ui-checks.json`,
`controls-ui-checks.json`, `observer-ui-checks.json` and `ui-checks.json` in the
artifact's `verification/` folder. All identify the same final build. They
record each test's mocking limits rather than labeling them speech tests.

## Implementation and remaining migration

`desktop_backend.py` owns an explicit headless engine lifecycle, stopped-only
settings adapter, profile lock and graceful shutdown. The dashboard owns only
its spawned child. A child shutdown timeout keeps the app open for cleanup.
It does not terminate unrelated detector processes. Private settings/logs live
under the preview's own `Backend` directory; the legacy profile is never edited.
Credential-free snapshots and narrow IPC retain the earlier session/candidate
checks. The existing delivery, duplicate, confirmation and queue guards remain
in the engine.

Start currently blocks with a named migration message if saved settings enable
live outline display, watcher suggestions, Discord bot, smart schedule,
settings sync, or local-model warmup. Their values are preserved. Session
restoration and full feature parity are still open. The headless transcript and
optional summary save path exists; actual provider summaries remain unverified.
These gaps prevent counting milestone 6 complete.

Main files for this stage: `desktop_backend.py`, `backend_verification.py`,
`verseview.spec`, `settings.py`, `vv_streaming_master.py`, `desktop_control.py`,
`desktop_settings.py`, `observer_feed.py`; dashboard backend manager, main,
preload, feed and observer integration; native build/package/integrity helpers;
focused Python/Node/packaged tests; the preview CI workflow and documentation.
The dependency versions in the Electron lockfile were retained; its app version
is now 0.5.0. Existing unrelated `.DS_Store` was preserved.

## Failures resolved during this stage

An initial Mac package contained Python framework symlinks that pointed back to
the build directory, causing strict signature verification to fail. Packaging
now relocates those links inside the copied companion, rejects escapes, refreshes
the inventory after nested signing and reseals the outer app. A focused test
deletes the source tree after copying, and the final packaged test additionally
hides the build input. Final signing, runtime inventory and launch all passed.

Initial verification harness runs also exposed a renderer-evaluation assumption
and a first-snapshot readiness race. The harness no longer uses Node globals
inside app evaluation; the host flushes initial telemetry before declaring
ready, and the test waits for actual control state. A retained failure screenshot
is historical evidence, not the final result. A separate regression prevents
unexpected start exception text from appearing in dashboard notices.

## Cleanup, preservation and next checks

All final verification app/companion processes exited. Temporary synthetic
source settings and the QA profile were removed after evidence capture. The
temporarily hidden native build directory was restored. The final native build
and approved temporary Python environment are retained for reproducibility;
PortAudio remains installed under the earlier approval. No system security
settings, display timeout preferences, installed app or production detector
settings were changed by this stage. An already-open older preview was left
alone. No commit, push, release or remote CI run was performed.

Next: build and smoke-check the companion on Windows, complete legacy feature
migration, then perform the deferred physical tests on both platforms. Preserve
the distinction between an accepted controller command and the reference/text
actually visible on VerseVIEW. The original intermittent incident remains
**unresolved**. Installation/replacement requires a later readiness review and
explicit user approval; `/Applications/VerseView Detector.app` remains intact.

The preview-only workflow can run manually or on the scoped
`codex/desktop-backend` branch. It has read-only repository permissions and
uploads development artifacts without publishing a release. A branch commit,
push and remote run require user authorization before proceeding.
