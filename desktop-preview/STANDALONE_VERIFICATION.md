# Standalone companion verification — 2026-10-17 CDT

For preview 0.6.0 and the latest native/packaged results, see
[session recovery verification](RECOVERY_VERIFICATION.md). This report preserves
the earlier companion and Smart Schedule checkpoints.

Latest checkpoint: **0.5.1 native Windows x64, Mac ARM64 and Intel Mac build,
frozen startup, package integrity and extracted-archive checks all passed** in
run `39091168118`. The local packaged schedule workflow also passed with mocks.
Remaining legacy-feature migration keeps milestone 6 in progress; real speech,
visible VerseVIEW output and graphical Windows tests are still deferred.

Preview **0.5.0** includes a frozen Python companion in the separate Mac app.
This first section records the 0.5.0 checkpoint. The 0.5.1 schedule and remote
build follow-up appears below.
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

At the 0.5.0 checkpoint, Start blocked with a named migration message if saved settings enabled
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
alone. No commit, push, release or remote CI run was performed at that checkpoint.

Next: build and smoke-check the companion on Windows, complete legacy feature
migration, then perform the deferred physical tests on both platforms. Preserve
the distinction between an accepted controller command and the reference/text
actually visible on VerseVIEW. The original intermittent incident remains
**unresolved**. Installation/replacement requires a later readiness review and
explicit user approval; `/Applications/VerseView Detector.app` remains intact.

The preview-only workflow can run manually or on the scoped
`codex/desktop-backend` branch. It has read-only repository permissions and
uploads development artifacts without publishing a release. A branch commit,
push and remote run were subsequently authorized by the user for this repository.

## 0.5.1 follow-up: branch publication and Smart Schedule

The user approved publication to their existing
`KevinAwesomeCoding/VerseView-Detector` repository. Branch
`codex/desktop-backend` now contains the migration: initial commit `c806ff4`,
schedule/CI diagnostics commit `1dc8229`, and Windows test corrections plus
packaged schedule verification in `cb8b573`. `main` was not changed, no release
was published, and the installed app remains intact. The preview workflow runs
only on this branch or by manual dispatch; documentation-only updates do not
trigger another matrix build.

Latest local Mac ARM64 artifact actually executed:

```text
/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-18T02-33-20-966Z-1dc82290-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app
```

This is preview **0.5.1**, based on `1dc8229` plus the then-uncommitted QA clock,
schedule test and version changes subsequently committed in `cb8b573`. The same
native build/smoke/package commands above were used. Source hashes identify the
exact backend bytes; the old 0.5.0 artifact and its evidence remain separate.
The local frozen smoke passed without GUI/audio, and the packaged companion
suite passed with PID **25590**, `frozen: true`, `guiImported: false`, its native
build directory hidden, and no real provider/presentation transport.

Smart Schedule shares the legacy local timetable through `service_schedule.py`:
Saturday Malayalam; Sunday English from 09:10, Malayalam from 10:40 and Hindi
from 16:40. The legacy GUI calls the shared language selector. The standalone
host resolves the schedule only on explicit Start, selects the existing
single/dual-stream policy, preserves the primary provider and delivery guards,
and leaves the saved profile unchanged. A missing service keeps saved choices.
Recognition never starts merely because the clock changes or auto-start was
saved. The host notice and configured stream metadata report the selection.

The **packaged** test used a fixed Sunday-noon clock available only in the
explicit isolated QA host. It first rejected an incompatible primary provider
and stayed stopped. With a compatible synthetic profile, it configured
Malayalam primary plus English secondary, retained profile bytes, then passed
stop, deliberate owned-child crash, explicit relaunch and shutdown checks.
Real provider behavior is still deferred. **92 Python tests** (seven new
schedule checks) and **31 Node tests** passed, with syntax and whitespace
checks. This follow-up reran the affected packaged companion suite; the earlier
120 layout checks are results for 0.5.0, not a new 0.5.1 layout sweep.

The first native Windows CI run stopped in observer tests before packaging.
Improved CI annotations in the next run captured CP1252 decoding errors when
tests read UTF-8 Malayalam/source files, plus an environment-clearing test that
removed Windows home-directory variables. These are test-harness failures;
they do not establish a production STT or presentation failure. The tests now
specify UTF-8 for those files and mock the home directory explicitly. Existing
Malayalam and source-parsing tests remain in the complete suite. Failure
annotations are preserved with the local build evidence. CI also retains the
Python test report when a job fails.

The next Windows run (`39090582267`, commit `cb8b573`) reached a Tk geometry
assertion with an unmapped one-pixel frame. Processing native window events
before measuring resolved it: run `39090809328`, commit `2db61c2`, passed all
Python regressions, native companion build and frozen startup, then failed in
the final package verifier. Native-command diagnostics then captured the exact
ASAR error: the license lookup used portable forward-slash paths, while ASAR's
directory lookup splits on the native host separator. `f8fba2e` normalizes entry
paths for the reader while retaining portable provenance keys. The license,
required-file and content-hash checks remain mandatory. A focused reproduction
with the actual ASAR library and simulated Windows path rules confirms the old
lookup fails and the normalized lookup succeeds. This was a verification-tool
defect, not evidence of missing STT data or a production presentation failure.

The corrective native matrix is
[39091168118](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39091168118),
at `f8fba2ee6f5f5ae5ead68993ad92b08821c75c5a`:

| Native target | Result at this checkpoint | Exact uploaded artifact |
| --- | --- | --- |
| Windows x64 | PASS: units, native build, frozen smoke, final runtime inventory and extracted ZIP verification | [12122313455](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39091168118/artifacts/12122313455) |
| Mac ARM64 | PASS: units, native build, frozen smoke, final runtime inventory/signing and extracted tar verification | [12122942187](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39091168118/artifacts/12122942187) |
| Mac Intel x64 | PASS: units, native build, frozen smoke, final runtime inventory/signing and extracted tar verification | [12122449374](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39091168118/artifacts/12122449374) |

GitHub-reported artifact digests (outer transfer artifacts): Windows
`sha256:9c67589f98e6fe61510e9147fa3cce7f861efb6e9ac252b50314ed51ca9e4048`;
Mac ARM64 `sha256:d339e88c00f9df7a742cd5e528df7dcfe2f11e38d6f03ca7ea9e432b3ea4f6a9`;
Mac Intel `sha256:029608b127cd64302d02a076b552c6a9fd80a01a76cec674f5033cd98782addd`.
Metadata was read through the GitHub API. These remote artifacts were verified
on their native CI runners, not downloaded and executed locally. Each contains
its exact build provenance, an inner archive/checksum, archive verification
record and CI logs. Windows GUI execution and physical tests remain deferred.

Earlier native ARM64 and Intel Mac jobs passed build/smoke/package verification.
The workflow now wraps Mac deliverables in tar (Windows in ZIP), with SHA-256
records, so native bundle metadata survives artifact transfer. This follows
[GitHub's artifact permission guidance](https://github.com/actions/upload-artifact#permission-loss).
Each archive is extracted into a separate temporary directory, rechecked for
runtime integrity and Mac signing, and its extracted frozen companion is
started in isolated no-audio mode. The local 0.5.1 Mac round trip passed;
its tar SHA-256 is
`46d2c89d81af4bd0a47e1692f6da304ad0475cecc106892f2f8b28e39d8d5bbd`.
The run completed **successfully across all three native jobs**. Remote Windows
and both Mac archive verifications passed. This checks
packaging and startup, not graphical Windows behavior or real speech. The
current dashboard runtime files and backend source hashes still match the local
packaged app tested above; later changes affect CI tools/tests/documentation.

Local QA profiles and synthetic source fixtures were cleaned up, verification
children exited, and the hidden build input was restored. The final local app,
archive, build environment and evidence remain available for reproducibility.
The already-open older preview was left alone. No production settings, installed
application, display timeout or system security setting was changed. Branch
publication was authorized; no merge to `main`, release or installation occurred.

Smart Schedule is no longer a compatibility gate. Live outline display,
watcher suggestions, Discord bot, settings sync, local-model warmup and session
restoration still need migration. Milestone 6 remains in progress at **5 of 8**;
physical tests remain deferred, installation/replacement remains pending, and
the original intermittent incident remains unresolved.
