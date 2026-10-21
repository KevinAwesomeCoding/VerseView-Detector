# Release readiness — October20,2026

## Current release policy — October 21, 2026

Current published application: 0.15.1. This policy supersedes the historical
candidate/signing requirements below. The user explicitly removed paid Apple
Developer ID/notarization and Windows publisher signing from the required scope.
They are optional distribution enhancements, not release blockers. Existing Mac
ad-hoc signing, package integrity checks and OS security protections remain in
place; no signing/security settings are removed or weakened. OS prompts remain
an informational distribution limitation rather than an unfinished feature.

Automated speech acceptance should use known audio fixtures through the actual
configured STT transport, followed by reference detection, guarded delivery and
observation of the real VerseVIEW output. Text callback replay covers downstream
logic only. The existing Windows frozen smoke tests use substituted STT/controller
services and do not establish real-provider audio recognition or visible output.
A person need not speak for each automated regression; prerecorded/synthesized
voices can cover deterministic cases and selected accents, rates and noise.
Physical microphone capture/device permissions/drivers and real display routing
remain separate, explicitly unverified hardware checks. Automated audio/visible
Windows acceptance is still to be implemented; it is not marked passed here.

Current candidate: **0.11.6**, separate desktop preview, shared Mac/Windows source.
The provider and consumer Settings changes are committed as
`1e01b24fddc65e9e000b08335f891b7470b3006e` on `codex/desktop-backend` and pushed
through the existing scoped preview workflow. This document does not authorize replacing
the original installed detector or publishing a release.

## Completed scope

- Reviewed free cloud models, role-specific routing, shared quota ledger, protected
  verse capacity and no automatic paid fallback.
- Consumer Settings for routes, write-only cloud credentials, local budget limits
  and Drive credential sync. Existing profiles and guards are preserved.
- Scoped real microphone/semantic results remain documented separately; new
  Settings behavior was exercised in an isolated packaged QA profile.
- 174 Python/53 Node checks and local Mac package/archive startup checks passed for
  the integration candidate. Native CI [run39494833854](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39494833854)
  **passed all three targets** for the exact source commit: Windows x64, Intel Mac
  x64 and Apple Silicon Mac ARM64. Tests, native frozen feature checks, package
  inventory and extracted archive/startup verification all completed successfully.

GitHub transfer artifacts (14-day retention; these digests are for the outer
GitHub artifacts, not the inner app archives):

| Target | Artifact ID | GitHub SHA256 digest |
| --- | --- | --- |
| Windows x64 |12297855857|`e0643bf09bcb584cf1405be59f9b9c66a15811952a99f915065034919fcffc30`|
| Intel Mac x64 |12296954883|`4f226dcd651ff0e8fbb17ca40eede13685faeb984c6945dbdf6cbd84614af30c`|
| Apple Silicon Mac ARM64 |12295624988|`1b96474f25723b87dd7249cfebe592f79d33232c256e644b0971f13b8d7c9eee`|

Sanitized local CI record: `build/verification/ci-39494833854.json`.

## Exact-commit Mac candidate and separate installation

Build `2026-10-20T20-46-57-364Z-1e01b24f-darwin-arm64` contains the committed
runtime source above. Only unrelated.DS_Store was untracked. Existing build scripts
were used; no dependency or system-security changes were needed. The archive is
`out/deliverables/2026-10-20T20-46-57-364Z-1e01b24f-darwin-arm64.tar.gz`, SHA256
`85c8f7182268b8bc817043197d37567fda337e52b1ed557bf19f7689aff4b34d`.
Inventory of 26 files, deep/strict ad-hoc signature, extracted archive inventory and
extracted frozen-backend startup passed.

A separate copy was installed at
`~/Applications/VerseView Preview/0.11.6-1e01b24/VerseView Desktop Preview.app`.
The copied app passed inventory and signature verification, then was opened using
Computer Use. App40964 and its own bundled backend40984 run from this installed
location, not a source script or checkout artifact. The existing private preview
profile was retained; recognition stays stopped, free routes remain enabled and
startup credential sync reports already up to date. Saved-session recovery was
not discarded. The earlier preview artifacts are retained.

Before launch, the stopped preview profile was copied privately to the sibling
`VerseView Preview Backups/20261020T154812-before-1e01b24` directory under Application
Support, with 700 directory permissions and a verified settings checksum. The
original production profile hash remains
`e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`.
The original `/Applications/VerseView Detector.app` was not replaced.

Local sanitized installation record: `test-results/release-candidate-install.json`.
This is a separately installed preview candidate, not an Apple-notarized production
release. It retains preview identity/profile separation for safe rollback.

## Skipped or awaiting acceptance

- **Apple distribution signing/notarization skipped:** read-only
  `security find-identity -v -p codesigning` returned 0 valid identities. No certificate,
  Apple account, payment, keychain or security changes were attempted. Existing
  workflow ad-hoc signatures validate local package integrity, not publisher identity
  or notarization. Do not bypass an OS warning to install it.
- **Windows physical UI/microphone acceptance deferred**, per the user. Native
  Windows build checks can run in CI; they do not replace physical acceptance.
- **Windows publisher signing skipped:** no production signing configuration is
  present in the scoped preview workflow. No certificate purchase or release was
  attempted.
- Real microphone testing of this new provider/Settings revision and a live outline
  remain unverified. Earlier speech passes are not relabelled as this revision's
  end-to-end results. Deepgram/Sarvam finite-credit dependency is still present.
- Original intermittent incident remains unresolved.

## Installation and rollback handoff

Use the verified whole Mac.app or Windows directory in a separate user-owned,
versioned location. Keep the original installed detector and previous working
preview. Stop recognition/bot and close the backend before changing executable
versions or backing up the private profile. Check build ID, stopped state, free
routes, credentials-present indicators and sync status before testing.

The preview profile is `~/Library/Application Support/VerseView Desktop Preview/`
on Mac or `%APPDATA%\\VerseView Desktop Preview\\` on Windows. Back it up privately;
it can contain keys and transcripts. Startup Drive sync is enabled only when its
saved URL is populated. It can update supported credentials, not model routes.
Rollback requires restoring the matching profile backup and opening the previous
whole package. See [installation and rollback](INSTALLATION_AND_ROLLBACK.md).

Installed-app replacement remains a final user approval step after the exact
candidate and its limitations are presented. Unavailable signing and deferred
physical tests are recorded explicitly, not treated as passed.
