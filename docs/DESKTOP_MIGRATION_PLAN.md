# Desktop migration progress

Overall: **[████████████░░░░] 75% — 6 of 8 milestones complete**

This is an engineering milestone count, not elapsed-time estimation or a
production-readiness score. The scope below is the current working baseline;
changes to scope can change the denominator. Physical tests are deferred at the
user's request. macOS and Windows remain required throughout.

| # | Milestone | State / completion requirement |
| --- | --- | --- |
| 1 | Dashboard design and themes | Complete: approved interactive prototype, separate bilingual panels and themes. |
| 2 | Cross-platform desktop shell | Complete with isolated checks: separate Electron packages; Windows execution remains in milestone 7. |
| 3 | Bilingual engine event connection | Complete with isolated checks: raw speech, translation, candidate IDs and delivery outcomes. |
| 4 | Engine controls and manual decisions | Complete with isolated checks: start/stop requests, lifecycle status, exact-candidate approval/rejection. |
| 5 | Non-secret settings in the dashboard | Complete with isolated checks: microphone, languages/providers, dual STT, Bible translation and VerseVIEW URL; stopped-engine saves, validation, conflict handling and package verification. |
| 6 | Standalone backend integration and packaging | Complete within isolated scope: frozen companion/private profile, core lifecycle/settings/confirmation, Smart Schedule, recovery, warmup, watcher suggestions, outline notes/output, owned Discord bot controls and credential sync. Preview 0.11.0 passes all three native CI targets and eight packaged Mac suites. |
| 7 | Physical end-to-end checks on macOS and Windows | Deferred: real microphones/configured STT, isolated visible VerseVIEW output, queue behavior, native appearance, recovery and platform-specific behavior. |
| 8 | Installation and replacement readiness | In progress: isolated Mac portable install/update/uninstall/reinstall and rollback pass; migration/rollback guide is written. Windows graphical lifecycle, production identity/signing/distribution, physical acceptance and explicit approval before replacement remain open. |

Completed milestones have the limits recorded in their verification reports.
They do not establish real speech transport, visible presentation, Windows
runtime correctness, or the cause of the original intermittent incident.

Milestone 6 final source `b2555dd5228d08930e5f5448aa922c9429eb7699` passes
149 Python tests, 48 Node tests and eight same-artifact Mac packaged suites
covering 252 layout cases. Windows x64, Mac ARM64 and Intel Mac native CI
build/frozen-smoke/package/extracted-archive checks pass in run 39124243081.
See [settings sync verification](../desktop-preview/SYNC_VERIFICATION.md)
for exact artifacts, preserved failure evidence and synthetic transport limits.

Preview 0.11.1 verifies installation/update/uninstall/reinstall/rollback in a
separate Mac location and disposable profile, with actual packaged 0.10.0 and
0.11.1 applications. It fixes obsolete external-detector guidance and a stale
connection footer in the owned-backend view. See the
[installation report](../desktop-preview/INSTALLATION_VERIFICATION.md) and
[migration/rollback guide](../desktop-preview/INSTALLATION_AND_ROLLBACK.md).
The installed detector remains intact. Milestone 7 stays deferred. Production
replacement and a release are not authorized; the open gates above prevent
counting milestone 8 complete.

Final 0.11.1 native CI run 39139494109 passed on all three targets, with 149
Python and 49 Node tests, frozen feature checks and extracted archives. Local
readiness, core backend and sync packaged checks passed on the exact final app.
No additional isolated feature migration is currently scheduled. Do not repeat
completed builds/suites without a source change, failure or unresolved concern.
The next acceptance work requires lifting the physical-test deferral and
resolving the isolated target; production distribution/replacement decisions
remain separate. Do not start live services or replace the installed app merely
because an automation asks to continue.

See the [final incident/gap audit](DELIVERY_GAP_AUDIT.md) for the supported
findings and exact remaining user actions. It also records an older packaged
test's unfinished settings-restoration claim; current QA cleanup must not be
treated as proof that those historical settings were restored. Any restoration
needs review of the user's intended current values before changing them.

Update this file and include the bar in future progress updates and completion
reports. Count a milestone only after its implementation and scoped verification
are complete. Latest completed milestone: standalone integration (preview 0.11.0).
Two milestones remain; 25% remains by milestone count. Preparation for milestone
8 can proceed now; physical acceptance and replacement approval remain release gates.
