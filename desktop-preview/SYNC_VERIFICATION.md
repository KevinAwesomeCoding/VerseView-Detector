# Private settings sync verification — preview 0.11.0

Overall migration: **[████████████░░░░] 75% — 6 of 8 milestones complete**.
Standalone integration and native packaging are complete within the isolated
verification scope. Physical acceptance is deferred; installation readiness is
next. The original intermittent delivery incident remains unresolved.

## Provenance

Runtime source: `b2555dd5228d08930e5f5448aa922c9429eb7699` on
`codex/desktop-backend`, committed and pushed in the original repository.
No uncommitted code was included. Unrelated `.DS_Store` was excluded.

Exact Mac app:
`desktop-preview/out/2026-10-18T15-00-34-620Z-b2555dd5-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
Native input: `desktop-preview/backend-build/20261018T114111Z-darwin-arm64/backend`.
The packaged sync report records `app.isPackaged`, that executable, build ID
and owned frozen backend. The native input was hidden during the UI test.

Existing build process, approved environment and local ad-hoc signing:

```sh
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/smoke-sync.py
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/archive-latest.py
```

Source hashes are in the outer provenance and embedded build record. Logs,
same-build UI reports, screenshots and native CI metadata are retained under
the build's `verification/` directory. No new dependencies were installed.

## Results

| Case | Result and limits |
| --- | --- |
| Regression checks | PASS: 149 Python tests, 48 Node tests, compilation, JavaScript syntax/offline CSP and whitespace checks. |
| Frozen sync | PASS with fake download transport: saved URL starts one opt-in pull; Start/bot/settings save remain blocked during it; recognition stays stopped afterward. |
| Scope and credentials | PASS: existing 12-key credential whitelist, raw service account, base64 payload and secondary credential URL; unrelated speech/presentation/unknown fields survive. Secret URLs and values stay outside the renderer and command payload. |
| Atomic commit | PASS: worker downloads/validates only; main host rechecks stopped states and storage revision before saving. Private content-addressed GCP files avoid overwriting a previous credential on settings-save failure. Focused tests cover invalid content, conflicting files, failed save and cancellation. |
| Conflict and failure | PASS: operator edits during a pull are retained; failed download does not change settings; unchanged pull skips writing. Dirty dashboard drafts survive and require Reload after external edits. No blind retry is added. |
| Shutdown | PASS: quitting discards an unfinished result, requests cancellation and waits for the owned worker; no late settings apply or orphan child. Existing synchronous transport timeout still bounds in-flight work. |
| Packaged sync UI | PASS: status, timestamp/count and reachable Pull/Close controls across 36 width/layout/theme combinations. Narrow screenshot inspected; no horizontal overflow or secret projection. |
| Same-artifact regressions | PASS: sync, bot, backend, settings, outline, suggestions, warmup and recovery; eight suites and 252 layout cases. Every report's build ID matches the exact artifact above. |
| Native CI | PASS: run 39124243081, Windows x64, Mac ARM64 and Intel Mac; unit tests, frozen startup/recovery/watcher/outline/bot/sync, package inventory and extracted-archive verification. Windows graphical execution remains unverified. |
| Local archive | PASS: extracted runtime inventory, deep/strict ad-hoc signature and frozen no-input startup. |
| Real sync endpoint/GCP authentication, Discord login, microphone/STT, visible VerseVIEW, live semantic queue, native appearance and Windows GUI | DEFERRED / UNVERIFIED. |

All sync downloads in frozen/UI checks were explicitly synthetic. No real
sync endpoint, provider, Discord or VerseVIEW instance was contacted. Unit
transport checks use a fake requests response to inspect TLS, timeout,
cancellation and size handling. These checks do not establish live-service
availability or correctness of real credentials.

## Behavior and failure evidence

The preview shares the legacy credential whitelist; it does not expand it.
Configure/remove `settings_sync_url` in the private backend JSON while the host
is closed. A saved URL opts into a launch-time pull. An explicit stopped-state
Pull button permits another attempt. Starting the host never starts recognition.
Sync excludes settings that could redirect presentation or change guards.
Existing HTTP/HTTPS requests transport and certifi verification are retained,
with a 1 MiB limit and ten-second request timeout. Raw errors remain in the
private backend log; the dashboard receives a fixed status message.

The first 87dc702 frozen check successfully updated three credential fields,
then failed a harness comparison between a canonical credential path and its
uncanonicalized temporary-profile path. Native run 39123891275 failed the same
assertion on all three platforms. Saved annotations establish that failure;
on this Mac `/var` resolves through `/private/var`. Commit b2555dd compares
resolved parent paths and still checks the credential exists. The corrected
local smoke, packaged UI and all three native jobs pass. This was a verification
harness defect, not a demonstrated application delivery failure. Original
invocation, log, snapshot and provenance are retained in
`verification/first-sync-smoke-failure/`.

Changed files cover the new `desktop_sync.py`, shared whitelist, backend store
and control adapters, narrow Electron IPC/feed/status panel, explicit QA fake
downloader, build inventory/workflow and focused Python/Node/frozen/UI tests.
The preview version is 0.11.0; README, roadmap and investigation are updated.

## Deliverables and cleanup

Local archive:
`desktop-preview/out/deliverables/2026-10-18T15-00-34-620Z-b2555dd5-darwin-arm64.tar.gz`.
SHA-256: `f74c634a7918e7fe4f2b2ef9aea27dfa4aa4ea743d272edb72ba4187bbde42eb`.

Native run [39124243081](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39124243081)
completed successfully for the runtime source above. GitHub transfer digests
are separate from the inner archive checksum:

| Target | Artifact ID | SHA-256 |
| --- | --- | --- |
| Windows x64 | 12135636799 | `5ca6181a8f27eca98224d5367964dc6b8a2dec15d8a6f0d68511490784dc65a2` |
| Mac ARM64 | 12135840473 | `61b00a6e8fd064f24ddb64006e53ebc371c98aaeb15209c4cd8a8f46c1ee8e1f` |
| Intel Mac | 12135457116 | `7cb08dea82e6d6ccfebaba99ef47bd37c67116fa06ba78c94846379a42ab9f2c` |

Remote artifacts were not downloaded or executed on this Mac. Final owned QA
processes exited; native inputs were restored. Synthetic source folders were
removed by the harnesses. The last QA profile was checked for fake credentials
and exited engine PIDs, then removed. Artifacts/build inputs and the approved
environment remain for reproducibility. The installed app, production profile,
main branch, system security and requested display timeouts remain unchanged.
Replacement requires explicit approval after the remaining acceptance work.
