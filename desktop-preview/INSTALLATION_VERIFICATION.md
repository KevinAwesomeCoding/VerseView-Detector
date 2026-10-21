# Isolated installation and rollback verification — preview 0.11.1

## Updated scope — October 21, 2026

The user has removed paid Developer ID/notarization and Windows publisher signing
from release requirements. They are optional; the historical production-signing
requirements below are superseded. Existing Mac ad-hoc signing/integrity checks
and OS protections stay intact. Windows installer/runtime/uninstall acceptance
passed in current native CI; physical Windows capture/display acceptance remains
unverified. A future audio-fixture test can exercise real STT and visible output
without requiring a person to speak each time; text injection cannot establish
STT or microphone capture coverage.

Overall migration: **[████████████░░░░] 75% — 6 of 8 milestones complete**.
Milestone 6 is complete within its isolated scope. The portable Mac preview
lifecycle below is verified; milestone 8 remains open for the distribution and
physical acceptance gates. No operational-app replacement is authorized.

## Tested packages and provenance

Final runtime source: `af3334529cdfbb543b0083ab7949cbfa26bd204b` on
`codex/desktop-backend`. Exact app:
`desktop-preview/out/2026-10-18T15-13-24-202Z-af333452-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.

The prior package used for upgrade/rollback is preview 0.10.0, source
`a6c6146a6cb67635bd2d4dbf78d96614a95fff39`, build
`2026-10-18T11-14-23-016Z-a6c6146a-darwin-arm64`.
The initial readiness run also passed from that prior package to 0.11.0 build
`2026-10-18T15-00-34-620Z-b2555dd5-darwin-arm64`.

The 0.11.1 frontend correction reuses the approved frozen native input
`desktop-preview/backend-build/20261018T114111Z-darwin-arm64/backend`.
All backend source hashes and the input stamp match the verified 0.11.0 package;
there is no Python runtime change in this revision. Outer provenance records
the new frontend source and version. No uncommitted code was included;
unrelated `.DS_Store` remains excluded.

Build commands use the existing process and approved dependencies/signing:

```sh
node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/archive-latest.py
```

The readiness harness is `desktop-preview/tests/readiness-ui.cjs`. It requires
absolute `PREVIEW_EXECUTABLE` and `PREVIOUS_PREVIEW_EXECUTABLE` paths to packaged
versions and the existing Playwright module via `PLAYWRIGHT_MODULE`. It launches
the actual Electron executables, uses an explicit synthetic QA profile and
verification backend, and never presses recognition Start. It asserts the
running executable, `app.isPackaged`, version/build ID, frozen owned child and
stopped state. It refuses an existing QA backend profile on its initial launch.

## Verified results

| Case | Result and limits |
| --- | --- |
| Fresh migration | PASS on Mac: previous packaged app imports synthetic settings once, preserves unknown fields and copies a managed GCP file into QA/Backend. Source credentials retain their bytes; saved auto-start never starts recognition. |
| Relocation and upgrade | PASS on Mac: current complete app copied to a disposable `Applications with spaces` folder; runtime inventory and deep/strict signature pass; that exact relocated executable launches its own frozen child. Existing preview settings/credential paths survive; a changed original source is not imported again. |
| Settings after upgrade | PASS on Mac: a stopped-state dashboard save persists in the preview profile; credentials and unknown fields remain private/preserved. |
| Portable uninstall/reinstall | PASS on Mac: after all owned children exit, removing only the temporary app leaves settings intact. Recopying/relaunching the app retains changed settings and credentials. |
| Rollback | PASS on Mac: prior 0.10.0 package reads this tested newer profile; restoring the entire pre-update Backend backup byte-for-byte restores the previous translation and credential. This proves the tested versions only. Full preference-parent backup is recommended in the guide; restoration of Electron preference/cache files was not exercised. |
| Preservation and cleanup | PASS: both original packaged artifacts retain their file/link inventories. Source fixture credentials remain unchanged. All owned child PIDs exit before copying/removing files. Only the disposable copied app, fixture and QA Backend are removed. |
| UI correction | PASS in final packaged readiness run: bundled setup omits external-detector environment-variable instructions, labels the saved Bible translation as applying on Start, and updates the footer when host ownership arrives. External-detector guidance remains covered by a focused view regression. |
| Unit/static checks | PASS locally: 49 Node tests and JavaScript syntax/offline CSP checks. All final native jobs also passed the 149 Python and 49 Node tests. |
| Affected packaged regressions | PASS: readiness, core backend and sync on this exact artifact; five packaged readiness stages and 36 sync layout cases. Earlier milestone 6 evidence has eight suites/252 cases on its separately identified 0.11.0 artifact; those counts are not relabeled as this build. |
| Extracted local deliverable | PASS: extracted inventory, deep/strict signature and frozen no-input startup. |
| Windows installation/upgrade/rollback GUI; Gatekeeper, notarization, SmartScreen, public installer/signing; physical microphone/STT and presentation | UNVERIFIED / DEFERRED. |

The synthetic Google key is a file-copy fixture, not authentication evidence.
No real provider, sync endpoint, Discord or VerseVIEW request was made.

## Defect found and repaired

The first readiness pass exposed setup text intended for an external Python
detector in the bundled-host Settings view. The corrected view now explains the
owned backend and private settings, and distinguishes saved Bible translation
from an engine-configured translation. A focused view regression checks both
bundled and external modes.

The first 0.11.1 packaged rerun then reproduced a stale footer after backend
connection: only the content panel refreshed on observer events. Commit
af33345 refreshes the connection notice on those same events, before selection
preservation, without replacing settings drafts or changing engine behavior.
The final readiness harness asserts this visible message after connection.
The failed screenshot, invocation, stages and original provenance are preserved
under `verification/first-readiness-footer-failure/` in the final evidence.
Neither finding explains the original intermittent delivery incident.

## Deliverable and remaining gates

Local archive:
`desktop-preview/out/deliverables/2026-10-18T15-13-24-202Z-af333452-darwin-arm64.tar.gz`.
SHA-256: `a71b9e3c683d27b6ceacc567a5896c14b94410987bd7b25291b590eab26607af`.

Native CI [39139494109](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39139494109)
completed successfully for this exact source on Windows x64, Mac ARM64 and
Intel Mac. Each job passed 149 Python tests, 49 Node tests, native build, frozen
feature checks, package inventory and extracted-archive verification. These are
native command-line checks; no graphical Windows lifecycle is claimed. GitHub
transfer digests below are separate from the inner archive checksum:

| Target | Artifact ID | SHA-256 |
| --- | --- | --- |
| Mac ARM64 | 12140688216 | `01e200bb40e5aab46571dc696136a4c3f96f0fd2d0323b3c6031e596bd8b10af` |
| Intel Mac | 12140653809 | `3df1aa32e7bc42cea9055e06e71bb5f2b62c2b9e186c1fa214c0768b4195c712` |
| Windows x64 | 12140996944 | `20698991ac17074f3592d8d843e6c4eea65a953499f0ce9375188387fbb599ec` |

The [installation and rollback guide](INSTALLATION_AND_ROLLBACK.md) covers
separate Mac/Windows targets, whole-package extraction, profile locations,
copy-once migration, externally located credentials, saved-URL sync behavior,
private backups, manual update, portable uninstall and rollback. It does not
authorize replacing the operational detector or weakening system security.

Remaining acceptance requires real microphone/configured STT on both OSes,
simultaneous English/Malayalam attribution, spoken John 3:16 → 3:17 within ten
seconds, duplicates, exact-candidate manual approval, a clearly reproducible
live semantic queue case, isolated visible VerseVIEW reference/verse text,
physical outline/monitor routing, glass/accessibility appearance and connection
recovery. Resolve the exact audience-isolated target and obtain presentation
approval before those tests. They remain deferred at the user's request.

Production readiness also requires an approved application identity, signing,
distribution/update plan and target-specific migration/rollback procedure.
Native CI does not establish Windows graphical installation or trust prompts.
After the remaining gates pass, present the exact replacement artifact and
destination for explicit approval. The installed app, production profile, main
branch, system security and requested display timeouts remain unchanged.
