# VerseView Detector desktop app

A separate Electron dashboard for macOS and Windows, with local engine events,
**start/stop, candidate approval, speech settings and cloud-provider configuration**, and a separate sample demo. The
Python companion owns microphone/STT, settings, and guarded delivery. Version
0.11.6 bundles the native backend, recovery, warmup, watcher suggestions, editable outline notes, owned Discord bot controls and private credential sync, reviewed free cloud routing and consumer cloud Settings; external-detector observation still works.
The installed detector remains unchanged. Physical acceptance and installation readiness remain open.

## Standalone companion

The Mac development artifact now includes a frozen Python companion. Press
**Launch bundled backend** to create a private preview profile and start the
host. On first use, existing detector settings and managed GCP credential files
are copied into that profile, preserving unknown fields and the original files.
Later launches retain the preview's own changes. Saved credentials never enter the
observer feed or prefilled forms; replacement fields are write-only. **Launching does not start recognition**, even when copied settings
have auto-start enabled. Normal launch enumerates input devices; verification
uses synthetic devices instead.

Press Start engine only when ready to use the configured microphone/provider and
VerseVIEW target. Scoped real speech results and their limits are in PHYSICAL_VERIFICATION.md and SEMANTIC_QUEUE_VERIFICATION.md. Backend
settings and logs live under `VerseView Desktop Preview/Backend` in the app's
profile. The folder button exposes that fixed folder, without sending secret
values to the renderer. Cloud providers, hidden key replacement, usage ceilings and Drive sync are available in Settings. Other advanced settings remain in its private JSON file; no
legacy GUI is required for the supported core workflow.

The host uses the existing engine configure/main, manual confirmation and
presentation guards. Clear output and Shift+Escape use the existing panic path.
A profile lock prevents two companions using the same profile. The dashboard
owns its child: quitting requests graceful shutdown, and a timeout keeps the
app open for cleanup. Unexpected exits are visible and are never automatically
restarted. Explicit relaunch selects the new owned PID and leaves recognition
stopped. Closing an external detector feed remains outside this ownership.

Session transcripts/optional summaries have a headless save path,
but real cloud summary behavior has not been physically verified.

A saved private `settings_sync_url` opts into a credential pull when the bundled
host launches. Recognition stays stopped. Settings also provides **Pull
credentials now** while recognition and the bot are stopped. The pull accepts
the existing credential whitelist and portable Google service-account formats;
speech, presentation and other settings retain their saved values. Credentials
and URLs stay in the private profile. During a pull, Start and settings saves
are unavailable. A download failure or intervening operator edit retains the
previous settings. Quitting discards an unfinished pull. Configure or remove
the URL only in the private backend settings file while the host is closed.
See [settings sync verification](SYNC_VERIFICATION.md) for exact artifacts,
fake-download coverage and remaining live-service checks.

The saved opt-in `local_llm_warm_at_start` now works on explicit Start, using
configured local-role clients and production request parameters on one
background worker. Dashboard status reports progress/success/failure without
exposing endpoints, credentials or raw errors. Recognition does not wait for
warmup. Stop cancels later roles/results; an in-flight synchronous request can
finish under its existing transport timeout. A quick restart skips overlapping
warmup. Routing and warmup settings remain in the private backend JSON. See
[warmup verification](WARMUP_VERIFICATION.md) for exact packages and limits.

The opt-in watcher now publishes a collapsible Verse suggestions panel, retaining
stream/language, confidence and bounded explanations. Advice expires after 90
seconds and is limited to six rows. Explicit Send uses a session-bound identity
and the existing guarded manual-delivery path; it reports command acceptance or
the need to inspect delivery activity. Advice itself is never labeled delivered.
Existing engine automatic WATCHER behavior remains unchanged. See
[suggestions verification](SUGGESTIONS_VERIFICATION.md) for packages and limits.

The Outline view connects the existing opt-in generation loop to editable notes.
Save uses the current session and note revision; a delayed model reply cannot
overwrite newer operator edits. Stop drains owned executor work, retaining the
notes in memory. Closing the backend clears them. Generated text above the
4,000-character editor limit retains previous notes with a fixed error notice.

A separate outline window opens only after you select a current monitor or
Windowed preview and explicitly open it. It displays plain text, supports Escape
and closes if its feed/session/target disappears. It is separate from VerseVIEW
verse output. Actual output-window/fullscreen routing remains physically
unverified; only injected-window routing and packaged editor tests were run.
See [outline verification](OUTLINE_VERIFICATION.md) for exact builds and limits.

Settings now includes explicit Discord bot Start/Stop, lifecycle status and
bounded recent command history. The bot runs through the bundled executable,
using private `discord_bot_token` and optional `vv_guild_id`; it connects only
when started. It controls this preview's owned backend through an authenticated
ephemeral loopback bridge, while retaining legacy host/port settings untouched.
Stopping the bot leaves recognition running. Bot Start/Stop uses current engine
capabilities; recovery still requires a local decision. Explicit verse commands
retain delivery guards and diagnostics, including duplicate suppression. Next
and previous use known engine context; send an explicit reference after changing
presentation elsewhere. See [bot verification](BOT_VERIFICATION.md) for mocks,
actual artifacts and remaining real Discord/platform checks.

Smart Schedule now shares the legacy local timetable: Saturday Malayalam;
Sunday English from 09:10, Malayalam from 10:40 and Hindi from 16:40. In the
standalone preview it resolves when you explicitly press Start. English uses
one stream; Malayalam/Hindi add an English secondary stream using the legacy
secondary-provider rules. The primary provider and delivery guards stay as
saved. Incompatible scheduled provider choices stop with a message rather than
being silently changed. The effective language is reported in the host notice
and configured speech streams; saved settings remain unchanged. No service
timer or saved auto-start starts recognition in this preview. This migration
has unit checks; a rebuilt packaged schedule check is recorded separately.

A native Windows companion must be built on Windows. The updated preview workflow
builds through the existing `verseview.spec`, smoke-tests the frozen host without
audio, packages it with Electron, and checks the resulting runtime archive. No
native Windows companion was built or executed on this Mac. Native Windows and
ARM64/Intel Mac CI build/smoke/archive checks now pass; graphical Windows execution is
still unverified. See [settings sync verification](SYNC_VERIFICATION.md) for
the latest complete native integration build, and [standalone verification](STANDALONE_VERIFICATION.md)
for the earlier core implementation.

### Session recovery

The owned companion writes a private `Backend/Recovery/session.json` checkpoint
every 15 seconds while running and on Stop/shutdown, before optional summary
processing. A crash can lose speech since the last checkpoint. Empty idle
launches do not create a checkpoint or overwrite a previous one.

On the next launch, choose **Restore saved session** or **Discard saved session**
before Start becomes available. Restore prepares the content while recognition
stays stopped. The next explicit Start configures the engine, restores context
and its existing quarantine, then starts recognition. Restore itself sends no
presentation command. Closing before Start retains the checkpoint for another
decision on the next launch. Discard removes only the preview's checkpoint.

Saved content includes both engine transcript buffers, verse history/anchor,
stream languages and bounded recent raw-speech previews. The historical preview
is separate from live STT and accepted commands. Full engine context stays in
the private file. Credentials/settings, provider logs, Discord message IDs,
pending approvals, queued references and browser commands are excluded.
Recovery does not change the saved microphone/provider configuration. Legacy
GUI checkpoint files remain untouched and are not automatically imported.

Stale decisions are rejected; corrupt files remain until explicitly discarded.
Write failures leave the previous checkpoint intact and display a generic
notice, with details in the private log. See [recovery verification](RECOVERY_VERIFICATION.md)
for tested artifacts, fault cases, native CI and remaining physical checks.

Native development build (using an approved environment with repository
requirements and PyInstaller already installed), from the repository root:

```sh
python desktop-preview/scripts/build-backend.py
python desktop-preview/scripts/smoke-backend.py
python desktop-preview/scripts/smoke-recovery.py
node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64
python desktop-preview/scripts/archive-latest.py
```

Use `--platform=win32 --arch=x64` on a native Windows host. Builds with no backend
argument remain frontend/external-observer previews and label the missing native
companion explicitly. Existing Python/packaging configuration is retained for
the operational app; the new headless option is selected only by the build helper.

## Use the dashboard

Choose **Live observer** or **Sample demo** in the window header. Both modes
support Studio/Focus layouts and Sage, Midnight, Glass, Galaxy, Aurora, and Ember
themes. Appearance, layout, and source-mode choices are saved in the preview's
own profile; sample sessions start fresh on launch.

Live observer displays the configured primary/secondary speech languages and
providers, raw final/interim transcripts, separate English translations when
provided, stream state, and recent delivery events. Activity preserves candidate
IDs, source, stream, language, stage, outcome, and timestamps. Unattributed
transcripts are kept separate. The last accepted command is distinct from
visible VerseVIEW output: this feed does not supply the visible screen or its
verse text.

A missing feed shows Waiting. A heartbeat older than six seconds shows Stale,
with the last snapshot explicitly identified. If several processes are active,
choose a detector process; the dashboard does not silently choose between them.
New sessions replace previous session data. A feed reconnect never sends a
presentation command.

In Sample demo, use Test area to generate English/Malayalam examples, duplicate
suppression, manual approval, and simulated queue release. Samples cannot
modify the observer feed. Their timestamps, confidence, providers, and outcomes
are simulated, and their safeguards are not a replacement delivery engine.

## Enable the engine export

The original installed app has not been rebuilt or replaced and cannot publish
the new feed. Use the updated repository source with the detector's existing
Python environment. From the repository root:

macOS (Terminal):

```sh
VERSEVIEW_OBSERVER=1 python vv_gui.py
```

Windows (PowerShell):

```powershell
$env:VERSEVIEW_OBSERVER = '1'
python vv_gui.py
```

These commands run the existing detector with its normal saved settings,
including any saved auto-start behavior. The observer does not change its
microphone, delivery safeguards, targets, or integrations. Start/stop and operate
that detector through its existing controls. The dashboard will discover the
feed after the detector is configured. Closing the dashboard does not stop the
detector. The exporter is disabled when `VERSEVIEW_OBSERVER` is absent.

The one-way feed uses per-process atomic snapshots:

- macOS: `~/Library/Application Support/VerseView/Observer/engine-<pid>.json`
- Windows: `%APPDATA%/VerseView/Observer/engine-<pid>.json`

Snapshots contain at most 48 recent transcripts and 192 delivery events, plus
allowlisted session/stream metadata. Raw text/translation fields are capped at
2,000 characters. They are local plaintext data, kept inside the user's profile;
Mac files are created with mode 0600. No API keys, arbitrary settings, provider
metadata, or exception messages are exported. Old process snapshots remain as
stale local data; the reader considers the newest 32 files and caches unchanged
ones. There is no network listener. The observation-only mode has no command inbox.

Raw Sarvam text is recorded before translation, so a translation error cannot
hide STT text already received. A later translation updates the same transcript
ID. Candidate IDs remain the engine's IDs; the viewer does not infer a
transcript-to-candidate association from timing alone.

## Optional dashboard controls

Enable both environment variables before launching the updated Python GUI:

```sh
VERSEVIEW_OBSERVER=1 VERSEVIEW_DESKTOP_CONTROL=1 python vv_gui.py
```

Windows PowerShell:

```powershell
$env:VERSEVIEW_OBSERVER = '1'
$env:VERSEVIEW_DESKTOP_CONTROL = '1'
python vv_gui.py
```

These are setup instructions for later physical testing; this stage did not run
that command. The GUI publishes a stopped control host before the engine starts.
Start uses its existing settings validation and configuration; it can start the
saved microphone/provider and normal integrations. Desktop-control mode routes
low-confidence manual confirmations to the dashboard instead of the legacy
popup. They stay held until a decision, stop, close, or session change; command
expiry does not silently approve them. Without the control opt-in, the original popup and observation-only behavior remain unchanged.
Closing the dashboard does not stop the detector; unhandled approvals expire.

The main process writes one atomic request into the selected host's private
`control-<pid>-<host-id>/` inbox. No network port is opened. Renderer APIs are
limited to start, stop, a decision for an existing candidate, and a typed settings save while stopped. Both sides
validate session identity; the Python GUI validates host identity, command age
(10 seconds), lifecycle state, and candidate identity again before acting.
Commands are consumed once, without automatic retries. The in-memory replay
ledger is bounded to 4,096 command IDs; restart the backend after that limit.
The inbox is for the same OS user, not a security boundary against another
process running as that user. On Windows it inherits profile-folder permissions.

A submitted request is not a running-engine or presentation acknowledgement.
The UI shows command acknowledgement, lifecycle status, and command acceptance
separately. An absent acknowledgement becomes **Outcome unknown** after 12
seconds; check the detector before retrying. Stale/ambiguous/disconnected feeds
cannot receive commands. Candidate decisions keep their engine candidate IDs,
and stop, close, or a session change cancels pending decisions. Start session
rotation follows only the exact acknowledged request on the same host.

The preview edits only the non-secret settings listed below and never exposes
credentials, arbitrary presentation commands, or bypass commands. Existing delivery guards still apply after approval. Queue
controls and passive watcher suggestions remain in the legacy detector.

## Dashboard settings

With desktop controls enabled, Settings contains microphone selection, primary
language/provider, dual STT and secondary language/provider, the detector Bible
translation, and the VerseVIEW control URL. The bundled host enumerates devices
on normal launch; close and relaunch the host after hardware changes. An external
legacy GUI feed uses that GUI's cached inventory.
No device enumeration, microphone capture, provider check or connection probe
is triggered by editing or saving this form.

Save is available only while the selected backend is fresh and stopped. The
backend checks that state again at execution time. Changes apply on the next
engine start. The provider choices follow the selected language. URLs accept
HTTP/HTTPS without credentials, query parameters or fragments; format validation
does not establish that a target exists or is isolated.

Drafts stay in memory, retain focus during incoming feed events, and are
separate from samples. They are not saved in localStorage. A revision token
covers both the backend GUI state and its settings file; an intervening edit
requires Reload before saving. A save request is not marked Saved until the
backend acknowledges it. Missing acknowledgement is Outcome unknown, without
an automatic retry.

A save updates only the displayed non-secret fields in the existing settings
file. Unknown fields and stored credentials are preserved; unrelated unsaved
legacy GUI fields remain unsaved. The writer replaces the settings file
atomically, so a write failure retains the prior file. Failed application of a
change restores the legacy widgets and leaves the dashboard draft available.
The form locks when the backend is running, closed, stale, or unavailable.

Native standalone packages include their Python backend. Frontend-only packages
still need an updated external detector. Credentials, audio format/timing,
safety settings and advanced provider options remain in the private backend
settings file; secrets are not editable in the dashboard. Watcher suggestions,
outline notes and bot controls have dedicated dashboard panels.

## Platforms and glass

The pinned Electron release supports macOS 13+ and Windows 10+. This is a
preview requirement, not a change to the existing Python app's support policy.
Glass requests native macOS vibrancy or Windows acrylic on Windows 11 22H2/build
22621 and newer. Older Windows versions use an opaque fallback. Other themes
are opaque. Reduce Transparency and high contrast disable native effects.
Native appearance varies by OS and accessibility/window state; reading panels
stay nearly opaque.

Sources: [Electron window materials](https://www.electronjs.org/docs/latest/api/browser-window),
[native theme preferences](https://www.electronjs.org/docs/latest/api/native-theme),
[supported platforms](https://github.com/electron/electron/blob/v44.9.0/README.md#platform-support).

## Develop and package

With Node 24, from this folder:

```sh
npm ci
npm start
npm test
npm run check
npm run package:mac
npm run package:windows
```

The previously approved local dependencies are pinned in the lockfile. Every push
to `main` now runs **Build VerseView Detector** (`.github/workflows/build.yml`). It
calls the reusable `desktop-preview.yml` workflow to test and build the current
Electron app with its frozen Python backend on Windows x64, Mac ARM64 and Mac Intel.
The reusable workflow can also be run manually without publishing.

After all three platforms pass, the main workflow verifies the extracted-runtime
reports and archive checksums again, then automatically publishes a **GitHub beta
release** containing three clearly named native app packages. SHA256 checksums
are in a collapsed section of the release notes; technical reports stay in Actions
artifacts instead of cluttering the app download list.
A missing, failed or corrupt package prevents publishing. Beta releases do not
replace the existing stable release. These remain preview builds; production
signing/notarization and the remaining physical acceptance gates are incomplete.
Uncommitted local changes are not included in GitHub builds.
Other architectures can be selected explicitly:

```sh
npm run package -- --platform=darwin --arch=x64
npm run package -- --platform=win32 --arch=arm64
```

The official packager creates uniquely named output directories under `out/`,
with source provenance beside the app and inside `app.asar`. The shell,
frontend, local icons/licenses, runtime manifest, and build record are packaged;
native builds additionally include the frozen companion outside `app.asar`.
Credentials, production settings and test files are excluded from the runtime.
Mac builds made on Mac receive verified local ad-hoc test signatures. Windows
builds are unsigned. Downloads remain beta software.

The consumer Mac ZIP contains only `VerseView Detector.app`; required licenses
and build metadata stay inside the bundle. Extract it and move it to Applications
when ready to install. Windows downloads are one `VerseView-Detector-Windows-Setup.exe`,
a per-user installer that stores the required Electron runtime files together
and supplies a Start menu entry and uninstaller. The native Windows runner builds
it with its existing Inno Setup compiler, silently installs it in a temporary
directory, verifies the installed runtime/frozen backend, then uninstalls it.
This is automated installation coverage; physical Windows acceptance is deferred.

See the [installation and rollback guide](INSTALLATION_AND_ROLLBACK.md) for
profile locations, one-time settings/managed-credential import, private backups,
manual updates and uninstall/reinstall. Packaged builds now check GitHub releases
for a newer verified package on launch and every two minutes while open. A new
release shows an in-app prompt and **Update** in the title bar. The app downloads
and checks the package before replacing it at the
same location after shutdown. Settings and credentials remain in the profile.
The [installation verification report](INSTALLATION_VERIFICATION.md) records
actual packaged Mac upgrade/rollback results and unverified Windows/security gates.

```sh
node scripts/verify-package.cjs '/path/to/VerseView Detector.app'
node scripts/verify-package.cjs '/path/to/installed/VerseView Detector'
```

## Checks and next work

`npm test` covers command/session validation, appearance and feed validation, version/accessibility
fallbacks, stale/disconnected recovery, multiple processes, session replacement,
and bounded reading. `npm run check` checks syntax and offline CSP. The existing
Python environment runs `python -m unittest discover -s tests` from the repository
root; those checks use mocked external services.

The UI scripts can use an existing Playwright installation; no extra package or
browser download is included. Set `PLAYWRIGHT_MODULE` to that module's path when
needed. Set `PREVIEW_EXECUTABLE` for the packaged binary; otherwise they run the
development app:

```sh
node tests/ui.cjs
OBSERVER_PYTHON=/path/to/detector/python node tests/observer-ui.cjs
OBSERVER_PYTHON=/path/to/detector/python node tests/controls-ui.cjs
OBSERVER_PYTHON=/path/to/detector/python node tests/settings-ui.cjs
PREVIEW_EXECUTABLE=/path/to/packaged/app-binary node tests/backend-ui.cjs
```

The observer UI test uses actual Python callback/parser/delivery code behind
mocked services. Its snapshots and screen banner say **callback replay**, and
it does not establish microphone/STT transport or visible presentation output.
Test feeds use temporary directories; Electron automation uses a separate QA
profile. Results/screenshots go into ignored `test-results/`.

See [standalone verification](STANDALONE_VERIFICATION.md) for current results,
[settings verification](SETTINGS_VERIFICATION.md) for stage five,
[the project progress bar](../docs/DESKTOP_MIGRATION_PLAN.md) for overall scope,
[control verification](CONTROL_VERIFICATION.md) for stage three,
[observer verification](OBSERVER_VERIFICATION.md) for stage two, and
[the milestone-one report](VERIFICATION.md) for the original desktop preview.
Isolated Mac installation, update, uninstall/reinstall and rollback checks now
pass. Windows graphical lifecycle and production signing/distribution acceptance
remain open. See [installation verification](INSTALLATION_VERIFICATION.md).
Mac physical acceptance is partial: a real microphone/provider connection and
native window/outline checks are recorded in [the physical checkpoint](PHYSICAL_VERIFICATION.md).
Human speech, actual verse output and Windows graphical acceptance remain open.
The progress plan records completion criteria and the remaining release gates.

Semantic model compatibility and the pending live queue check: [verification](SEMANTIC_QUEUE_VERIFICATION.md).


## Product name and theme icons (0.15.0)

All three native targets use **VerseView Detector** for the application name.
The original repository icon is the static bundle/installer/shortcut icon and
first-launch runtime/sidebar icon. Selecting any of the six appearance themes
uses its matching logo in the sidebar and the Mac Dock or Windows window icon;
the choice survives restarts. Finder and pinned shortcut images remain the
original static icon; the running application controls its own native icon.
Native appearance preferences load before window creation. Existing renderer
preferences migrate without losing the saved theme. The internal desktop profile
folder and preference key retain their old Preview names to preserve existing
settings, credentials and sessions; this is not the displayed product name.

Consumer downloads expose no provenance, version or license siblings. Required
license notices remain in the installed runtime. Build reports/checksums stay in
Actions artifacts and release notes. See [consumer packaging verification](CONSUMER_PACKAGING_VERIFICATION.md)
for verified results and platform limitations.
