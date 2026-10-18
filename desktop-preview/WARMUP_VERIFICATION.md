# Local-model warmup verification — preview 0.7.0

Overall migration: **[██████████░░░░░░] 62.5% — 5 of 8 milestones complete**.
Warmup is a substep of milestone 6 (standalone backend integration and
packaging), not a separate milestone. Watcher suggestions, live outline,
Discord bot controls and settings sync still require migration. Physical tests
remain deferred; the original intermittent delivery incident remains unresolved.

## Provenance

Runtime source: `6242886cd2033ea074e1fdf5dc2c900019cf0fee`, pushed on
`codex/desktop-backend` in the existing repository. No uncommitted code was
included; unrelated untracked `.DS_Store` remains excluded.

Exact local app:
`desktop-preview/out/2026-10-18T03-45-45-542Z-6242886c-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
Native input: `desktop-preview/backend-build/20261018T034521Z-darwin-arm64/backend`.
Reports identify this executable, version 0.7.0, packaged true and the matching
build/source ID. The native input was hidden during warmup and core companion
checks; the bundled frozen backend executed.

Commands reuse the approved temporary environment and existing spec:

```sh
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/smoke-recovery.py
node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64
```

The separate app uses the existing approved ad-hoc signing process. No new
dependencies, security changes, release or installed-app replacement occurred.
Provenance/inventories, reports and screenshots are beside the app in the
build's `verification/` directory. Local extracted-archive verification and its
checksum are recorded separately beside the deliverable.

## Verified findings

| Check | Result and limits |
| --- | --- |
| Regressions | PASS: 109 Python tests, 34 Node tests, JavaScript syntax/offline-page and whitespace checks. |
| Warmup and delivery coexist | PASS with mocks: actual frozen configure/main/callback/delivery accepted synthetic John 3:16/17 while slow mocked model completions ran. A manual decision remained usable. No microphone, actual STT or model endpoint was contacted. |
| Role request shape | PASS: captured configured clients use each role's production temperature/token/context parameters. Provider fallback/skip policy and delivery guards are unchanged. |
| Failure isolation / privacy | PASS: a deliberately failing summary warmup displays a fixed notice; verse warmup completes and recognition continues. Models, endpoint/auth values and raw exceptions are excluded from public status and renderer. Private logs can retain details. |
| Stop and quick Start | PASS: Stop prevents later roles/results. Quick Start skips warmup while an old synchronous request finishes; no overlapping worker is created and old results cannot update the new session. |
| Later Start / opt-out | PASS: newly configured roles, successful completion and disabled states work in the packaged app. Idle host launch never starts recognition or warmup. |
| Layout | PASS in packaged automation: 36 warmup size/layout/theme cases retain readable status, scrolling and usable Stop. The 640-logical-pixel screenshot was inspected. |
| Core / recovery | PASS with mocks: same-build core companion and recovery suites cover bilingual delivery, approval, settings, panic, schedule, child failure/relaunch, checkpoint/crash/restore and 36 recovery layout cases. Three packaged suites, 72 layout cases total. |
| Native CI | PASS: Windows x64, Mac ARM64 and Intel Mac units/build/frozen warmup-recovery smoke/package/extracted-archive verification. Graphical Windows behavior remains unverified. |
| Real models, physical microphone/STT, visible VerseVIEW, live semantic queue | DEFERRED. No physical or live-provider claim is made. |

The host owns one daemon warmup worker and captures its configured clients.
Later configuration cannot redirect remaining calls. Stop is checked between
roles and before publishing results. An already-running synchronous request
cannot be forcibly cancelled; its existing configured transport timeout still
applies and it may finish after recognition stops. Recognition does not wait
for warmup. There is no automatic warmup retry or fallback-policy change, and
warmup success is not a delivery result. Configured remote local-LLM servers
remain network requests in normal use; QA mocked them.

## Native development artifacts

Run [39094733176](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39094733176)
completed successfully at the runtime revision above.

| Target | Artifact ID | GitHub outer artifact SHA-256 |
| --- | --- | --- |
| Windows x64 | 12123628208 | `5359668b30dc817af0e67c7d4c69c4ae458242d7d85345ab8fa940dc28110a6d` |
| Mac ARM64 | 12124162727 | `6e0ec2f883293f474b2e18d3a3615fd6b6b4100b743530b9665eeec0d41dee07` |
| Intel Mac | 12124321844 | `2d53cf6755c87123aee6d57a48909817361d6e2b1df8114b2bca4fa3e274f94f` |

Metadata was read from GitHub; native runners verified their artifacts. Remote
packages were not downloaded/executed on this Mac.

## Cleanup and next deliverable

Test-owned apps/children exited; hidden native inputs were restored. Synthetic
source fixtures were removed; the disposable QA backend profile is removed
after evidence capture. The final native build, separate app and approved
environment remain for reproducibility. The installed detector, production
settings, display timeouts and security settings remain unchanged.

Next within milestone 6: watcher suggestions, preserving the existing delivery
path and distinguishing suggestions from command acceptance. Full legacy
feature parity and milestones 7/8 remain incomplete.
