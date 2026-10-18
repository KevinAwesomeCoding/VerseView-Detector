# Mac physical acceptance checkpoint — October 18, 2026

**Latest repeat, 15:12 CDT:** normal packaged 0.11.2 recognized all three full
English phrases. 3:16 and 3:17 PRESENT commands were accepted **9.475974 seconds
apart**; repeated 3:17 was recognized and suppressed by the exact-reference guard,
with no second command. **PASS for rapid command transition and duplicate
suppression.** The user explicitly confirms both verses appeared and the repeat
stayed unchanged (**visible reference behavior user-confirmed**). Exact visible
verse text and contemporaneous automated output capture remain unverified.
See the [latest investigation entry](../docs/DELIVERY_INVESTIGATION.md) for IDs and
timestamps. Earlier checkpoints below retain their historical results.


**Earlier user-spoken checkpoint:** normal packaged **0.11.2** now has actual real
microphone/Deepgram recognition and accepted PRESENT commands for 3:16 and 3:17,
23.564752 seconds apart. Two earlier phrases produced a chapter-only parse and a
verification hold. Follow-up inspection found Spoken Numeral Mode is off; the
shorthand chapter-only parse is documented behavior for that setting, not a
proven regression. No setting was changed. Actual visible verse output and the within-ten-seconds condition
remain unverified. Populated native Activity scrolling passed while stopped.
See the [latest investigation entry](../docs/DELIVERY_INVESTIGATION.md) for the
exact transcript/candidate/stage timeline. The earlier away-from-computer session
below is retained as historical evidence, not the latest speech result.


Progress: **[████████████░░░░] 75% — 6 of 8 milestones complete.**
This is partial milestone 7 evidence. Human speech and Windows graphical acceptance
remain open. The user is away and explicitly allowed skipping spoken cases.
The original intermittent delivery incident remains unresolved.

## Artifact and approved target

The actual normal-profile application was preview **0.11.1**, source
`af3334529cdfbb543b0083ab7949cbfa26bd204b`, build
`2026-10-18T15-13-24-202Z-af333452-darwin-arm64` under `desktop-preview/out/`.
Its executable was `VerseView Desktop Preview-darwin-arm64/VerseView Desktop
Preview.app/Contents/MacOS/VerseView Desktop Preview`, PID **59388**. Its owned
frozen companions were PIDs **59427** and **60733**. This was the packaged app,
without isolated verification mode or transcript injection, not a Python script.
Archive SHA-256: `a71b9e3c683d27b6ceacc567a5896c14b94410987bd7b25291b590eab26607af`.

Computer Use resolved **VerseVIEW 11.0.0 #2**, PID **59283**, on this Mac:
`http://127.0.0.1:50010/control.html`; Main Presentation enabled on
**Screen 1 → 1920×1080**, Stage/AUX disabled. The user confirmed current audience,
projector, broadcast and livestream isolation and approved the planned cases.
No test reference was delivered during this checkpoint.

## Real microphone and provider observations

Times below are October 18, America/Chicago (CDT). Local private logs and
sanitized observer snapshots are preserved in
`desktop-preview/test-results/physical-20261018/`; raw logs remain in the private
`verseview-physical-20261018-czzw04lv` temporary folder, never committed.

| Case | Result and last confirmed / first failed or unknown stage |
| --- | --- |
| Initial microphone open | **FAIL** at PyAudio open: `-9986 Internal PortAudio error`, 11:26:09.028, after microphone permission prompted. Controller had connected and device [2] MacBook Air Microphone was selected. No transcript or candidate. User granted permission; a fresh backend was launched. No delivery retry or guard change. |
| Fresh real microphone | **PASS for device open only:** PID 60733 selected the same hardware; microphone opened **11:45:51.972**. |
| Configured real STT connection | **PASS for connection only:** English Deepgram Nova-3 WebSocket connected **11:45:52.205**. No proof of recognized speech yet. |
| Synthetic acoustic attempt | **UNVERIFIED for speech recognition/delivery:** macOS Samantha spoke “John chapter three verse sixteen.” then “John chapter three verse seventeen.” twice through the physical speakers at **11:52:02.065**, **11:52:06.733**, **11:52:11.662**. These are generated phrases, not human speech. Zero transcript rows, candidate/attempt IDs, delivery requests or acceptances. Speaker audio reaching the microphone is unknown; do not attribute absence to a proven provider defect. No virtual input or callback injection was used. |
| Human 3:16 → 3:17 within ten seconds; duplicate; manual approval; bilingual recognition | **UNVERIFIED / skipped while user away.** No recognized input, IDs, suppression or approval evidence exists for this current packaged speech stage. |
| Live semantic queue release | **UNVERIFIED:** no recognized range or matching spoken verse. Optional model availability must also be established before attempting it. |
| Visible VerseVIEW reference and verse text | **UNVERIFIED:** zero presentation commands; control-window presence is not evidence of verse output. |

The explicit Stop was acknowledged as request
`3e7a95329a90400a9ad9aa2803f9b39c`. Deepgram 1011 warnings at 11:54:16.424 and
11:54:17.031 occurred during shutdown; controller closed at **11:54:17.158**.
Both owned backends exited and microphone/provider listening stopped. The initial
permission/open failure and later successful fresh-process connection are retained
as separate outcomes. A Cerebras startup ping returned HTTP 402/payment_required;
no billing or account changes were made. This is separate from Deepgram transport.

## Native dashboard and output checks

| Check through Computer Use | Result |
| --- | --- |
| Default **1180×880** window | **PASS for observed stopped/session/settings controls and readability.** Actual transcript/diagnostic activity under speech remains unverified. |
| Settings scrolling | **PASS:** lower microphone/provider/URL settings and Save/Reload controls reachable. |
| Native zoom **1920×971** and restore | **PASS:** editor/output controls remain usable; original 1180×880 restored. |
| Glass appearance | **PARTIAL:** app reports macOS native glass and is readable. Comparison against another app behind it remains unverified. Sage restored. |
| Actual windowed outline output | **PASS:** operator-entered “Outline display verification”, “English + മലയാളം”, “Windowed test only” visibly appeared in the actual **800×600 Live Sermon Points** child. Escape closed it. This checks rendering, not STT, AI generation, fullscreen or monitor routing. |
| Recent candidate outcomes and diagnostic scrolling during recognition | **UNVERIFIED:** this session produced zero candidates. Prior isolated QA evidence remains separate. |
| Footer after closing backend | **FAIL in 0.11.1:** top correctly said closed/stale, disabled controls, but footer still said “Bundled backend connected.” Preserved `final-stopped.jpg` and `closed-footer-before.txt`. Minimal 0.11.2 correction described below. |

## Cleanup and settings

Production `~/Library/Application Support/VerseView/settings.json` stayed byte-for-byte
unchanged in this checkpoint, SHA-256
`e1e2bc2198a328250fe8f3ca1b6b3c3f48928820750916fdc91cada8d26b9760`.
The normal preview Backend profile did not exist before this session; the existing
copy-once migration created a private copy with managed credential files. Temporary
preview-only external-integration/LLM settings and confidence changes were recorded
privately and **restored byte-for-byte** after closing the backend. No production
profile rollback was attempted; this does not resolve the historical Oct 4 cleanup gap.

The private preview profile is retained for future normal use. Temporary outline
text was in memory and cleared on backend exit. The outline child is closed,
VerseVIEW is back on VERSES, Sage and the original window size are restored.
User-granted microphone permission remains granted. Existing controller code
fetched matching official ChromeDriver 155; its cache is retained. No new manual
dependency installation, installed-app replacement, release, or change to the
requested 2-minute battery / 10-minute adapter timeouts occurred. OS security
protections were not weakened; the user-granted microphone permission is retained.

## 0.11.2 status correction

The frontend now derives its footer from feed freshness and backend session closure,
so a stale or closed managed snapshot cannot claim connection. Controls and delivery
guards are unchanged. A focused regression covers fresh, stale, disconnected,
closed and external feeds. The packaged lifecycle check now asserts the footer after
both a child crash and explicit Close, then reconnects and verifies the connected
message returns. `readiness-ui.cjs` checks setup text for the current package version,
so a version bump no longer silently skips its assertions.

The following section records new-artifact checks separately; **0.11.1 microphone
connection evidence must not be presented as a 0.11.2 speech pass**.

### Exact corrected artifact and validation

- Source **`e54b905fabe60ebfcf60f61916a15ab67079bb11`**, branch `codex/desktop-backend`.
- Build command: `node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64`.
  This invokes the existing asset preparation/packager/ad-hoc signing workflow;
  unchanged Python source hashes allow reuse of the verified native companion from
  `desktop-preview/backend-build/20261018T114111Z-darwin-arm64/backend`.
- App: `desktop-preview/out/2026-10-18T17-04-40-349Z-e54b905f-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
- Archive: `desktop-preview/out/deliverables/2026-10-18T17-04-40-349Z-e54b905f-darwin-arm64.tar.gz`.
  SHA-256 **`489317c7f3bf75255691696dd35b042b3fc9d473cf31751c8eb46bc56f541361`**.
- Provenance recorded only unrelated untracked `.DS_Store`; no uncommitted runtime
  changes were included. Packaging allowlists exclude it. Original installed app intact.
- **PASS:** 149 Python tests, 50 Node tests, JavaScript/offline checks and whitespace.
- **PASS:** updated packaged backend lifecycle suite, including crash/close/relaunch
  status and child shutdown; microphone/provider/controller substitutes are explicitly
  isolated in this suite. This is not speech or visible VerseVIEW acceptance.
- **PASS:** packaged source/inventory verification (24 runtime files), strict ad-hoc
  signature verification, archive extraction and extracted frozen no-input startup.
- **PASS:** Computer Use launched the actual new normal app, PID **62977**, whose
  executable resolves inside the exact bundle above. Its real frozen host PID **62986**
  was launched stopped and explicitly closed, without starting recognition. Both its
  accessible Live announcement and visible Settings footer report feed unavailable;
  controls are disabled. Version/build are visible in the same Settings screenshot.
  The preview remains on Live session, Sage, 1180×880, with backend closed.
- **UNVERIFIED:** real speech through this corrected artifact; the microphone/provider
  connection observations above belong specifically to 0.11.1.

Selected safe screenshots: [windowed bilingual outline](../docs/evidence/2026-10-18-desktop-physical/outline-windowed.jpg),
[0.11.1 closed view](../docs/evidence/2026-10-18-desktop-physical/closed-footer-before.jpg),
[0.11.2 visible corrected footer](../docs/evidence/2026-10-18-desktop-physical/closed-footer-after.jpg).
The original misleading Live announcement was screen-reader text; it is preserved
in `closed-footer-before.txt`. The Settings footer displays the same helper visibly.
No layout redesign was needed.

Changed implementation files are `src/dashboard.js`, `src/observer.js`, package
manifest/lock and focused Node/packaged lifecycle tests; readiness assertions now
follow the current package version. Investigation, progress and acceptance documents
record the scope and gaps. No Python delivery logic changed in this correction.

The packaged lifecycle suite's synthetic QA Backend profile was removed after its
owned children exited. Temporary source fixtures and extracted-archive directories
were cleaned by their harnesses. Preserved private raw logs/settings backup, preview
profile, separate build artifacts and the previously approved reusable build
Python/dependencies remain on disk; these are not claimed deleted.


### Final native CI

**PASS:** [run 39147884519](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39147884519)
at source `e54b905fabe60ebfcf60f61916a15ab67079bb11` completed successfully on
Windows x64, Mac ARM64 and Intel Mac. Each native job checked the Python/Node
regressions, built its frozen companion, exercised isolated feature checks and
verified the packaged/extracted archive. This establishes native build/smoke
coverage, not Windows graphical or real speech acceptance.

| CI artifact | ID | GitHub artifact SHA-256 digest |
| --- | --- | --- |
| Windows x64 | 12144595378 | `85e014fb22b917a3e970b49bf76269bdc68621658e0afa343da73c6252401f58` |
| Mac ARM64 | 12144610003 | `79887643ca10fdad6bc7f4871405fa9576cc4cbe0ff63ffd0c9b909cda5afbb1` |
| Intel Mac | 12144880408 | `ffa61923bb774d201b3c509eb446eaeede3a2c993762de738da716066650a03e` |

These are GitHub artifact digests, distinct from the locally tested archive hash.
Local API metadata is retained at `desktop-preview/build/verification/ci-39147884519.json`.

### Next acceptance session and replacement gate

When the user is present, test real spoken John 3:16 then 3:17 about four seconds
later, repeat 3:17, a contextual below-threshold candidate with exact-ID approval,
and both actual English/Malayalam streams. Capture provider text, candidate/attempt
IDs, stage events/times and the actual VerseVIEW reference/verse text. Check recent
outcome scrolling while transcription continues. Attempt semantic range release
only with working model/fetch prerequisites; retain the observed Cerebras billing
failure as a separate setup issue. Finish glass/background comparison, isolated
fullscreen monitor routing and Windows graphical/physical acceptance. Existing Mac
approval applies while its resolved target remains unchanged; resolve and approve
Windows routing before presentation commands there.

The [installation/rollback guide](INSTALLATION_AND_ROLLBACK.md) describes copying
an approved artifact alongside the retained old app, backing up its profile, and
restoring app/profile together on rollback. Do not replace the installed app yet:
physical acceptance and production identity/signing/distribution remain open.
Request explicit approval for the exact artifact/destination only after those
checks pass. No release or replacement was performed. Stop at this user-present
gate; another continuation alone does not authorize forced live testing.
