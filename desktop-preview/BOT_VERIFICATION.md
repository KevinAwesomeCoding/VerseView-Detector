# Owned Discord bot verification — preview 0.10.0

Overall migration: **[██████████░░░░░░] 62.5% — 5 of 8 milestones complete**.
Bot integration is part of milestone 6; settings sync remains. Physical tests
are deferred. The original intermittent delivery incident remains unresolved.

## Provenance

Runtime source: `a6c6146a6cb67635bd2d4dbf78d96614a95fff39`, committed and pushed
on `codex/desktop-backend` in the existing repository. No uncommitted code was
included; unrelated `.DS_Store` remains excluded.

Exact app:
`desktop-preview/out/2026-10-18T11-14-23-016Z-a6c6146a-darwin-arm64/VerseView Desktop Preview-darwin-arm64/VerseView Desktop Preview.app`.
Native input: `desktop-preview/backend-build/20261018T111359Z-darwin-arm64/backend`.
The packaged bot report identifies that executable/build and confirms an owned,
frozen, GUI-free bot child. The native input was hidden during the UI check.

Existing build commands, using the approved environment and ad-hoc signing:

```sh
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/build-backend.py
node desktop-preview/scripts/package-native.cjs --platform=darwin --arch=arm64
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/smoke-bot.py
/tmp/verseview-standalone-build-20261017/bin/python desktop-preview/scripts/archive-latest.py
```

No new dependencies, system security changes, installed-app replacement, main
push or production release occurred. Evidence is retained in the build's
`verification/` directory, including earlier failed invocation logs/screenshots.

## Results

| Case | Result and limits |
| --- | --- |
| Regressions | PASS: 137 Python tests and 46 Node tests; JavaScript syntax/offline-page and whitespace checks. |
| Owned lifecycle | PASS with mocks: explicit Start bot, separate frozen child, Stop bot, graceful parent EOF and host cleanup. Stop bot leaves recognition running. Unexpected child exit reports failure without an automatic process restart. |
| Private bridge | PASS: ephemeral loopback port, private token, expiring request identity, replay rejection and bounded non-secret command history. Start/Stop use the desktop command inbox and current capabilities. |
| Delayed acknowledgement | PASS in focused HTTP/inbox test: if a power request is written but its result does not arrive within three seconds, HTTP 504 and the history label it unknown. The test later processes that original request once; no retry or false rejection/acceptance claim is added. |
| Delivery | PASS with fake browser: John 3:19 and next John 3:20 reach COMMAND_ACCEPTED with matching bridge/candidate IDs and DISCORD-MANUAL source. Stream attribution remains unknown because this is a remote operator command. Acceptance does not establish visible output. |
| Guards | PASS: immediate previous/re-present commands retain duplicate suppression; worship mode blocks delivery; invalid references, stopped engine and pending recovery cannot be bypassed. No blind presentation retry was added. |
| Compatibility | PASS with mocks: existing slash-command vocabulary and control panel retained. Clear uses panic; Close uses the existing presentation-close action. Next/previous use known engine context and canonical bounds; use an explicit reference after an external presentation change. |
| SDK source check | PASS: actual discord.py 2.7.1 command registration and callbacks with mocked interactions/bridge/login; invalid-token failure is fatal without retry. No real Discord connection/messages were made. This source check does not establish real SDK login in the frozen package. |
| Packaged bot UI | PASS: Settings status and owned PID, explicit Start/Stop, immediate command acknowledgement, bounded history, reachable controls across 36 width/layout/theme cases. Narrow screenshot inspected. |
| Other packaged regressions | PASS: core backend, settings, outline, suggestions, warmup and recovery on this same artifact. Seven suites, 216 layout cases total; each report's build ID was checked before collecting evidence. |
| Native CI | PASS: run 39122401057 for Windows x64, Mac ARM64 and Intel Mac: unit tests, native build, frozen bot/outline/watcher/warmup/recovery/startup checks, package inventory and extracted-archive verification. No graphical Windows execution is claimed. |
| Local archive | PASS: extracted runtime inventory, ad-hoc deep/strict signature and frozen no-input startup. |
| Actual Discord login/commands, microphone/STT, visible VerseVIEW, live semantic queue, physical native appearance and Windows GUI | DEFERRED / UNVERIFIED. |

Packaged accepted commands (synthetic bot input, UTC; no spoken input or real Discord message):

| Reference | Candidate / bridge ID | Timestamp |
| --- | --- | --- |
| John 3:19 | `af2762494b9244f78fe5b8e55d0214e6` | `2026-10-18T11:14:51.845602+00:00` |
| John 3:20 | `9f55278d312a4d64a1788a12569c5778` | `2026-10-18T11:14:51.846251+00:00` |

The packaged child uses the existing bundled bot script through the backend
executable's bot dispatch; it never invokes system Python. Normal Start bot
uses private `discord_bot_token` and optional `vv_guild_id`. Legacy `vv_host`
and `vv_port` values remain stored, while this preview's bot controls its owned
local backend through the private ephemeral bridge. Bot connection is opt-in.
Existing Discord SDK reconnect behavior remains; delivery commands are not
automatically retried. Credentials, server ID and raw SDK logs stay outside the
renderer. Private logs are bounded under `Backend/Logs/discord-bot.log`.

## Failures found and repaired

The first frozen smoke reached accepted/suppressed commands, then failed on a
harness assumption that Stop alone requires a recovery decision. The corrected
test closes/reopens the host before checking recovery. Both invocation logs
are retained; that assumption was not an application defect.
The initial native CI run 39121175840 failed that same bot smoke step on all
three platforms; it is superseded by the corrected final run listed above.

The first packaged UI run reproduced a session-selection race: a remote Start
rotated the session before its bridge acknowledgement arrived. The dashboard
lost the selected feed while the backend kept running. It now retains only the
same process/control identity while waiting for matching acknowledgement in
the new session. A regression includes the intermediate missing-ack snapshot.

The next run reproduced a Settings-view acknowledgement defect: controls stayed
disabled until the timeout because acknowledgement was processed only in views
containing engine controls. Reconciliation now runs in shared view updates.
A focused view regression and the corrected packaged run pass. Missing bot
panel padding/history bounds were corrected without redesigning the interface.

Inspection also found unsupported `Path.open(opener=...)` in headless session
transcript/summary saving. Built-in `open` now preserves the intended private
file mode; focused tests cover transcript-only and optional mocked summaries.
These findings do not explain the original intermittent delivery incident.

Additional lifecycle checks cover incomplete private settings JSON, Stop racing
with loop closure, and quitting while the owned bot is draining. Status errors
do not escape the bot projection or expose file contents. Stop bot immediately
rejects new bridge requests. Host shutdown signals recognition Stop before
waiting for the bot; it retains the process while either owned component still
needs cleanup. This preserves the existing stopping/timeout UI instead of
letting recognition continue because a bot request is slow.

## Development deliverable and cleanup

Changed files cover the owned backend/control adapters (`desktop_backend.py`,
`desktop_control.py`, the new `desktop_bot*.py` modules and `vv_discord_bot.py`),
the explicit QA adapter, Electron command/feed/preload/main handlers, Settings
bot panel/CSS, native source inventory/workflow, bot smoke/UI/view tests and
focused engine/backend/bot regressions. Version manifests and investigation,
preview and roadmap documentation were updated. The engine delivery guards
themselves were reused; no guard was removed or disabled for these commands.

Local archive:
`desktop-preview/out/deliverables/2026-10-18T11-14-23-016Z-a6c6146a-darwin-arm64.tar.gz`.
SHA-256: `16dd9efc36eb0a713ca17fb6540d57d65fb1886f98c75cf6558c81f16567e03e`.

Native run [39122401057](https://github.com/KevinAwesomeCoding/VerseView-Detector/actions/runs/39122401057)
completed successfully against the runtime source above. GitHub outer transfer
digests (separate from the inner tar/ZIP checksum):

| Target | Artifact ID | SHA-256 |
| --- | --- | --- |
| Windows x64 | 12135265793 | `a5789cde5b54397f9e7caddf26e8e7741479c8c52cf34ec2bd134f4d27055ad1` |
| Mac ARM64 | 12134453842 | `6889c2d01114e5e7c9ec915c3d5d7822e1eb1a62258f1b9c7ac68cb737a9d383` |
| Intel Mac | 12134926770 | `3d4d64a283406e1c11b49bbb760f66669dd8d1303613fb54f75539c0aee3aca1` |

Metadata and failure annotations were read from GitHub and saved with the local
evidence. Native runners verified their packages; remote artifacts were not
downloaded or executed on this Mac.

Final owned QA apps/children exited; native build inputs were restored. The final
disposable QA profile was checked for synthetic credentials, its engine PIDs
were confirmed exited, and it was removed. Synthetic source folders were
removed by the harnesses. The installed application,
production profile, main branch, security settings and display timeouts remain
unchanged. Final artifacts/build inputs and the approved environment are retained
for reproducibility; this report does not authorize replacing the installed app.
