# CachyOS Hyprland ML4W configs — refreshed 2026-10-13

Base: CachyOS + ML4W dotfiles stable 2.16 + kitty 0.49.2
Repo: https://github.com/orsnaro/My-Configs-Cmder.git, folder `conf_backups/cachyos_hyprland_ml4w/`

Source live paths are symlinks:
`~/.config/hypr|kitty|waybar|quickshell|rofi|swaync` -> `~/.mydotfiles/com.ml4w.dotfiles.stable/.config/...`

Layout here mirrors $HOME:
- `dotfiles/.config/...` (hypr, kitty, quickshell, waybar, rofi, swaync, ML4W source/settings/listeners/themes/assets/colors, ml4w-dock, ml4w-statusbar, fastfetch, declarative fish configuration)
- Appearance/launcher dependencies: matugen configuration/templates, walker, elephant, ohmyposh, hyprland-kde-overrides; GTK 3/4 `settings.ini`, `gtk.css`, and `colors.css` only.
- Calendar: `gcal-consent.py`, `gcal-sync.py`, `gcal-remind.py`, and tests only.
- `local/.local/bin/...` (hypr-*, glaze-*, qs-lazy-toggle, albion-data-watch/start; cemu-mousepad.py excluded)
- `local/.local/share/...` (ml4w-dock QML source, quickshell-overview, ml4w-dotfiles-settings, applications/quake-kitty.desktop)

Excluded: wallpapers, backup leftovers (`*.bak*`, `*-bak`, `backup-*/`), Python caches, `.git/`, `.github/`, private `.superpowers/`/`.opencode/` scratch, virtual environments, node_modules, `.env*`, OAuth credentials/tokens, and Fish's mutable `fish_variables` store. Intentional dock `docs/superpowers/` reports/plans and tests remain included. Calendar caches, notification state, GTK bookmarks and personal agenda data are not allowlisted.

Kitty source patch: `dotfiles/.config/kitty/patches/*.diff` + `apply-native-patch.sh`, requires sudo, version-pinned 0.49.2. See `KITTY_PATCH_STATE.txt`.

Dock QML (`local/.local/share/ml4w-dock/`) + quickshell QML are user-space source (plain copy, no sudo). Only kitty needs sudo re-patch.

Matugen regen (do not fight): `hypr/colors.conf`, `hypr/colors.lua`, `kitty/colors-matugen.conf`, `ml4w-dock/colors.json`.

Restore: `./RESTORE.sh [--dry-run]` — merges files without deleting unrelated destination files, preserves copied permissions, recreates the dock launcher link if absent, and prompts for the Kitty sudo patch. It **prints** the reload/relogin instruction; it does not reload the desktop automatically. Dry-run previews config, bin, and desktop-entry copies without writing files. Requires Bash and rsync with `--mkpath` support.
Re-backup: `./BACKUP.sh` — refreshes the allowlisted snapshot and manifest. Missing optional directories are skipped; real copy failures stop the script. Exclusions protect existing excluded snapshot files: review/remove old artifacts explicitly rather than using `--delete-excluded`.

## Current behavior

- Quake Kitty stays open and visible when GUI windows launch. The native `quake-apps-to-normal-workspace` rule sends non-Quake windows initially mapped on `special:quake` to `m+0 silent` (the normal workspace underneath); no wrapper, daemon, or polling.
- Mouse-follow focus remains enabled with `special_fallthrough = true`; `hide_special_on_workspace_change = false` keeps Quake visible while normal workspaces change.
- Dock press/hold reordering uses the current 250 ms threshold; gesture regressions and the implementation report are included.
- Includes current Kitty resize mappings, wallpaper automation/theming, calendar panel/helpers, Fastfetch network-usage query, and Walker/Elephant configuration.

## Restore prerequisites

- Install the applications/tools referenced by the configs separately (including Walker/Elephant, Matugen, Quickshell, Oh My Posh, and the Albion data client if used). This is a config/source backup, not a binary or package backup.
- Fish expects `~/.local/bin/oh-my-posh`; the Pomo module expects `~/.local/bin/pomo`. Install these separately or recreate their links; the current Pomo binary lives in an external repo.
- Calendar helpers require a fresh `~/.config/gcal/.venv` with `google-api-python-client`, `google-auth`, and `google-auth-oauthlib`. Supply your own `client_secret_*.json`, then run `~/.config/gcal/.venv/bin/python ~/.config/gcal/gcal-consent.py` to consent. Tokens, caches, and virtual environments are intentionally not restored.
- Obsidian's mounted vault and browser profiles are external and are not backed up here.

## Backup-script tests

`python3 -m unittest discover -s tests -v` runs both scripts against disposable homes under `/tmp/opencode` with real rsync. Component regressions live in their respective `tests/` directories; some GUI integrations require a dedicated session/terminal.

Snapshot validation on 2026-10-13: backup/restore fixtures, Hyprland, Kitty unit tests, wallpaper tests and offline calendar tests pass. **The full suite is not green:** the statusbar module-order assertion predates the microphone module, Fastfetch's historical baseline fixture is external/missing, and dock Wayland long-hold/timing checks fail. These are reported for separate investigation, not silently skipped; the backup PR is a draft.

## Directional navigation

Physical keys: J=left, L=right, I=up, K=down (US and Arabic layouts).

- `Alt+J/L/I/K`: Kitty panes first; at a pane edge, focus desktop windows, then adjacent monitors, including empty active workspaces. At the outer monitor edge, stop without wrapping.
- `Shift+Alt+J/L/I/K`: move desktop windows.
- `Ctrl+Shift+Alt+J/L/I/K`: focus desktop windows.
- `Ctrl+Alt+J/L/I/K`: resize Kitty panes; native resize mappings and the Python fallback remain unchanged.
- `Shift+Alt+arrows`: desktop window focus, unchanged.

Kitty receives the original event, not a synthetic forwarded shortcut. Its no-UI `smart-focus.py` focuses pane groups in-process and uses bounded local Hyprland IPC only at an edge. `checked_focus` also handles empty desktops; PID/address guards reject stale Kitty requests. No watcher, polling, parity filter or navigation subprocess is needed.

## Caveats

- Restore targets `$HOME` only (no alternate target dir); base required: CachyOS + ML4W dotfiles stable 2.16.
- `hypr/monitors.conf` + `custom.lua` workspaces hardcode a 3-monitor layout (DP-2/HDMI-A-2/DP-1) — adjust for single-display machines.
- Matugen overwrites `hypr/colors.*`, `kitty/colors-matugen.conf`, `ml4w-dock/colors.json` on theme change; these copies are a snapshot.
- `kitty/patches/ors-*-tabs-before-no-neighbors.diff` is a superseded single-hunk iteration, kept for reference; the applier uses `tabs.diff` + `utils.diff` only.
- Excluded on purpose: game/tool binaries (`albiondata-client`, `fetch`, `obsidian*`), `cemu-mousepad.py`, `*.bak` leftovers.
