# Consumer packaging and theme integration — October 21, 2026

Version 0.15.0 integrates the previously local theme-icon work into the native
release source. All three supported targets use the VerseView Detector product
name. No original installed application or normal user settings were replaced.

## Local verification

- 211 Python tests, 81 Node tests, JavaScript/offline-page checks and whitespace checks passed.
- Separate Apple Silicon build: `2026-10-21T15-38-42-170Z-d39af49a-darwin-arm64`.
  Base revision d39af49; includes the uncommitted consumer packaging/theme changes
  recorded in its provenance. Command: `node desktop-preview/scripts/package-native.cjs`.
  Existing approved frozen backend was reused; backend source was unchanged.
- Packaged name, executable, window, menu and runtime manifest are VerseView Detector.
  The static bundle ICNS matches the original repository icon byte for byte.
- Native ZIP extraction yielded exactly `VerseView Detector.app`, with no visible
  provenance/version/license siblings. Required Electron license notices are
  inside Contents/Resources/licenses. Signature/inventory and extracted frozen
  backend startup checks passed without microphone or presentation activity.
- Actual packaged Electron integration passed original-icon first launch and
  restart, six theme selections, six saved-theme restarts, actual Dock setter
  image comparison and rapid changes. Screenshots/results are retained locally
  in test-results/theme-icons. Computer Use independently inspected the packaged
  window, original sidebar logo, appearance controls and Galaxy logo.
- A legacy saved Ember theme and Focus layout survived a source-to-renamed-package
  file-path change with the old preference format and no native preference cache.
- Tests use a unique disposable QA subprofile. Normal settings, saved credentials,
  selected themes and original installed applications are preserved.

## Release verification


### Published 0.15.0 beta using the local Apple Silicon build

[Download VerseView Detector 0.15.0 Beta](https://github.com/KevinAwesomeCoding/VerseView-Detector/releases/tag/desktop-beta-235-local-1).
The user approved local Apple Silicon packaging instead of waiting for hosted
ARM runner availability. All three packages use source
`dfefa3cc08881538d31942eac8ce1ea0fbdb439d`; the release tag was verified against
that exact commit. Windows and Intel CI packages were reused unchanged after
verifying their outer Actions digests, reports and inner package hashes.

Apple Silicon was freshly frozen/packaged from a clean local checkout using the
existing approved Python environment and cached Electron dependencies. No tracked
source edits or uncommitted runtime changes were included. Commands:
`python desktop-preview/scripts/build-backend.py`,
`node desktop-preview/scripts/package-native.cjs`,
`node desktop-preview/scripts/verify-latest.cjs`, and
`python desktop-preview/scripts/archive-latest.py`.
Build: `2026-10-21T17-41-55-730Z-dfefa3cc-darwin-arm64`.
ZIP SHA256: `65d77d3ed9b67012b7724f4f7594ae565a7c3fb4558a96f7cabb94969d027cd4`.
Local output directory: `build/consumer-release-dfefa3/release/` in the repository.

211 Python tests, 81 Node tests, syntax/offline checks, six frozen feature/startup
checks, native package inventory/signatures/extraction and all six packaged theme
selections/restarts passed. All three native reports/checksums passed the existing
release staging validator. A draft release received exactly three packages;
server digests were checked before publishing. All three published downloads were
then downloaded again and verified byte-for-byte. Both downloaded Mac ZIPs contain
only VerseView Detector.app; signatures, static original icons and inventories
passed after extraction. The downloaded ARM app passed frozen startup and Computer
Use confirmed its actual app.asar window/name/original sidebar icon with listening
stopped. The original installed app and normal settings remained intact. Temporary
QA profiles/test windows were removed; reproducible build and download artifacts
are retained under build/consumer-release-dfefa3. No dependency install or security
setting change occurred. No real microphone or presentation command was used.

[Machine-readable release evidence](../docs/evidence/releases/desktop-beta-235-local-1/verification.json)
records all download names, hashes, source/platform origins and validation limits.
Hosted ARM CI remains unavailable; an all-green hosted workflow is not claimed.

### Hosted CI results and capacity failure before the local release

Native Windows x64 passed in [run 39628053341](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39628053341)
for source `dfefa3cc08881538d31942eac8ce1ea0fbdb439d`. Build
`2026-10-21T15-45-22-019Z-dfefa3cc-win32-x64` passed installed runtime/frozen
startup and uninstall checks. Setup SHA256:
`e58e8759430ce34d7db25a05150882e7f49442452bd61907e2bbe63b2c3831a9`.
Intel Mac x64 also passed native package, static original icon, app-only ZIP,
strict/deep signature and extracted frozen startup verification. Build
`2026-10-21T15-52-15-684Z-dfefa3cc-darwin-x64`; ZIP SHA256:
`2e394cd632fdc6b471a0472808a18f7b6e13a300036cd9bb1167bbac599f95e8`.
Apple Silicon CI could not acquire a hosted runner during attempt 1; GitHub
explicitly reported macOS ARM capacity constraints. The job never ran application
checks, and release publication was correctly skipped. One failed-job-only retry
(attempt 2) also ended after 15 minutes without acquiring a runner (runner ID 0);
the same ARM capacity notices were recorded. Windows/Intel successes were
preserved. Hosted Apple Silicon checks never started. The user subsequently
approved the verified local native build used in the published beta above;
no further hosted retry was requested.
Windows uses the native runner's existing Inno Setup compiler, a per-user setup,
installed runtime/frozen startup checks, and uninstall verification. No new local
build dependency was installed. Publication requires all three native reports and
matching checksums, plus app-only Mac and Windows lifecycle verification.

## Limits

Mac Finder and Windows pinned shortcut icons are static original icons. Theme
changes affect sidebar and the running application's Dock/window icon. Physical
Windows UI/taskbar testing remains deferred. Apple distribution signing/notarization
and Windows publisher signing remain incomplete; existing local Mac ad-hoc signing
is preserved, and no security settings were changed. No microphone, provider,
presentation or delivery logic was changed/tested in this packaging stage. The
original intermittent delivery incident remains unresolved.
