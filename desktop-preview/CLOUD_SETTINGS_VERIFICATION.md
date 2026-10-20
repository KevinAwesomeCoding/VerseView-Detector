# Cloud Settings integration — 2026-10-20

## Delivered

Version0.11.6 adds a Cloud providers section to the packaged dashboard's Settings:
reviewed model selection per feature, free-only routing switch, per-account free
plan confirmations, write-only credential replacement fields with presence status,
lower-only request/token ceilings, shared watcher interval, and Drive download URL.
The existing credential pull and status panel is reused. Saved keys never enter
the observer feed or prefilled form. Empty replacement fields retain existing keys.
Saves use the existing private600-mode inbox, stopped-engine gate, revision check,
and main-thread settings transaction. Requests are removed after execution.

This form is shown only for the managed bundled backend. It does not change the
legacy GUI's provider widgets. It does not add microphone transcription providers,
account creation, paid fallback, automatic cloud probes or quota purchases. Daily
ceiling controls describe local limits, not guaranteed free account capacity.

## Verification

- PASS174 Python tests and53 Node tests, syntax/offline-page and whitespace checks.
  New checks cover write-only credential projection/save, preservation of other
  settings, stale/running saves, rejected unknown/paid models and higher budgets,
  invalid URLs/credential fields and exception redaction.
- PASS package inventory26files, existing ad-hoc signature verification, extracted
  archive runtime inventory and extracted frozen-backend startup.
- Computer Use inspected the **packaged0.11.6** app with an isolated QA profile and
  frozen backend36737 (`--verify-isolated`). The form scrolled to the Drive fields,
  account credentials and usage sections. Existing saved keys were not displayed.
- Through that UI, a harmless fixture Drive URL was saved, the existing pull
  control completed against the verification downloader, and a dummy Groq key was
  saved. Backend results acknowledged both settings writes. The field cleared and
  showed Configured afterward; the observer contained only the presence boolean.
  Sync applied3fixture fields, stayed stopped, and generated no transcript.
- Native numeric-field editing was attempted but not established as saved through
  Computer Use. Numeric validation and persistence are covered by backend tests;
  no claim is made about a full UI exercise of every model/budget combination.
- The two-source Computer Use screenshot/AX observations sometimes lagged actual
  backend updates. Private profile values and exact control acknowledgements were
  checked independently; stale images were not used as transition evidence.

Sanitized local results:
`test-results/cloud-settings-20261020/packaged-ui-checks.json`.
No actual microphone, presentation, Discord bot connection or cloud inference was
started for these tests. The production settings hash stayed
`e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`.

## Build provenance

Source branch `codex/desktop-backend`, HEADe039a0d2 plus uncommitted provider and
settings integration changes. The existing provider work and unrelated.DS_Store
were preserved. Exact source hashes and working-tree listing are in provenance
and the bundled backend manifest; this is not a clean-commit release.

Commands (existing build workflow):

```
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
cd desktop-preview
npm run package -- --platform=darwin --arch=arm64 --backend="$(cat backend-build/latest.txt)"
node scripts/verify-latest.cjs
/tmp/verseview-standalone-build-20261017/bin/python scripts/archive-latest.py
```

App: `out/2026-10-20T20-15-32-634Z-e039a0d2-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
Archive: `out/deliverables/2026-10-20T20-15-32-634Z-e039a0d2-darwin-arm64.tar.gz`.
SHA256: `8f7de0f4ae280537927aea7553dceb16d744bd8e4bf02ad71d38878becaec9e4`.

Windows native packaging/physical UI was not rerun for this change. Apple
distribution signing/notarization, installed-app replacement, broader live
provider tests and original intermittent-incident explanation remain outstanding.
Overall migration remains6/8 milestones,75%; this completes the scoped settings
integration, not the full project.

## Final runtime and cleanup

The QA app/backend exited and its disposable QA profile/source fixture were
removed. The earlier0.11.5 preview was closed; normal0.11.6 now runs its own frozen
backend36963 using the existing private preview profile. Its actual observer shows
configured/stopped, free-cloud mode enabled, all four recommended credential fields
present, and startup Drive sync **unchanged / already up to date**. Saved session
recovery remains available; no context was discarded. Production settings and the
original installed detector are unchanged. Existing dependencies were reused.
