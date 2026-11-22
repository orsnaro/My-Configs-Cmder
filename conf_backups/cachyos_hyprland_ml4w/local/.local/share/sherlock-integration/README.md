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

## Emoji usage ordering — 2026-11-03

Super+period keeps the native grid, with **most-used emoji first and most-recent selection breaking ties**. Typing uses the existing search/filter/scorer; clearing the query restores usage order. Unused emoji retain their original order. Only explicit selections count, with skin-tone choices grouped under their base emoji. Browsing, searching and cancellation do not count. Learning starts with new selections; clipboard history is never inspected or imported.

`emoji-usage.patch` changes four Rust source files in Sherlock **v0.1.14-3**, adding no dependencies, service, process, watcher, timer, thread or resident history table. History is read only on grid creation/selection and atomically saved only on selection. Ordering precedes the existing 77-result filter so a previously used emoji anywhere in the dataset can reach the first row. Nonempty-query matching/scoring, wrappers, shortcuts and the service unit are unchanged.

The private history is `$XDG_DATA_HOME/sherlock/emoji-usage.json` (normally `~/.local/share/sherlock/emoji-usage.json`; upstream's existing `~/.sherlock` directory takes precedence if present). Missing/corrupt history falls back to the original order; write failure does not block selection. To reset, close the picker and move that file aside. No history, binary, machine-local build record or rollback snapshot is published here.

### Rebuild and install manually

`RESTORE.sh` copies the patch; it does **not** download, compile or install Sherlock. The official binary documented in `CURRENT-RESTORE.md` remains an unpatched fallback. `provenance.json` continues to describe that official binary, not this locally modified build. This patch targets upstream GPL-3.0 source; retain the upstream `LICENSE` in the build checkout.

After restoring these integration files, install Rust/Cargo, a C linker, `glib-compile-resources` and the GTK4/layer-shell development dependencies required by the pinned upstream source. Build in a fresh directory; the commit check prevents applying against a moved tag. The nine added tests use disposable fixtures below `/tmp/opencode`:

```bash
mkdir -p /tmp/opencode
build_dir=$(mktemp -d /tmp/opencode/sherlock-emoji-build.XXXXXXXX)
git clone --depth 1 --branch v0.1.14-3 https://github.com/Skxxtz/sherlock.git "$build_dir"
cd "$build_dir"
test "$(git rev-parse HEAD)" = 93afa10ce1be2b83ac33d7eee6f4943b38b33422 || exit 1
git switch -c feat/emoji-usage-order
git apply --check "$HOME/.local/share/sherlock-integration/emoji-usage.patch"
git apply "$HOME/.local/share/sherlock-integration/emoji-usage.patch"
CARGO_BUILD_JOBS=2 RUSTFLAGS='-C linker=/usr/bin/cc' nice -n 10 cargo test --locked
CARGO_BUILD_JOBS=2 RUSTFLAGS='-C linker=/usr/bin/cc' nice -n 10 cargo build --release --locked
```

Only after both commands succeed, install over an existing working Sherlock setup. Back up the current executable and atomically replace it; do not overwrite a running executable in place:

```bash
mkdir -p "$HOME/.local/state" "$HOME/.local/bin"
backup_dir=$(mktemp -d "$HOME/.local/state/sherlock-emoji-usage.XXXXXXXX")
cp -p -- "$HOME/.local/bin/sherlock" "$backup_dir/sherlock.original"
printf 'Original executable backup: %s\n' "$backup_dir/sherlock.original"
staged=$(mktemp "$HOME/.local/bin/.sherlock-emoji.XXXXXXXX")
install -m755 target/release/sherlock "$staged"
mv -T -- "$staged" "$HOME/.local/bin/sherlock"
systemctl --user restart sherlock.service
```

Keep the printed/saved `backup_dir` path. To undo, stop the existing service, restore that `sherlock.original` to `~/.local/bin/sherlock`, and start the same service. Compare digests before restoring so later changes are not overwritten. The history file can remain inert; no shortcut/configuration rollback is needed.

Verification of this exact patch: **10 native tests** (nine new), the existing **36 Python integration tests**, and Lua toggle/hit-test/lifecycle checks passed. The installed binary passed isolated GUI checks for frequency/recency ordering, search/clear, restart persistence, default/tone selection and cancellation; synthetic XDG data and the existing runtime field override prevented personal clipboard access. Four emoji/app transitions, synthetic history cancellation and forty stable-PID app reopen cycles passed before/after. Short hidden-idle CPU samples were 0% in both builds; this is not a zero-memory/activation-cost guarantee. Review was inline because the configured free reviewer quota was exhausted. No physical shortcut or reboot test is claimed.
