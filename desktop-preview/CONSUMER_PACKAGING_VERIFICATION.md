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
- Tests use a unique disposable QA subprofile. Normal settings, saved credentials,
  selected themes and original installed applications are preserved.

## Release verification

Native Intel Mac and Windows installation verification are pending the new CI run.
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
