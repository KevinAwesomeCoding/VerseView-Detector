# Desktop migration progress

Overall: **[██████████░░░░░░] 62.5% — 5 of 8 milestones complete**

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
| 6 | Standalone backend integration and packaging | In progress: frozen companion, private profile migration, core lifecycle/settings/confirmation, Smart Schedule, recovery, warmup, watcher suggestions, outline notes/output and Discord bot controls with isolated packaged checks. Windows x64 and both Mac native build/smoke/package/archive checks passed for 0.10.0. Settings sync remains; physical output is deferred. |
| 7 | Physical end-to-end checks on macOS and Windows | Deferred: real microphones/configured STT, isolated visible VerseVIEW output, queue behavior, native appearance, recovery and platform-specific behavior. |
| 8 | Installation and replacement readiness | Pending: distribution/install/update checks, migration and rollback instructions, final regressions and explicit approval before replacing the installed app. |

Completed milestones have the limits recorded in their verification reports.
They do not establish real speech transport, visible presentation, Windows
runtime correctness, or the cause of the original intermittent incident.

Milestone 6 work completed so far: native Mac companion, private profile copy,
core start/stop and decisions, error/restart/shutdown handling, Smart Schedule, explicit session recovery, local-model warmup, watcher suggestions, live outline notes/output implementation,
and packaged isolated verification. Native Windows x64, Mac ARM64 and Intel Mac
outline/watcher/warmup/recovery/build/archive checks all passed for 0.9.0. The
0.10.0 owned bot implementation passes 137 Python tests, 46 Node tests and seven
packaged suites/216 layout cases; final three-platform native CI passed.
See [bot verification](../desktop-preview/BOT_VERIFICATION.md). Remaining feature
migration covers settings sync. Keep this requirement visible rather than advancing the
overall bar while they remain incomplete.

Update this file and include the bar in future progress updates and completion
reports. Count a milestone only after its implementation and scoped verification
are complete. Latest completed milestone: settings (preview 0.4.0). Current work:
finish standalone backend feature parity and native verification. Core packaging
and Smart Schedule/session recovery are implemented; the listed feature migrations remain.
Three milestones remain; 37.5% remains by milestone count.
