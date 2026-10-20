# Live transcript view — October 20, 2026

The Live page now has Focus / Full transcript buttons. Focus preserves the larger
recent-speech/output view. Full transcript uses 14px text in independently scrollable
English/Malayalam panels, with final speech from the current listening session's
beginning through the latest entries. Jump to live follows the bottom; scrolling
back preserves reading position during updates. Changing views never controls the
engine or presents a reference. The view preference is saved per desktop profile.

A private append-only transcript journal supplies history beyond the existing
48-item observer snapshot. Writes run on the observer's background flush thread;
IPC reads bounded 512KiB pages and validates session IDs, offsets, records and file
type. Translations update the corresponding original row. Recent-only legacy
sessions are labelled unavailable rather than presented as complete history.
This cannot recover earlier speech already discarded by older builds. History
files remain local with the observer data; this change adds no cloud upload.

## Verification

- PASS: all 177 Python tests, Python checks, all 58 Node tests and offline/syntax
  checks. Focused regressions cover 120 final entries beyond the 48-row snapshot,
  new sessions, long text, translation updates, disk failure, bounded pagination,
  reloads, unsafe paths, malformed/partial records, and toggling without engine
  commands or a self-triggered empty-page request loop.
- PASS: separate macOS ARM64 packaged application 0.11.7, inventory (27 files),
  archive extraction and frozen backend startup checks.
- PASS: Computer Use in the exact packaged application showed both Live buttons,
  Full selected, Jump to live, English John 3:16 and John 3:17 from the session,
  Malayalam യോഹന്നാൻ 3:16 with translation disclosure, and accessible Stop.
  The isolated synthetic backend was stopped afterward. No microphone, cloud STT
  or real presentation was used for this feature verification.
- PASS: installed separate preview 0.11.7 switched Full transcript → Focus through
  Computer Use and restored the output card, with listening stopped.
- UNVERIFIED: long populated-panel scrolling by Computer Use. Window access
  intermittently returned noWindowsAvailable.
  Scroll-position restoration and switching logic have automated coverage; this
  is not a claim of complete visual verification. Native Windows verification of
  this revision has not run.

## Test artifact provenance

Base revision: f41c045b with the uncommitted transcript-view implementation included
and recorded by the packaging manifest. Build commands:

```sh
python desktop-preview/scripts/build-backend.py
cd desktop-preview
npm run package -- --platform=darwin --arch=arm64 --backend="$(cat backend-build/latest.txt)"
node scripts/verify-latest.cjs
python scripts/archive-latest.py
```

Build ID: `2026-10-20T21-27-14-343Z-f41c045b-darwin-arm64`.
Artifact: `desktop-preview/out/2026-10-20T21-27-14-343Z-f41c045b-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
Archive SHA256: `b27f467af4af2bffb5b40e70be3b95e42a9d32cd7ef2147275a79c18ffad4ad1`.
Packaged QA main PID45069 / bundled backend PID45111 used a separate QA profile
and dummy credentials. The production `/Applications/VerseView Detector.app`
remains unchanged. The original intermittent delivery incident remains unresolved.
Overall migration progress stays 6/8 (75%); the consumer/Developer Mode cleanup
remains proposed separately.

Separate usable preview: `~/Applications/VerseView Preview/0.11.7-transcript-view/VerseView Desktop Preview.app`.
Opened through Computer Use and left in Focus, with backend/listening stopped.
Previous0.11.6 preview is retained. A private settings backup was made before the
switch. Disposable QA profile and dummy source were removed after owned QA/backend
processes exited. Normal settings and original detector settings were preserved.
