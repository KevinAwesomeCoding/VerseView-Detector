# Release readiness — October20,2026

Current candidate: **0.11.6**, separate desktop preview, shared Mac/Windows source.
The provider and consumer Settings changes are being committed and built through
the existing scoped preview workflow. This document does not authorize replacing
the original installed detector or publishing a release.

## Completed scope

- Reviewed free cloud models, role-specific routing, shared quota ledger, protected
  verse capacity and no automatic paid fallback.
- Consumer Settings for routes, write-only cloud credentials, local budget limits
  and Drive credential sync. Existing profiles and guards are preserved.
- Scoped real microphone/semantic results remain documented separately; new
  Settings behavior was exercised in an isolated packaged QA profile.
-174 Python/53 Node checks and local Mac package/archive startup checks passed for
  the integration candidate. Exact-commit native CI results will be recorded after
  the branch push.

## Skipped or awaiting acceptance

- **Apple distribution signing/notarization skipped:** read-only
  `security find-identity -v -p codesigning` returned0valid identities. No certificate,
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
