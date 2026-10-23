# Preview installation, migration and rollback

## Current consumer beta downloads (0.15.0 and later)

Use the current GitHub beta release matching your platform. Apple Silicon and
Intel Mac downloads are ZIPs containing only **VerseView Detector.app**. Extract
the ZIP, then copy the app to a separate versioned folder for evaluation. Leave
the original operational app intact until you choose to replace it. Required
license notices and provenance are inside the app; checksums are in the release
notes. Native ditto creation/extraction preserves executable modes and framework
symlinks.

Windows downloads are a single **VerseView-Detector-Windows-Setup.exe**. Setup
installs for the current user under `%LOCALAPPDATA%\Programs\VerseView Detector`,
with a Start menu entry and uninstaller. It keeps required runtime files together.
Uninstall via Windows installed apps; the installer does not delete your profile,
settings, keys or saved sessions. Keep the previous trusted installer for rollback.

The displayed product is now **VerseView Detector** on all platforms. The internal
`VerseView Desktop Preview` profile paths below are intentionally unchanged for
upgrade compatibility. First launch uses the original icon; explicit/saved theme
choices affect the sidebar and running Dock/window icon. Finder and pinned
shortcuts retain the original static icon.

Signing/security and physical Windows limitations below still apply. The old
archive/executable instructions in the following historical sections describe
pre-0.15.0 builds. See [consumer packaging verification](CONSUMER_PACKAGING_VERIFICATION.md)
for the current build results.


The Electron application is still a separate development preview. The original
installed detector remains the operational app. These steps describe a manual
preview installation/update; they do not authorize replacing the operational
app or publishing a release. Mac speech acceptance has scoped results in PHYSICAL_VERIFICATION.md and SEMANTIC_QUEUE_VERIFICATION.md. Windows physical acceptance remains deferred.

## Choose and verify a package

Use a native artifact from the successful scoped preview workflow, matched to
your machine: Mac ARM64, Intel Mac x64, or Windows x64. The exact tested source,
build ID and archive checksum are recorded in the corresponding verification
report. Verify the inner archive's SHA-256 against its `.sha256` sidecar before
extracting. GitHub's outer artifact digest is a different checksum.

Mac deliverables are `.tar.gz` archives so executable modes and Python framework
symlinks survive transfer. Windows deliverables are ZIP files. Extract the whole
archive into a new directory. Keep provenance and checksum records with that
version; keep the prior working artifact for rollback. The development workflow
expires remote artifacts after 14 days, so it is not a permanent release channel.

For a repository checkout with its approved Node dependencies, optional package
inventory verification is:

```sh
node desktop-preview/scripts/verify-package.cjs '/path/to/VerseView Desktop Preview.app'
node desktop-preview/scripts/verify-package.cjs '/path/to/VerseView Desktop Preview-win32-x64'
```

This checks the embedded source/runtime inventory; it is not publisher identity
verification. Mac test apps have local ad-hoc signatures, and Windows test apps
are unsigned. Gatekeeper, notarization, Windows SmartScreen, a public installer
and production signing have not been accepted. If the OS blocks opening a
development package, stop and record the message. Do not disable security,
remove quarantine or change signing settings to make this procedure pass.

## Data locations and first launch

| Data | macOS | Windows |
| --- | --- | --- |
| Existing detector profile | `~/Library/Application Support/VerseView/` | `%APPDATA%\VerseView\` |
| Preview preferences and profile parent | `~/Library/Application Support/VerseView Desktop Preview/` | `%APPDATA%\VerseView Desktop Preview\` |
| Preview backend settings, credentials, logs and recovery | `…/VerseView Desktop Preview/Backend/` | `…\VerseView Desktop Preview\Backend\` |

Verification scripts use a further `QA/Backend` directory. Normal app launches
must not use the verification environment variables shown in test documentation.

On a Mac, copy the complete `VerseView Desktop Preview.app` to a separate folder
you own, such as `~/Applications/VerseView Preview/`. Open that exact app. Leave
`/Applications/VerseView Detector.app` intact. On Windows, copy the entire
`VerseView Desktop Preview-win32-x64` directory to a separate user-owned folder
and open `VerseView Desktop Preview.exe` there. Keep its DLLs/resources beside
the executable; copying only the EXE is not an installation.

Select Live observer and **Launch bundled backend**. On the first launch only,
the backend manager copies existing detector settings into its own profile,
including unknown fields. JSON files in the existing managed `credentials`
directory are copied privately; a GCP path into that directory is redirected
to the preview's copy. An arbitrary credential path outside that managed
directory is retained as an external dependency, not automatically imported.
Check it before using that provider; retain its separately secured backup.

Later launches use the preview's own settings. Changes to the original profile
are not imported again, and preview changes are not written back to it. The
dashboard's **Open backend settings folder** button opens its private backend
directory. In version0.11.6 and later, Settings → Cloud providers offers reviewed routes, write-only key replacement fields, free-use limits and a Drive download URL. Existing keys are represented only by presence indicators. Other advanced options remain in the private settings file.

Recognition remains stopped after host launch even if copied `auto_start` is
true. A saved `settings_sync_url` does opt into a credential pull at host launch;
review this private setting before launching if that is not intended. Bot login
and outline output require separate explicit controls. Real microphone/STT and
presentation should start only in the isolated test session approved by the user.

## Manual update and backup

Packaged builds check GitHub releases for a newer compatible stable or beta
package on launch and every two minutes while open. When one is available,
the app shows an in-app prompt and **Update** appears in the title bar. **Later**
dismisses the prompt for that release until the app closes; a newer release
prompts again. Clicking **Update now** or the title-bar **Update** button
it downloads the whole native package and verifies its published SHA-256 before
the app quits. On Mac, a helper extracts and verifies the complete app bundle,
then swaps it into the existing location and keeps the prior bundle as a hidden
rollback copy. The location must be writable by the current user. On Windows,
the verified per-user installer runs for the existing install directory. Keep
the profile backup and previous installer for important upgrades. If the
download or verification fails, the installed app remains in place.

To update manually, use a complete new native package.

1. Stop recognition and the Discord bot, then close the backend and quit the
   preview. If the app says shutdown is still pending, wait for cleanup before
   changing files. Do not swap a running executable or delete a live profile.
2. Back up the entire preview profile parent from the table, preserving its
   directory structure, settings, credentials, recovery data and preferences.
   Store the backup privately: it can contain API keys, service-account keys,
   speech transcripts and logs. Keep the prior app/package and its provenance.
3. Extract and verify the new package in a separate versioned location. Keep
   the whole Mac app or Windows directory intact. Update a shortcut only after
   verifying the executable/build ID being opened.
4. Launch that new package and its bundled backend. Check its version/build ID,
   stopped state, selected settings and credential availability before Start.
   An existing preview profile must be retained; the source detector profile
   must not overwrite it. An unexpected migration error is a stop condition.
5. Perform the remaining physical acceptance checks in the isolated environment.
   Retain the previous package and backup until the new version is accepted.

Backups containing absolute GCP paths should be restored to the same profile
location. Moving a profile to another account or OS requires reviewing absolute
paths and provider/device configuration; copying JSON alone does not establish
a successful migration.

## Rollback and uninstall

For rollback, close the preview and all its owned work first. Keep a private
copy of the current profile for diagnosis. Reopen the retained previous preview
package. Compatibility of that older package with every future profile format
is not guaranteed. If needed, restore the complete pre-update profile backup to
its original location while both versions are closed, then open the prior app
and verify its settings and credentials before recognition. A tested 0.10 to
0.11 profile round trip is evidence for those versions only.

To uninstall the portable preview, quit it and remove only the copied preview
app/directory and its shortcuts. The profile remains for reinstall or rollback.
Deleting the preview profile is a separate, destructive operation; back it up
and obtain the user's explicit instruction before doing so. Do not delete the
existing detector's app/profile. Removing the preview does not revert any
settings in the operational detector because they are separate.

## Operational replacement gate

No installed-app replacement is performed by these steps. The current preview
has a distinct application identity/profile and development signing. It should
not be made the production application by renaming it over the installed app.

Before proposing a production replacement, finish physical Mac and Windows
acceptance, resolve material failures, identify the release/signing/update plan,
and prepare an exact backup/migration/rollback procedure for the approved target.
Then present the concrete artifact, destination and remaining limitations and
request explicit approval. Keep the old app and original profile recoverable.

See [installation verification](INSTALLATION_VERIFICATION.md),
[settings sync verification](SYNC_VERIFICATION.md), and the
[migration plan](../docs/DESKTOP_MIGRATION_PLAN.md) for verified results and open gates.
