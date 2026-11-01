# Native on-demand Rofi sessions — 2026-11-01

## Result

Deployed locally and retained in both restoring Hyprland overlays. App/run/calc
toggle and monitor lookup now use the existing native helper, not Python.
Transparent Wayland guards were replaced by short session-scoped compositor
callbacks and a blocking process-descriptor watcher. No resident frontend,
keyboard buffering/replay, compositor/Rofi patch, KDE change, push or PR update.

The user subsequently approved **150 ms shared layer fade-out**, down from
1 second, accepting faster closing of fading panels/notifications. Opening
remains 200 ms. A settings comparison after config-only reload showed exactly
one changed animation leaf (`fadeLayersOut`, speed 10 → 1.5); every other setting,
including window/workspace animations and curves, remained unchanged.

## Startup and typing measurements

- Ten alternating native/Python toggle measurements, including real focused-monitor
  IPC: median **3.255 ms native**, **26.5515 ms Python**. This measures the toggle
  step, not the whole launch or a physical Meta shortcut.
- Initial native input probe: **669.0 ms** first observed focus, then
  **50.6–53.7 ms**. This was not a controlled cold-cache benchmark.
- Final ten-probe run: observed focus **46.4–53.6 ms**, median **48.85 ms**.
- Typing at 0/30 ms lost prefixes to an owned harmless GTK entry. The 60/120 ms
  samples and all immediate-post-focus samples delivered the full synthetic
  arithmetic expression. Post-focus probes also moved the pointer to another
  monitor before typing; keyboard input still reached Rofi.
- These are explicit virtual-keyboard tests. They prove neither a zero-delay
  guarantee, physical global-shortcut behavior, nor preservation of pre-focus keys.
  Occasional startup latency remains. No arbitrary typing was captured or replayed.

## Live verification

- Apps, emoji and clipboard × both other outputs × left/right/middle: **18/18**
  settled-menu cases; repeated with config reload while open and after the final
  reload-race fix. Tests wait for the owned picker's painted border, not merely
  layer registration. Pointer movement alone leaves it open.
- An owned GTK sink under each outside click received **zero button presses**
  during dismissal, then received the next ordinary press after closing.
  No synthetic data was written to the real clipboard.
- Thirty open/close cycles, including ten simultaneous overlapping starts:
  one picker, no lock warnings, no clipboard writes and no remaining watcher.
  Final registration observations: 45.2–51.9 ms (not visual/focus measurements).
- Existing arithmetic, actual-view ranking/recency, safe fixture launching and
  deliberate repeat-toggle live checks: **6/6**. Existing same-monitor settled
  outside-click checks: **3/3**. Historical fixture files/results were preserved;
  their repeat-toggle rerun added an in-memory startup-lock readiness barrier.
- Final watcher PSS across 18 cases: **199–212 KiB**, median 207 KiB while open;
  no watcher remains closed. Historical Walker/Elephant benchmarks were not rerun
  or rewritten. Three native Rofi Timing-domain traces were captured privately
  through intercepted `wl-copy`, never the real clipboard.

## Automated checks and accepted baseline failures

All six active Python suites were run explicitly: **379 tests: 377 passed,
1 existing failure, 1 existing skip**. Both Lua behavioral suites passed.
Native builds pass `-Wall -Wextra -Werror`; changed Python/Lua/shell parsing,
source inventory and whitespace checks pass.

Unchanged exceptions, deliberately not repaired in this work:

1. `test_tv_tls.TvTlsTests.test_stricter_runtime_minimum_is_preserved`: TLS 1.3
   minimum is lowered to TLS 1.2 in unrelated existing production code.
2. `test_absolute_resize.AbsoluteResizeTest.test_down_moves_divider_down_from_top_without_losing_focus`:
   existing skip requiring a focused scratch Kitty.
3. Real Pleamar `RESTORE.sh --dry-run`: existing
   `manifest content mismatch: source/vitreus/bin/vitreus-tvremote`; no destination
   writes occurred. Its stale TV record remains untouched.

Isolated full ML4W dry-run and actual restore passed. The actual restore rebuilt
both the plugin and native watcher and installed the new Lua module/core sources.
The ML4W inventory matches all **625** payload files. Pleamar records were refreshed
only for the changed custom rules and the new session module.

## Recovery, review and limits

Changed live files were snapshotted before deployment, before the faster fade,
and before the reload-race fix. The live custom.lua delta against its previously
verified expected-current version is only the approved six-line Rofi block;
later user rules remain intact. Native/wrapper/module sources match the payload.

Only expected-current hashes/mtime were updated in the separate private permanent
manifest after reviewing that delta. Original restore targets, snapshots and the
historical benchmark manifest were preserved. Read-only `rollback.py --check`
passed for **12 integration files**; that is a wiring-recovery preflight, not a
claim that it checks every newly installed helper asset.

Review was **inline self-review**, the user's previously approved fallback after
the configured free agent failed on quota, not an independent review. One important
reload race was fixed RED→GREEN: adoption now rechecks that the exact verified PID
still owns a mapped layer when IPC arrives, so late adoption cannot replace a
new session with an unmapped old PID. No Critical/Important findings remain;
no deferred minors. Hotplug, reboot/login and physical shortcuts are not claimed
tested. The original dirty checkout and its coordinator link were not overwritten.

### Rulings made

- Retained the already-created `fix/rofi-startup-reliability` branch named by the
  approved spec; if wrong, the cost is follow-up branch naming, not edits to main.
- Kept the known TLS failure diagnostic rather than treating the focused task
  gate as an all-green repository claim; the cost is the disclosed unrelated TLS
  risk remaining unfixed.
- Treated the 669 ms first observation as an outlier, not a cold-cache guarantee;
  the cost is no guaranteed worst-case startup bound.
- Distinguished reload `adopt` from startup `register` to validate mapping at IPC
  delivery; if adoption cannot verify it fails safely, rather than enabling stale
  dismissal callbacks.

Private test evidence is retained under the existing launcher-trial follow-up's
`startup-reliability/` directory. Raw traces, clipboard fixtures, screenshots,
runtime files and compiled binaries are not included in the public payload.
