# Milestone one verification — 2026-10-17

The standalone sample dashboard is implemented and packaged for macOS ARM64
and Windows x64. The Mac package was launched and exercised. Windows execution
and a controlled comparison of external content behind Glass remain unverified.
No live speech or presentation functionality is connected in this milestone.

## Build provenance

- Repository: branch `main`, base revision
  `3a4349be57099c0c130800300b335d98f611d11a`.
- Uncommitted new preview implementation is included. This is not a clean build
  of that revision alone. Each output's `provenance.json` and embedded
  `build-info.json` record the working-tree status and hashed source snapshot.
- Electron `44.9.0`, official packager `20.3.0`, Lucide `1.59.0`, Node `24.19.0`.
  Local dependencies were installed with explicit user approval. No global
  dependencies or system security preferences were changed.
- Commands: `npm run package:mac` and `npm run package:windows`, from this folder.
  The underlying recorded commands select `darwin/arm64` and `win32/x64`.
- Mac build: `2026-10-17T23-29-08-490Z-3a4349be-darwin-arm64`.
- Windows build: `2026-10-17T23-29-10-405Z-3a4349be-win32-x64`.

Exact Mac application:

```text
out/2026-10-17T23-29-08-490Z-3a4349be-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app
```

Exact Windows application directory:

```text
out/2026-10-17T23-29-10-405Z-3a4349be-win32-x64/VerseView Desktop Preview-win32-x64
```

The complete Windows directory and its provenance are also in
`out/VerseView Desktop Preview Windows x64.zip`. Keep its EXE, DLLs, and resources
together. Each build directory has `executable.sha256`. Mac ad-hoc test signing
passes `codesign --verify --deep --strict`; no distribution certificate or
notarization is configured. Windows is an unsigned development artifact.

## Verified results

| Check | Result | Evidence / limit |
| --- | --- | --- |
| Both packages contain the intended frontend | PASS | Archive verifier checks 12 entries, byte hashes, expected runtime manifest, required assets, and package allowlist; Python engine excluded. |
| Packaged Mac executable actually ran | PASS | `app.isPackaged === true`, exact executable path in UI report; Computer Use also read the `app.asar/src/index.html` URL and matching build ID. Final foreground launch PID was 11121. |
| Default Mac window readability | PASS | Native screenshot shows separate readable English/Malayalam panels, shared verse preview, sample labels, theme and navigation controls. |
| Six themes and Studio/Focus layouts | PASS | Actual Electron-window UI checks; theme changes preserve reference/session state. |
| Bilingual sample processing | PASS | Run both generates one accepted John 3:17 sample command and suppresses the second stream's duplicate. This is simulation. |
| Manual approval and queue examples | PASS | Malayalam John 3:18 is held, then updates the preview after approval. The range example releases John 3:20 with retained stream attribution. Semantic matching is simulated. |
| Resizing, scrolling, keyboard input | PASS | 24 native-window cases: three widths (1180, 900, 640), two layouts, four views. No horizontal overflow. Settings build information is reachable. Native Computer Use confirms scrolling. |
| Title-bar scrolling defect | FIXED / PASS | Initially settings content showed through the sticky title bar. Only the dashboard surface now scrolls. Automated geometry assertion and native screenshot confirm the separation. |
| Appearance persistence and sample reset | PASS | Theme/layout persist across restart; sample session starts fresh. Reset retains appearance and in-session sample configuration. |
| Preview isolation | PASS | Sandboxed renderer, no Node integration, invalid theme IPC rejected, network fetch blocked. Preview has its own profile. No production engine or device access. |
| Native macOS Glass selection | PASS | Main process reports native `under-window` vibrancy; Glass appearance is visible in Computer Use. This alone does not prove a specific external window is visible behind it. |
| Controlled external-window blur comparison | UNVERIFIED | Browser Use rejected opening the local-file comparison page because its URL policy permits only HTTP/HTTPS. No workaround was attempted. Existing native screenshots establish the appearance, not a controlled behind-window comparison. |
| Windows native runtime/acrylic | UNVERIFIED | x64 PE executable and source archive built/verified on Mac. It was not executed on Windows. |
| Accessibility fallback selection | PASS (logic) | Seven unit tests cover material selection, Windows build boundaries, reduced-transparency/high-contrast policies, invalid input, and opaque fallback colors. Physical OS accessibility switching is unverified. |
| Mac Intel / Windows ARM64 | UNVERIFIED | Build configuration supports selecting them; no local build or execution was performed. |
| Existing delivery regressions | PASS | All 40 existing Python tests passed in the previously approved isolated Python environment; no live controller or STT services used. |
| Syntax / whitespace | PASS | Preview JavaScript checks and `git diff --check`. |
| Real microphone/STT/VerseVIEW | OUT OF SCOPE | No engine adapter in milestone one. Sample outcomes are not real speech or presentation evidence. |

The final packaged Mac UI run reported zero JavaScript and unexpected console
errors. Its report and native screenshots are preserved beneath the Mac build's
`verification/` directory; ignored `test-results/` also holds the working copies.
The screenshot from Computer Use is the native appearance evidence. Renderer
screenshots can differ from native OS compositing and should not be used to
prove desktop translucency.

## Changes and cleanup

Added `desktop-preview/` (shell, frontend adapted from the approved dashboard,
local dependency manifests, build scripts, checks, documentation), a separate
manual `.github/workflows/desktop-preview.yml`, and narrow `.gitignore` rules.
The existing production workflow, Python UI/engine, installed application,
credentials, and production settings were not edited. Unrelated `.DS_Store`
was preserved. No commit, push, release, or replacement was performed.

Removed superseded preview builds and the automation-only `QA` profile. Kept
the approved project-local dependencies, the two final builds, Windows ZIP,
and verification evidence. The preview's normal profile saves only appearance
and layout choices, separately from production. The verified Mac preview is
left open on Live session for review.

Next work: Windows runtime verification and controlled native Glass comparison,
then a read-only adapter to the existing Python transcript/delivery events.
Microphone access and presentation controls come in later milestones. These UI
changes do not explain or resolve the original intermittent delivery incident.
