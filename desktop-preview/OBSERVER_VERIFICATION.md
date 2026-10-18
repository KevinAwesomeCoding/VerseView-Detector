# Read-only observer verification — 2026-10-17

Historical stage-two report. See [control verification](CONTROL_VERIFICATION.md)
for version 0.3.0, optional controls, and the latest test results.

Version 0.2.0 adds a local, one-way connection from the existing Python engine to
the desktop preview. The packaged Mac app was verified against actual engine
callback/parser/delivery code behind mocked services. This is **callback replay**,
not microphone/STT transport or visible VerseVIEW verification. Windows execution
remains unverified.

## Exact artifacts and provenance

Branch `main`, base Git revision
`3a4349be57099c0c130800300b335d98f611d11a`, with the uncommitted desktop-preview
work and new observer implementation. These are dirty-source builds, not clean
builds of that commit. No commit, push, release, or installed-app replacement was
performed.

Commands, from `desktop-preview/`:

```sh
npm run package:mac
npm run package:windows
```

Mac ARM64 build:

```text
out/2026-10-18T00-00-20-862Z-3a4349be-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app
```

Windows x64 build:

```text
out/2026-10-18T00-00-23-129Z-3a4349be-win32-x64/VerseView Desktop Preview-win32-x64
out/VerseView Desktop Preview 0.2 Windows x64.zip
```

Tool versions: Electron 44.9.0, official packager 20.3.0, Lucide 1.59.0, Node
24.19.0. No new dependencies were installed in this stage. The Mac package has
verified local ad-hoc signing; Windows is unsigned. Source snapshots and build
commands are recorded in the existing provenance files. Each build also has an
executable SHA-256 file.

The Python publisher/engine are intentionally not embedded in the Electron app.
Their tested source hashes are separately recorded in the Mac build's
`verification/adapter-source.sha256`. The installed Python detector was not
rebuilt and does not yet publish the feed.

## Verified results

| Check | Result | Evidence / limit |
| --- | --- | --- |
| Actual packaged app ran | PASS | Observer and sample UI reports show `app.isPackaged: true`, the exact executable above, version 0.2.0, and matching Mac build ID. |
| Both archives contain intended adapter/frontend | PASS | Archive verification checks 14 entries, hashes, runtime manifest and allowlist; production Python engine excluded. |
| Engine callback → snapshot → desktop rendering | PASS (replay) | Real English handler, Sarvam handler, parsers and delivery code under the existing fake-controller/network-isolation harness. Banner and feed origin say callback replay. |
| Separate English/Malayalam output | PASS (replay) | Raw Malayalam stays in the secondary panel; English translation is separate. Provider/language come from explicit engine configuration. |
| Candidate outcome metadata | PASS (replay) | Original candidate ID, source, stream, language, stage, timestamp and acceptance/suppression outcome survive the boundary. No transcript/candidate association is invented from timing. |
| Changing verses and held reference | PASS (replay) | John 3:16 accepted; secondary duplicate suppressed; later John 3:17 accepted. John 3:18 manual-confirmation event is visible without being promoted to accepted output. No approval button is exposed in observer mode. |
| Raw text survives translation failure | PASS | Focused real Sarvam-handler regression asserts raw text is observed before a raised translation error; the original error still propagates and no browser command occurs. |
| Partial/final/translation identity | PASS | Partials replace only their own stream; finals remain; translations update the same raw transcript ID. |
| Lost feed and session replacement | PASS | Heartbeat expiry visibly marks the last snapshot stale. A new replay process/session clears prior John 3:17 data and shows only its new session. |
| Several processes / malformed data | PASS (unit) | Ambiguous active sources require selection. Losing the selected source does not silently choose another. Invalid schemas, future timestamps, oversized files and traversal-like selection are rejected. |
| Old process files and bounded reading | PASS (unit) | More than 32 historical process files do not block the latest active feed; only the newest 32 are read, with a bounded cache for unchanged snapshots. |
| Read-only boundary | PASS | No engine start/stop, microphone, approval or presentation API exists in the preload. Renderer sandbox, Node isolation, blocked networking and narrow trusted-sender IPC remain. |
| Sample/observer separation | PASS | Sample actions update only demo state; switching back preserves the actual observed snapshot. Live observer's Test area contains only a switch to sample mode. |
| Layout, themes and copying text | PASS | 24 observer cases and 24 sample cases: two layouts, three widths, four views. All six themes retain session data. Theme/navigation controls retain their DOM nodes during incoming events. Selected transcript text remains stable; latest data renders after selection clears. |
| Python regressions | PASS | 50 tests: the existing delivery suite, focused translation-observation regression, and publisher tests. Existing service/device isolation retained. |
| Desktop unit/syntax/whitespace | PASS | 13 desktop unit tests; JavaScript and Python compilation; `git diff --check`. |
| Visible presentation / verse text | UNVERIFIED | Last accepted command is explicitly labelled as engine evidence. The observer does not read VerseVIEW's screen or substitute sample KJV text. |
| Real microphone/STT transport | UNVERIFIED | No live microphone/provider session started in this stage. |
| Windows runtime | UNVERIFIED | Windows x64 package built and archive verified on Mac; no Windows execution. |
| Native Computer Use handoff | BLOCKED | The Mac locked again. Automated Electron-window checks completed, but updated native-window handoff awaits unlock. Previous milestone's controlled Glass comparison also remains unverified. |

The final packaged observer and sample runs report no JavaScript errors. The
sample suite also reports no unexpected console errors. Evidence is preserved
in the Mac build's `verification/` directory: `observer-ui-checks.json`,
`ui-checks.json`, archive report, callback-replay screenshot, activity screenshot,
and stale-feed screenshot. Renderer screenshots establish frontend content;
they do not prove desktop compositing.

## Implementation and operation

`observer_feed.py` is a standard-library, opt-in publisher. Engine hooks add
observation without changing delivery decisions, cooldowns, confirmations, retry
rules, controller commands or provider exceptions. Export failures cannot raise
into the engine. Disk writing happens on a daemon thread; snapshots are atomic,
bounded, and allowlisted. No network listener or upstream command channel exists.

The observer is disabled unless the updated detector is started with
`VERSEVIEW_OBSERVER=1`. This is separate from launching the Electron preview.
The normal feed directory is inside the existing user's VerseView profile on
both OSes. The viewer discovers up to 32 recent process files and reads them
only. It does not read credentials or change production settings. See
[README.md](README.md#enable-the-engine-export) for platform startup commands.

The existing installed detector remains intact. Running it alone will not
produce this new feed. A normal updated detector run retains its saved behavior,
including auto-start and presentation settings; this stage did not launch that
runtime. Real speech verification should use the resolved, approved isolated
VerseVIEW target before any presentation commands are exercised.

## Cleanup and next checks

Replay processes and temporary feed folders were removed, as was the automation
QA profile. Final artifacts, evidence, project dependencies and the normal
preview profile were retained. Superseded stage-two builds were removed; the
previous milestone's final artifacts were preserved. No production settings,
installed app, system display timeout, credentials or security preferences were
changed.

Next: unlock and review the updated preview, then verify an observer-enabled
detector with real microphone/STT on an isolated target, and run the Windows
package on Windows. A command/control bridge belongs to a later stage. The
original intermittent delivery incident remains unresolved.
