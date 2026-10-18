# Desktop controls verification — 2026-10-17

Historical stage-three report. See [settings verification](SETTINGS_VERIFICATION.md)
for version 0.4.0 and the latest results.

Version **0.3.0** adds an opt-in command connection to the Python detector:
start/stop, reported lifecycle status, and approve/reject for an exact held
candidate. Physical testing is deferred at the user's request. This stage did
not run a microphone/provider session or operate a real VerseVIEW instance.

## Exact artifacts and provenance

Branch `main`, base revision `3a4349be57099c0c130800300b335d98f611d11a`, plus the
uncommitted preview, observer, command adapter, GUI wiring, and regression tests.
These are dirty-source development builds. Build commands from this directory:

```sh
npm run package:mac
npm run package:windows
```

Mac ARM64 artifact actually executed:

```text
out/2026-10-18T00-13-21-181Z-3a4349be-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app
```

Windows x64 artifact (built and inspected, not executed):

```text
out/2026-10-18T00-13-39-957Z-3a4349be-win32-x64/VerseView Desktop Preview-win32-x64
out/VerseView Desktop Preview 0.3 Windows x64.zip
```

Each build has `provenance.json`, executable/archive SHA-256 files, and embedded
build information. Electron 44.9.0, official packager 20.3.0, Lucide 1.59.0,
Node 24.19.0. Mac ad-hoc test signing and deep/strict verification passed under
the prior approval. Windows is unsigned. No dependencies were installed.

The three final UI reports identify the exact Mac executable above,
`app.isPackaged: true`, version 0.3.0, and its matching build ID. They did not
execute the source Electron entry point. Archive inspection verifies the
allowlist, runtime manifest, and hashes of all 15 runtime files on both platforms,
including the command adapter, preload, reader, and frontend.

Python remains a separate backend; it is not included in these Electron
packages. Tested backend/fixture hashes are in the Mac build's
`verification/adapter-source.sha256`. Verification documentation was finalized
after packaging; packaged runtime bytes remain those checked by provenance.
The original installed detector does not acquire these controls automatically.

## Results and evidence

| Check | Result | Evidence / limitation |
| --- | --- | --- |
| Packaged Mac runtime and both package contents | PASS | Exact executable, version, build ID, manifests and source hashes verified. |
| Start/stop command round trip | PASS with mocked lifecycle | Packaged buttons → narrow IPC → atomic local inbox → Python broker → start/stop test callbacks → acknowledged status. The production GUI's device lifecycle was not started. |
| Exact candidate approval | PASS with fake browser | Real engine holds John 3:18; dashboard shows its original candidate ID. Approval returns through the existing engine gate and yields COMMAND_ACCEPTED with that ID. No physical browser/output involved. |
| Rejection and continued transcription | PASS with callback input | John 3:19 is cancelled; John 3:18 remains the last accepted command until a later real transcript callback for John 3:20 updates both speech and acceptance views. |
| Delivery guard after approval | PASS (regression) | Context-bearing confirmation preserves ID/source/stream; enabling worship mode before approval completes still prevents browser delivery. |
| Stale/replaced/duplicate commands | PASS | Both boundaries check the session; backend also checks host, age and current state. Replayed command IDs do not execute twice. Missing/answered candidates cannot be approved. Unsupported actions are rejected. |
| Start session rotation | PASS | Explicitly selected host follows only the matching acknowledged Start request on the same PID/control host. Unrelated session changes do not silently select another source. |
| Command feedback attribution | PASS | Selecting another host clears the previous host's request feedback. |
| Pending decisions | PASS | Stop, close, and session changes release waiters without approval. Command expiry does not expire or approve an already-held candidate. |
| Read-only compatibility | PASS | Observer-only backend exposes no control panel; command submission is rejected. Existing confirmation callback remains the default without control opt-in. |
| Renderer isolation / sample separation | PASS | Sandbox and context isolation remain; arbitrary networking and invalid appearance requests are blocked. Sample controls do not control the backend. |
| Layout and essential controls | PASS | 36 control theme/layout/width cases, 24 observer view/layout/width cases, and 24 sample cases. Stop remains accessible. Selected transcript text remains stable while stale/closed controls disable. |
| Observer regression | PASS (callback replay) | Raw English/Malayalam, separate translation, delivery metadata, stale feed and new-session behavior retained. |
| Unit / syntax / whitespace | PASS | 62 Python tests, 19 desktop unit tests, Python compilation, JavaScript syntax/offline CSP, and `git diff --check`. |
| Real GUI start/stop with devices | DEFERRED | Existing GUI methods are wired and inspected, but the production GUI/device lifecycle was not executed by this isolated harness. |
| Real microphone / configured STT provider | DEFERRED | All speech input in this stage enters real callbacks under mocks. |
| Visible VerseVIEW reference and text | DEFERRED | Engine command acceptance remains explicitly distinct from visible output. |
| Live semantic queue release | DEFERRED | Existing queue regressions remain; no physical semantic queue test. |
| Windows runtime / native glass comparison | UNVERIFIED | Windows archive built and checked on Mac. No Windows host or physical desktop-compositing comparison used. |

Evidence is in the Mac build's `verification/`: `controls-ui-checks.json`,
`observer-ui-checks.json`, `ui-checks.json`, archive reports, source hashes,
check summary, and screenshots of held/accepted controls, narrow layout,
observer activity/staleness, and scrolling. All three final UI suites report no
JavaScript errors; the sample suite also reports no unexpected console errors.
Screenshots establish rendered frontend content, not visible VerseVIEW output
or native desktop translucency.

## Implementation and operating boundaries

`desktop_control.py` is standard-library only and opt-in. The GUI advertises a
stopped host before engine configuration, polls its own inbox on the GUI thread,
and delegates start/stop to the existing methods. Engine confirmation has an
optional contextual callback carrying candidate ID/source/stream; the original
callback signature and behavior remain available by default. Approvals do not
bypass additional guards beyond the engine's existing manual-approval path.

The dashboard exposes only three specific preload calls: start, stop, and an
approve/reject decision. It opens no network listener and does not expose the
existing broad bot bridge. Requests expire after ten seconds and are consumed
once; there is no automatic retry. A local submission is distinguished from a
backend acknowledgement, lifecycle status, and command acceptance. Missing
acknowledgements become Outcome unknown after twelve seconds.

This is a same-user local channel, not protection against another process with
that user's filesystem access. Settings, credentials, microphone selection,
provider configuration, queue actions, and passive watcher suggestions remain
in the existing detector. See [setup instructions](README.md#optional-dashboard-controls).
Do not launch that backend until ready for its normal saved auto-start and
integration behavior during later physical testing.

## Changed files and cleanup

This stage adds `desktop_control.py`, `tests/test_desktop_control.py`,
`desktop-preview/engine-commands.cjs`, command unit/UI tests and their isolated
Python fixture. It extends `observer_feed.py`, `vv_gui.py`,
`vv_streaming_master.py`, delivery regressions, reader/preload/main/frontend,
packaging allowlists/checks, version manifests, workflow, ignore rules and docs.
Existing preview/observer changes and unrelated `.DS_Store` were preserved.

Automation closed its own app instances and test backends, removed temporary
feeds and its QA profile, and retained final artifacts/evidence. Only superseded
builds created in this stage were removed; earlier milestone artifacts remain.
No installed-app replacement, production settings edit, dependency installation,
system security/display-timeout change, commit, push, or release was performed.

Physical tests remain deferred. The original intermittent delivery incident
remains unresolved. Replacing the installed detector requires a separately
verified backend build and explicit approval; this stage does not justify a
production replacement.
