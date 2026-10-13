# Dock reorder validation — 2026-10-12

## Result and usage

Pinned order is kitty, system monitor, Dolphin, Brave. Hold a pinned icon with
the left mouse button for approximately 250 ms, drag horizontally onto another
pinned icon and release. A changed drop is persisted once; invalid/no-motion
drops do not write or activate the app. Existing clicks, menus and hover remain.

Production changes are confined to DockItem.qml and DockWindow.qml: existing
MouseArea events, icon positioning/highlighting and the existing settings
writer. There are no new QML objects, timers, polling, services or dependencies.
Pre-existing monitor and preview customizations were preserved.

## Behavioral tests

Run from the dock directory:

```sh
python DockApp/tests/dock_reorder.py
bash DockApp/tests/dock_previews.sh
git diff --check
```

Final real Qt mouse-event run: 21 gesture/data cases plus initialization passed
(Qt reports 22), and a separate fresh-process persistence check plus
initialization passed (Qt reports 2). Zero failures or skipped tests. The
existing preview contract test and whitespace check passed. Test homes,
desktop entries and activation logs are disposable; user app launches and
settings are not used as fixtures.

Coverage: moves in both directions and across multiple slots; stationary
delegates with a visibly moving icon; no write before release; exactly one
save per changed drop; invalid vertical/launcher/running drops; no-motion and
explicit cancellation; model replacement and hidden-window cancellation;
left-only/pinned-only arming; ordinary and held left/middle/right clicks; hover
suppression; autohide; source/target alias groups; restart persistence.

Red runs caught the initially missing hold behavior, both source- and
target-alias ordering errors, and consumption of non-reorder long presses
before fixes. Rejected hold events now retain Qt's original click behavior.
Final evidence:
`/tmp/opencode/dock-reorder-final-tests.log`, fixture artifacts
`/tmp/opencode/dock-reorder-grg1ov4c/`.

Independent final review approved with two comments. The target-alias comment
was reproduced with a failing regression test and fixed. Deferred persistence
now captures prepared data and consults DockSettings, not a window/delegate.

## Resource comparison

Six alternating fresh-process trials, identical settings/modules/environment,
20 rotations and model rebuilds per process before sampling, then six seconds
idle. Baseline uses the existing settings writer for the same rotations;
patched uses the actual drag functions. GUI mouse-event behavior is tested
separately above.

| Measurement | Baseline median | Patched median | Difference |
| --- | ---: | ---: | ---: |
| Private anonymous memory + swapped private pages | 46,588 KiB | 46,844 KiB | +256 KiB (0.25 MiB) |
| RSS | 149,116 KiB | 148,984 KiB | -132 KiB (within startup noise) |
| Idle CPU ticks / 6 seconds | 0 | 0 | 0 |

Transparent huge pages are `always` on this system. Uncontrolled baseline
launches varied by several MiB, with changes quantized in approximately 2 MiB
chunks. To distinguish the feature's sub-MiB footprint from rounding, THP was
disabled **only in disposable benchmark child processes**, via inherited
`PR_SET_THP_DISABLE`. No system setting or installed-dock launch was changed.
Earlier controlled post-use runs measured +452 and +580 KiB; all controlled
runs were below the user's 1 MB budget. Actual system-default RSS can vary by more
than 1 MB even without a code change; this is not a universal RSS guarantee.

Installed dock separately verified: one process, original system THP setting,
zero additional CPU ticks during ten sampled idle seconds, expected pinned
order and successful configuration loading. No periodic work was introduced.

Reproduce the comparison:

```sh
DOCK_BENCH_NO_THP=1 DOCK_BENCH_WARM=1 python /tmp/opencode/dock-reorder-memory.py
```

Utility and complete trial data remain in `/tmp/opencode/dock-resource-check/`.
The exact pre-edit user sources remain in `/tmp/opencode/dock-reorder-baseline/`.

## Existing environment warning

Quickshell 0.3.1 reports it was built for Qt 6.11.2 while the installed Qt is
6.12.0. This warning existed before the change; tests and the installed reload
completed successfully. No package/system changes were made.

References for native event semantics: [Qt MouseArea documentation](https://doc.qt.io/qt-6/qml-qtquick-mousearea.html)
and [Qt 6.12 MouseArea implementation](https://github.com/qt/qtdeclarative/blob/v6.12.0/src/quick/items/qquickmousearea.cpp#L1010-L1034).

## Backup

Corresponding dock settings, source, tests and documentation are mirrored into
`/shared_across_des/repos/My-Configs-Cmder/conf_backups/cachyos_hyprland_ml4w/`.
Only the dock subtree is refreshed; unrelated backups are untouched. Work is
on local feature branches, with no commits or pushes of user work.

Backup verification: 25 dock source/config files match byte-for-byte; the
manifest lists all 518 backed-up files with no missing/stale entries; scratch
artifacts are excluded. The backed-up Qt gesture/restart tests and preview
contract test also passed. Evidence: `/tmp/opencode/dock-reorder-backup-tests.log`.

## Follow-up: 400 ms hold

User requested 0.4 seconds instead of 0.8. The only production adjustment is
`pressAndHoldInterval: 400` on the existing MouseArea; no additional timer or
process is created. The real-mouse helper now verifies no drag at 350 ms and
an active drag by 450 ms. The old default failed 16 timing cases; the new
interval passed the complete suite (22 gesture/initialization checks, 2
fresh-process checks) and the preview test.

Early runs intermittently lost a held click or failed to arm. Investigation
found the fixture's readiness check accepted the immediate settings update
before asynchronous reload completed, which could replace a pressed delegate.
A regression assertion reproduced incomplete reloads across all 21 cases;
the test harness now waits for both settings updates before creating a window.
No additional production fix was needed. Final evidence is
`/tmp/opencode/dock-hold-400ms-green.log`; reload-race RED evidence is
`/tmp/opencode/dock-hold-reload-race-red.log`.

The memory comparisons above predate this one-line timing override; memory
was not reprofiled for it. Subagent authentication failed, so implementation
and the one-line review were performed inline. No package changes were made.

## Follow-up: 250 ms hold

User requested 0.250 seconds and explicitly skipped the full test workflow.
Changed only the production interval from 400 to 250 ms; usage notes, backup
and future test expectations were kept consistent. No behavioral suite or
resource benchmark was rerun for this scalar adjustment.
