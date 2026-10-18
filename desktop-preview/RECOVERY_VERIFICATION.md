# Session recovery verification — 2026-10-17 CDT

Preview **0.6.0** adds recovery to the owned standalone companion. Overall
progress remains **[██████████░░░░░░] 62.5% — 5 of 8 milestones complete**;
milestone 6 still requires local-model warmup, watcher suggestions, live outline,
Discord bot controls and settings sync. Physical checks remain deferred.

## Build provenance

Existing repository `KevinAwesomeCoding/VerseView-Detector`, branch
`codex/desktop-backend`. Implementation commit `6b5c30c`; canonical engine-context
fix and native recovery regression commit
`6dc51858eaf90f6d9d209224e22a371f0d64bc2d`. The tested runtime is the latter
revision. Its source was committed before building; unrelated untracked
`.DS_Store` remained excluded. Final documentation follows packaging.

Exact Mac ARM64 app executed:

```text
/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-18T03-22-21-039Z-6dc51858-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app
```

Native build input:

```text
desktop-preview/backend-build/20261018T032145Z-darwin-arm64/backend
```

Commands from the repository root, using the previously approved environment:

```sh
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/smoke-recovery.py
node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64
```

The native helper reuses `verseview.spec` with its headless option. Versions
remain Electron 44.9.0, official packager 20.3.0, Lucide 1.59.0 and
PyInstaller 6.22.3; no new local dependencies were installed. The separate app
received approved ad-hoc signing, with deep/strict verification. Provenance,
source hashes, runtime inventories and dependency versions identify the exact
contents. The core companion report records PID **29178**, `frozen: true` and
`guiImported: false`; the recovery suite additionally hid the build input across
its relaunches. Test reports and screenshots are in the build's `verification/` folder.

## Verified results

| Case | Result | Evidence / limits |
| --- | --- | --- |
| Packaged app / frozen companion | PASS | Six reports identify the exact packaged 0.6.0 executable/build ID. The native build directory was hidden during recovery and core companion checks; no source backend was substituted. |
| Periodic checkpoint then forced termination | PASS with mocks | The actual frozen engine accepted synthetic John 3:16/17 callbacks, held John 3:18, and wrote its real 15-second autosave. Deliberately killing only that QA child left the checkpoint available on relaunch. |
| Pending work excluded | PASS | The unapproved reference, decision state, queues, commands, settings, provider logs and credential fields are absent from the saved projection. The next host has no pending candidates or accepted events. |
| Bilingual saved content | PASS | Both full engine context buffers survive; recent raw Malayalam preview and language attribution remain separate. The UI labels historical speech versus possibly translated engine context. Only bounded previews enter the renderer. |
| Explicit Restore | PASS | Before a decision, Start is unavailable. Restore stages content but leaves recognition stopped, live transcripts empty, and delivery events empty. Closing before Start preserves the file and asks again on relaunch. |
| Configure/restore/start order | PASS | Focused regression verifies configure → engine restore → worker launch. Actual engine restore retains secondary context and opens the existing system quarantine without browser/Discord presentation. |
| Resumed context / clean Stop | PASS with mocks | Explicit Start used the prepared context; a subsequent Stop checkpoint retained a unique recovered marker and the secondary buffer. Checkpointing precedes the optional summary path; real summary providers were not exercised. |
| Discard / corrupt data | PASS | Discard deletes only the private checkpoint and leaves recognition stopped. Invalid content is retained until a decision, cannot be restored, blocks Start, and never appears in renderer errors. |
| Stale decisions / selection | PASS | External checkpoint edits invalidate the displayed revision. An old IPC decision is rejected; old buttons disable while selected preview text remains intact. |
| Write failure / bounds / privacy | PASS (unit) | Atomic replacement failure retains original bytes and removes temporary files. Typed limits reject malformed context and oversized buffers. POSIX checkpoint mode is 0600; a symlink is never restored and explicit discard leaves its target intact. |
| Layout and scrolling | PASS in packaged automation | 36 recovery width/layout/theme cases, 36 settings, 36 controls, 24 observer and 24 sample cases: **156 total**. Expanded recovery details persist through feed updates; decision controls remain reachable. |
| Regressions | PASS | **105 Python tests**, **33 Node tests**, six packaged Mac suites, JavaScript syntax/offline-page checks and whitespace checks. |
| Native CI | PASS on Windows x64, Mac ARM64 and Intel Mac | Current run includes a frozen recovery regression using a fake controller, callback replay, deliberate child termination and explicit restore on each native host. |
| Microphone/STT, actual VerseVIEW reference/text, semantic queue release | DEFERRED | No spoken input, configured provider transport or real presentation output was used. No safety guard or live presentation retry was bypassed. |
| Windows GUI and native appearance | UNVERIFIED | Native CI runs the frozen host and verifies extracted packages; it does not establish graphical Windows behavior. |

## Recovery contract and failure found

The fixed file is `Backend/Recovery/session.json` inside the preview profile.
Atomic UTF-8 writes use a unique temporary file, flush/fsync and replacement.
Idle launch never overwrites unresolved content. Saved data is a typed allowlist
bounded to 8 MiB, with up to 500,000 characters per engine buffer and 4,096
history/citation entries. The preview exposes at most 2,000 characters per
stream and ten recent references. Oversized/malformed content is rejected;
the last good checkpoint is retained. A crash can lose content since the last
15-second checkpoint; this is not zero-loss persistence.

Restore applies no saved settings and does not resume old pending approvals,
range queues, presentation commands, raw provider logs or Discord messages.
Context is applied after configure because configure resets anchors, quarantine
and the secondary buffer. The existing engine quarantine then requires new live
reference evidence before restored context can steer presentation. Historical
preview text is not injected as live STT or an accepted command. A later explicit
Start can present newly received references through the normal guards.

The first packaged test failed before its crash phase: engine callbacks and the
held manual candidate were confirmed, but the recovery validator rejected the
engine's digit-string chapter/verse context. No checkpoint was written. Logs and
the screenshot were preserved under the final build's
`verification/superseded-first-failure/`. The failed local app was then removed. The fix
accepts canonical digit strings, adapts numeric legacy context to that format,
and still rejects malformed values/booleans. A focused unit regression and a new
native frozen-engine CI smoke exercise the actual autosave/restore boundary.
The rebuilt packaged test passed all affected cases. This new recovery defect
does not explain the original intermittent delivery incident.

## Native CI and remaining limits

The authorized preview branch was pushed within the existing repository;
`main` and production release publishing were not changed. Current native run:
[39093309837](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39093309837)
at `6dc51858eaf90f6d9d209224e22a371f0d64bc2d`. **The run completed successfully.**
Windows x64, Mac ARM64 and Intel Mac all
passed units, native build, no-input startup, frozen crash/recovery smoke,
runtime inventory and extracted-archive verification. CI smoke uses synthetic credentials, no microphone or global
hotkey capture, mocked STT/browser/integrations and blocked live HTTP. The
normal app's microphone, panic key, presentation and provider behavior is unchanged.

Exact uploaded development artifacts:

| Native target | GitHub artifact | GitHub-reported outer artifact SHA-256 |
| --- | --- | --- |
| Windows x64 | [12123632275](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39093309837/artifacts/12123632275) | `ea11c148f1167bbb9e387888ec92ab3c00187233662a2cbc4dede75bad843cd6` |
| Mac ARM64 | [12122669964](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39093309837/artifacts/12122669964) | `a22045fbd6f5f65ca6d9bdc5304d896902d31e39889d45bf99395843aaabda0d` |
| Mac Intel | [12123458239](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39093309837/artifacts/12123458239) | `6600cf2c62fe015550c2f325bce06f542a3344d8c05d9ba9fcd7913c0ff02f8c` |

Metadata/digests were read from GitHub; these remote artifacts were verified by
their native runners, not downloaded and executed locally. Their provenance,
inner archive/checksum, extracted-runtime check and CI logs identify contents.
The separate local Mac tar was also extracted and verified, including signature
and frozen startup. Its SHA-256 is
`e85b3ed71fefcce8a79024348c3b0dfe5c0c6d9b800aff3bc9670eaca9b5a34c`.

Legacy GUI checkpoint files are not automatically imported, modified or deleted.
This step recovers content created by the new owned companion; full legacy
feature migration is still incomplete. Cloud summaries, real microphone/STT,
physical output/recovery, live semantic queues and graphical Windows execution
remain deferred. The original intermittent incident remains unresolved.

## Files and cleanup

Main changes: `desktop_recovery.py`; companion checkpoint lifecycle; secondary
snapshot/restore field in the existing engine; session/revision-bound recovery
commands and feed decoding; narrow preload/IPC; historical preview and decision
UI; focused unit and packaged regressions; native recovery smoke/workflow;
version 0.6.0 manifests and documentation. No new dependency was required.

Verification processes and synthetic source fixtures were closed/removed. The
temporarily hidden build input was restored. The final QA profile was removed
after evidence capture; the final app, native build and approved environment
remain for reproducibility. The already-open older preview is left alone. The
installed `/Applications/VerseView Detector.app`, production settings, display
timeout preferences and system security settings remain unchanged. No merge,
release or installed-app replacement was performed.
