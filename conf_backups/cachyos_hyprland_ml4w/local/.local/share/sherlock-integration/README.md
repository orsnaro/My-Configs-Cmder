# Sherlock primary launcher

## Everyday use

- Bare Super: toggle applications/calculator open or closed; also dismiss a visible emoji/history picker.
- Super+V: existing cliphist history, including image previews. Enter copies the selected item; Escape cancels without changing the clipboard. Paste normally afterward.
- Super+period: native searchable emoji grid directly.
- Super+R: unchanged Rofi command runner. `~/.local/bin/rofi-trial apps` opens the previous app launcher.
- Unmodified left/right/middle clicks outside Sherlock dismiss it (on any monitor); the dismissal click is consumed. Inside clicks and modified mouse shortcuts remain normal. Escape still closes it.

One `sherlock.service` user service owns the resident UI. The existing `wl-paste --watch cliphist store` recorder is unchanged. `sherlock-clp` runs only when history is opened. No additional clipboard recorder, theme watcher, blur rule or wallpaper hook was added.

The CSS retains Cairo, 85% background opacity, opaque text and 10px outer corners. It imports the existing GTK palette at startup; automatic wallpaper refresh is deferred. `systemctl --user restart sherlock.service` refreshes that palette manually without stopping applications launched by Sherlock.

## Installation and verification

- Official Sherlock release `v0.1.14-3`; archive digest verified against GitHub's published SHA-256. Executable reports `v0.1.14`, as built upstream.
- Clipboard helper source pinned to `9c6600d467e1ea81cfd70f8f4fc9b8e135b1363c`. Upstream lockfile's obsolete root package name was corrected locally; dependency versions/checksums were not changed. The original is saved as `upstream-clipboard/Cargo.lock.upstream`.
- The local Rust build used `/usr/bin/cc` as its linker for build/test commands only; no global compiler settings changed. `cargo test --locked` succeeds, but upstream defines zero unit tests.
- Run local tests with `python -B -m unittest -v` from this directory: 36 tests cover cancellation, byte-exact data, decoder errors, concurrent requests, PID-scoped mode state, native Close without reload/restart, intentional restarts, native IPC framing, ownership and startup readiness. `lua test_session.lua` covers toggle/click hit-testing and layer lifecycle.
- Native GUI checks verified calculator, a harmless temporary .desktop application, direct emoji search, synthetic text/image selection and return to app search. The temporary desktop entry was removed. Real clipboard contents were never inspected or overwritten by the tests.
- Independent review was unavailable because the configured free model quota was exhausted. Implementation and review were done inline.

The wider existing Hyprland suite is **not fully passing**. Both the original backed-up configuration and the installed configuration produce 11 passes and these same seven failures:

1. `brave_google_signin.lua`
2. `brave_task_manager.lua`
3. `glaze_bindings.lua`
4. `glaze_brave_launchers.sh`
5. `glaze_mail.lua`
6. `obsidian_settings.lua`
7. `qbittorrent_dialogs.lua`

Six Lua tests have incomplete pre-existing mocks of `hl.bind`: the unchanged `rofi_session.lua` expects a returned button with `set_enabled`. The separate Brave launcher expectation also fails unchanged. No unrelated code/tests were modified to conceal these failures.

Evidence and protected-file backups: `~/.local/state/sherlock-migration/20261102/`. See `live-check.json`, `resources.json`, `hyprland-tests.json`, `baseline-tests.json`, `before.json` and `progress.md`.

Initial installation sample, before the repeated-Meta incident: 76.188 MiB PSS and 2.357% of one CPU core over 10.184 seconds open-idle; 76.015 MiB and 0% over 6.108 seconds hidden afterward. This excludes the compositor and the existing recorder. Clipboard images can increase transient RAM; the wrapper releases the history model after selection/cancellation. This is not a zero-overhead guarantee.

## Repeated-Meta hang: verified workaround

The original integration unnecessarily sent Close → Show → SwitchMode(Search) on every app shortcut. Native Show-only stayed responsive; repeating SwitchMode(Search) reproduced a persistent ~100% CPU loop, with the window sometimes stuck at 200×200. Merely caching repeated apps requests was insufficient: repeated emoji/app model reloads could still reproduce it.

- Ordinary app reopening now sends only native Show and retains the same daemon PID.
- Mode changes and history dismissal safely rebuild through the **same existing service** rather than repeatedly replacing native models within one process. One initial mode population per fresh daemon preserves the native emoji grid and correct app aliases. This is an integration workaround, not an upstream GTK/Sherlock patch.
- The tradeoff is a brief cold-start delay for mode changes. There is no watchdog, extra daemon or service-unit policy change.
- Intentional mode-change restarts first reset this service's systemd failure/start counter so legitimate rapid switching does not trip crash rate limiting. Automatic unattended crash-loop protection is otherwise unchanged; journal evidence remains available.
- History cancellation waits for the native response client before replacing the UI. Delayed history cleanup cannot restart/hide a newer app window. Test clipboard data/sinks are isolated; real clipboard contents are not read or overwritten by verification.

Regression commands: `python -B burst_check.py --label latest` (60 rapid actual wrapper invocations), and `python -B transition_check.py` (four emoji/app cycles, cancellation of active synthetic history by reopening apps, then 40 open/close cycles with one stable app PID). Both verify normal 900×593 geometry and CPU settling; results and pre-fix evidence are saved in `~/.local/state/sherlock-migration/20261102/meta-fix/`.

## Toggle/outside-click correction

`~/.config/hypr/sherlock_session.lua` checks live layer visibility and logical global cursor coordinates inside Hyprland. The bare-Super callback opens the unchanged app wrapper when hidden, or asks the existing IPC helper to Close the observed PID when visible. Mouse bindings are active only while Sherlock is mapped; they never poll or query hyprctl. The helper validates the native peer PID/UID and preserves the loaded mode marker, so closing apps does not restart the service or rebuild results.

Evidence/backups: `~/.local/state/sherlock-migration/20261102/dismiss-fix/`. Live compositor callback checks covered 12 stable-PID toggle cycles, inside pass-through, same/other-monitor outside dismissal, visible config reload, emoji closure, Escape and synthetic history cancellation without changing the sink. These are callback/injected-Escape checks, not a claim of physical Meta/mouse verification. The prior burst/transition regressions still pass with 0% hidden CPU. Independent review remained unavailable; the exact diff was reviewed inline.

To undo only this correction, compare/restore `custom.lua` and `sherlock_ipc.py` from the dismissal backups if no later edits would be lost, then reload Hyprland. The unused new Lua module can remain after its require is removed. This preserves the earlier CPU-hang workaround.

## Rollback

The only pre-existing live files changed are `~/.config/hypr/scripts/launcher.sh`, `~/.config/hypr/custom.lua` (two bindings), and `~/.config/hypr/conf/autostart.lua` (one startup command). Their original content and permissions are recorded in `before.json` and `backups/`.

To undo immediately, compare those three files against their recorded backups, restore the originals only if no later edits would be discarded, stop `sherlock.service`, and reload Hyprland. Preserve symlinks by updating their resolved files. No Sherlock service enablement or package uninstallation is required: startup is owned by the one added Hyprland command. Rofi's files were not changed.

The native reset/readiness helper is on demand, not a daemon. Its startup check times out after 15 seconds and validates the peer PID/UID. Runtime mode state contains only the daemon PID and mode, not clipboard contents. The Meta-incident integration file backups and diffs are under `meta-fix/`; reverting to those old helpers would also restore the reproduced bug.
