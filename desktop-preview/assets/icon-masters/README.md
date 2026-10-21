# VerseView theme icon masters

Six lossless 1254 × 1254 RGBA PNG masters, generated with the built-in image generation tool from the supplied upscaled reference (`Downloads/01-app_icon.png`), retained here as `reference-original.png`. The original root `app_icon.png`, `.icns`, and `.ico` are preserved. These are raster masters, not vector or layered originals.

Runtime exports live in `../../src/assets/icons/`: `verseview-{sage,midnight,galaxy,aurora,ember,glass}.{png,icns,ico}`. PNG exports are 1024 × 1024 with alpha. ICNS includes 16–1024px representations. ICO includes 16, 20, 24, 32, 40, 48, 64, 128, and 256px images. Re-export on macOS with `python3 desktop-preview/scripts/export-theme-icons.py` (Pillow and iconutil required). This resamples/encodes only and preserves alpha.

`theme-icon-review.png` displays all six over light and dark surfaces, plus 16/24/32/48px previews. The review sheet has opaque backgrounds for inspection; the actual icons have transparent backgrounds. Glass uses static frosted material and real alpha; it does not require live blur.

## Generation prompt set

One built-in edit call per theme, using the upscaled icon as the edit target and `transparent_background: true`. Substitute THEME and its PALETTE below into this shared prompt:

Use case: precise-object-edit. Create the THEME variant of the supplied VerseView app icon. Input is the edit target. Preserve precisely its core symbol, silhouette, relative proportions and placement: open book below, latitude-longitude globe behind, flying dove pointing right in front. Change ONLY colors and restrained material finish. PALETTE Single centered icon on genuinely transparent background, high-resolution square 1024x1024 or greater. All variants must share the reference composition, same padding (about 11%), same soft upper-left studio light, subtle shallow dimensional edges, crisp clean contours, minimal detail for readability at 24px. No text, no letters, no badge, no rounded square container, no added symbols. Keep cutout gaps in globe truly transparent. No checkerboard or black background. Preserve underlying mark, do not redesign dove/book/globe.

- **sage:** Soft sage greens #247e69, #edf1ea, moss-green book cover, pale sage pages and ivory dove; calm natural satin material.
- **midnight:** Matte charcoal #111319 and #242834 book cover, indigo #475cc9 globe and pages, pale cool ivory dove, subtle lavender edge accents.
- **galaxy:** Violet #7b4ad6, deep indigo #141026 book cover, violet pages, lavender-white dove, restrained tiny starlight details confined INSIDE the existing colored mark.
- **aurora:** Deep teal #0d1e28, #126f84 globe and book, northern blue and green #58bfb5 light gradients confined inside the mark, pale mint-white dove.
- **ember:** Warm amber #aa5a20 and gold pages, earthy brown #45301f cover, warm cream-white dove and muted bronze globe.
- **glass:** Frosted blue #5281a7 and lavender #b8a0e1, translucent frosted-glass book and globe with restrained pearlescent edges, milky semi-transparent dove. Actual alpha transparency through parts of material and zero-alpha background.


The `original` runtime exports are generated separately from the unchanged root
`app_icon.png`. The exporter centers its visible alpha bounds on a transparent
1024px canvas (800px maximum mark extent) and uses that same canvas for PNG, ICNS
and ICO. This corrects the legacy canvas's unequal padding. Generated theme
masters and their eighteen exports are unchanged.
