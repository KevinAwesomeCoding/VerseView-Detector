# Groups 6–7: Connections and Developer settings

October 22, 2026 (Chicago). Items 21–28 in the consumer parity plan.
**28/32 packages complete (87.5%)**. Actual hardware/provider certification is
separate from implementation acceptance.

## Separate application tested

Version 0.15.7, branch `main`, base `62c990b213cbf997d61745670073a016937ca22d`
plus uncommitted Groups 1–7 changes. Existing edits and `.DS_Store` are retained.

- App: `/Users/kevinanil/VerseView-Detector/desktop-preview/out/2026-10-22T05-50-40-417Z-62c990b2-darwin-arm64/VerseView Detector-darwin-arm64/VerseView Detector.app`.
- Companion: `desktop-preview/backend-build/20261022T055008Z-darwin-arm64/backend`.
- Existing build scripts: `python desktop-preview/scripts/build-backend.py`,
  `node desktop-preview/scripts/package-native.cjs`, and
  `node desktop-preview/scripts/verify-latest.cjs`.
- Approved temporary build environment reused; no new dependencies, security
  changes, installed-app replacement, commit, push or release publication.
- `provenance.json` alongside the app records the dirty working tree, dependencies,
  commands and source hashes. Package verification checks 62 shipped runtime files
  and the frozen companion. The source script is not the launched application.
- `test-results/connections/results.json` records `app.isPackaged=true`, the exact
  executable above, and its owned frozen companion PID. No legacy GUI imported.

## Implemented behavior

21. Google service-account JSON is chosen with a native file picker, validated by
    the existing validator, and copied into hash-addressed private managed storage.
    The public feed shows presence only. Settings files use a versioned, typed
    import/export format. Default exports omit keys. Explicit credential scope
    includes supported keys and managed Google JSON; changing scope requires a new
    prepared export. Native transfer rechecks ownership/revision after the dialog,
    bounds file size and rejects symlinks. Imports preserve unrelated fields and
    sessions, use the existing atomic settings/credential transaction and apply on
    next Start. Failed save removes a newly created credential and retains settings.
    Empty imported key fields retain existing keys. Existing approved Drive sync
    and its conflict behavior remain intact; its exposure policy is unchanged.
22. ATEM enable/IP/duration setup is in Settings; discovery and manual controls are
    in Connection tools and Live integrations. A fresh, one-use review binds the
    saved IP and settings revision, names Keyer 1 / Mix Effect 1, expires after
    30 seconds and requires explicit isolation approval. A single bounded request
    is used; acceptance is labeled as a request, never proof of keyer or pixels.
    Listening must be stopped. Real ATEM/network/output tests remain unverified.
23. Local text-model enable/server, per-role route/model selection, startup warm
    preference and skip/cloud fallback are exposed normally. Fallback credit use
    is explained. Local Whisper speech-server setup is separate. Token/header
    contents stay write-only; presence is visible. Custom overrides, headers,
    timeouts and keep-alive values are in Developer Mode. Effective targets reuse
    production model precedence and endpoint normalization, including old bare
    host/port profiles. No model is downloaded. Free-only cloud precedence remains.
24. Explicit Test/Warm uses a captured saved endpoint/model/role/auth and the
    existing engine functions. Warm uses production role request settings. Progress,
    cancellation, success/failure and exact selected target are visible. Cancellation
    ignores late output while retaining busy guards until I/O ends. ATEM commands
    cannot be cancelled once potentially sent. Start/save/import/notes/reset cannot
    overlap incompatible work. Stop/Emergency remain reachable. Existing owned
    Discord lifecycle controls are accessible on Live; setup stays in Settings.
25. Developer fields expose sample rate, chunk size, cooldown, duplicate window,
    silence timeout, AssemblyAI turn cutoff and Google interim flush with units,
    typed bounds, provider applicability and saved-value readback. There is no
    separate legacy debounce field: the existing duplicate window is retained.
26. Developer Mode retains reviewed cloud tuning, watcher batching/windows/thresholds/
    cooldown, custom local configuration, outline prompt and AI fallback enable.
    Normal UI still shows useful errors. Candidate IDs and structured outcomes are
    in Diagnostics; additional connection credentials never enter the public feed.
27. All 79 historical fields have a current disposition in
    `evidence/consumer-settings-audit.csv`. It is checked against the original
    inventory. Legacy startup, screen index, panic key and bridge host/port have
    deliberate documented replacements; arbitrary free-cloud internals remain
    preserved rather than becoming an unrestricted editor. Unknown fields survive.
28. About shows the actual app version and a fixed trusted GitHub Releases action.
    It explicitly describes manual download/install. No fake updater or Python
    self-replacement path was added. Paid signing/notarization is not required by
    this implementation and was not attempted.

## Evidence and limitations

- 257 Python and 99 Node tests pass in the final consolidation. New checks cover
  typed options/headers, legacy endpoint migration, private failure replies,
  in-flight cancellation, stale/running guards, exact ATEM review, secret scope,
  atomic import failure/rollback, Gladia and other supported key import, full
  inventory coverage and private command/decoder boundaries.
- A loopback-only HTTP fixture exercised the real existing engine Test/Warm request
  code with captured model and auth headers. This proves transport wiring against
  a synthetic server; it does not establish a real installed model's performance.
- Packaged `connections-ui.cjs` PASS: settings, private replacement presence,
  selected-role Test/Warm, Cancel, Google managed import, native transfer IPC,
  default/scoped exports, scope revocation, settings round-trip, ATEM review gates,
  Developer ranges/custom models, unsaved-draft external conflict, Reload, fixed
  releases action and restart persistence. No renderer errors. Native chooser
  responses were automated test substitutes; Computer Use of those dialogs is
  still unverified in this group because the Mac was locked.
- 36 settings size/layout/theme combinations PASS (1180/900/660, Studio/Focus,
  six themes), with emergency controls reachable. This is automated UI geometry,
  not a claim that every native translucent backdrop was visually inspected.
- Frozen `smoke-connections.py` PASS; added to the existing three-platform CI
  workflow. Only Apple Silicon was executed locally. New Windows/Intel native
  results must not be inferred from the workflow's presence.
- Initial QA runs exposed a legacy endpoint normalization mismatch (fixed), a
  connection-panel child-position change that closed disclosures during progress
  (fixed with a stable job container), and too-short synthetic busy timing for
  reliable feed observation (QA delay only extended to 1.5s). An older timeout
  could clear a newer pending UI request; it now checks request identity.
- All packaged connections/ATEM checks used an explicitly isolated QA profile.
  Microphone/STT, provider keys, real local inference, real ATEM and visible
  VerseVIEW were not tested here. The original intermittent incident remains
  unresolved. `/Applications/VerseView Detector.app` and real profiles are intact.
