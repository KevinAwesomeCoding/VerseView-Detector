# Theme icons — October 20, 2026

## Delivered assets

- `assets/icon-masters/verseview-{sage,midnight,galaxy,aurora,ember,glass}.png`: six lossless 1254px RGBA masters.
- `assets/icon-masters/reference-original.png`: untouched supplied upscaled reference. Original repository-root icon files also remain unchanged.
- `assets/icon-masters/theme-icon-review.png`: light/dark backgrounds and 16/24/32/48px visual review.
- `assets/icon-masters/README.md`: generation method, complete prompt set, export instructions.
- `src/assets/icons/verseview-{theme}.{png,icns,ico}`: eighteen runtime/native assets. PNG is 1024px; ICO contains nine sizes from 16–256px; ICNS contains standard and Retina sizes through 1024px.

The variants preserve the recognizable book/globe/dove composition, with matching framing and lighting. Image generation is not an exact vector trace; there are minor contour variations. All icons have zero-alpha backgrounds and globe cutouts. Glass has real alpha and static frosted material cues. No icon depends on window vibrancy or a live backdrop. The original source artwork is retained.

## Application changes

- `src/dashboard.js` and `src/dashboard.css`: replace the letter mark with the selected theme's static image in both sidebar and narrow navigation. Existing saved theme drives the first render and native-theme IPC.
- `theme-icons.cjs`: validated filenames, native format loading, PNG fallback, Dock updates on macOS, window updates on Windows. Electron supports PNG/JPEG and Windows ICO directly; the macOS loader reads the largest embedded PNG from the generated ICNS before passing the native image to `app.dock.setIcon`. See [Electron nativeImage formats](https://www.electronjs.org/docs/latest/api/native-image).
- `main.cjs`: apply the native icon when creating the window and handling theme changes; include success/error status in the existing appearance response.
- `scripts/package.cjs`: Sage is the packaged default; include the icon module in the package allowlist. Runtime assets are included under the existing `src` allowlist; masters stay outside the runtime package.
- `scripts/export-theme-icons.py`: repeatable lossless-format exports with Pillow and macOS iconutil.
- `tests/theme-icons.test.cjs` and `tests/theme-icons-ui.cjs`: native asset, Windows routing, theme switching and restart checks.

The native Glass policy and CSS accessibility fallbacks are unchanged. Backend, recognition and presentation behavior are unchanged.

## Checks performed

| Check | Result |
| --- | --- |
| Existing tests plus focused icon tests | 77 passed |
| JavaScript syntax and offline page checks | Passed |
| PNG/master dimensions and RGBA mode | Passed for all six |
| Transparent corners/background, alpha retained in ICNS and ICO | Passed for all six |
| ICO size inventory | All nine requested sizes present |
| Light/dark visual review and small-size previews | Inspected; mark stays recognizable, fine globe detail naturally diminishes at 16px |
| Packaged macOS UI selection | Passed for all six; both layout icons loaded and native status matched |
| Actual macOS Dock setter payload | Passed for all six; ICNS decoded artwork exactly matched the corresponding PNG export |
| Saved-theme restart in packaged macOS app | Passed for all six; correct in-app icon and successful Dock update |
| Rapid theme switching through UI controls | Passed; final in-app/native state matched Sage |
| Glass native backdrop | Reported native on macOS; other five themes reported solid |
| Accessibility reduced-transparency/high-contrast fallback | Existing policy tests passed; OS accessibility settings were not changed |
| Package default | Packaged `electron.icns` SHA-256 exactly matches the Sage ICNS; bundle metadata points to that file |
| Package signing | Local ad-hoc signing and deep/strict signature verification passed |
| Windows window-icon route/fallback | Unit checked; not executed on Windows |

The Dock setter was exercised against the real running macOS app and its decoded image compared against the intended export. An independent screenshot of the Dock could not be captured: the computer-use Dock inspection timed out, and app screenshots exclude the Dock. This is a graphical inspection limitation, not a claim of an independently observed Dock appearance.

Windows graphical testing is deferred. Changing the running window's icon does not rewrite a pinned shortcut or the executable's static icon; those use the packaged Sage default. macOS Finder and the stopped app also use the bundle's Sage default; runtime Dock customization does not modify the bundle.

Evidence: `test-results/theme-icons/{theme}.png` and `results.json` (ignored local test outputs). The test harness restores prior QA preferences and does not edit production preferences or start recognition.

## Built application

`out/2026-10-21T02-35-48-913Z-66dc11b2-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`

Includes the current verified native macOS backend from `backend-build/20261021T022837Z-darwin-arm64/backend`. This is a locally ad-hoc-signed development build, not a notarized distribution.

## Installation follow-up

Installed at the user's request on October 20, 2026:
`/Users/kevinanil/Applications/VerseView Preview/0.13.0-theme-icons/VerseView Desktop Preview.app`.

The installed 0.12.1 app was inspected with recognition stopped and no unsaved settings, then quit cleanly together with its owned backend. The previous app remains in `0.12.1-fcac8c1` for rollback. The complete preview profile was backed up privately under `/Users/kevinanil/Library/Application Support/VerseView Preview Backups/before-0.13.0-theme-icons-20261020-214300/`. Existing settings were retained in place.

Verified the package inventory (48 files and bundled backend) and deep/strict code signature, then opened the installed 0.13.0 app. Its actual window URL pointed to the new installation, Settings showed version 0.13.0 and saved Glass selection, and a screenshot confirmed the new Glass mark in the sidebar. Recognition remained stopped. `scripts/verify-package.cjs` was updated to allow the new native-icon module during package verification.
