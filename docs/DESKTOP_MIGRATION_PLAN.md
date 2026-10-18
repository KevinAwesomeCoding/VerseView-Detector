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
| 8 | Installation and replacement readiness | In progress: distribution/install/update checks, migration and rollback instructions, final regressions and explicit approval before replacing the installed app. |

Completed milestones have the limits recorded in their verification reports.
They do not establish real speech transport, visible presentation, Windows
runtime correctness, or the cause of the original intermittent incident.

Milestone 6 final source `b2555dd5228d08930e5f5448aa922c9429eb7699` passes
149 Python tests, 48 Node tests and eight same-artifact Mac packaged suites
covering 252 layout cases. Windows x64, Mac ARM64 and Intel Mac native CI
build/frozen-smoke/package/extracted-archive checks pass in run 39124243081.
See [settings sync verification](../desktop-preview/SYNC_VERIFICATION.md)
for exact artifacts, preserved failure evidence and synthetic transport limits.

Current work is bounded installation/update/uninstall/rollback verification in
a separate preview location and disposable profile, followed by migration and
rollback instructions. The installed detector remains intact. Milestone 7
stays deferred. Production replacement and a release are not authorized.

Update this file and include the bar in future progress updates and completion
reports. Count a milestone only after its implementation and scoped verification
are complete. Latest completed milestone: standalone integration (preview 0.11.0).
Two milestones remain; 25% remains by milestone count. Preparation for milestone
8 can proceed now; physical acceptance and replacement approval remain release gates.
