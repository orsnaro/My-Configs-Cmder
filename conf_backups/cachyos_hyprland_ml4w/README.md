# CachyOS Hyprland ML4W configs — navigation update 2026-10-07

Base: CachyOS + ML4W dotfiles stable 2.16 + kitty 0.49.2
Repo: https://github.com/orsnaro/My-Configs-Cmder.git, folder `cachyos_hyprland_ml4w/`

Source live paths are symlinks:
`~/.config/hypr|kitty|waybar|quickshell|rofi|swaync` -> `~/.mydotfiles/com.ml4w.dotfiles.stable/.config/...`

Layout here mirrors $HOME:
- `dotfiles/.config/...` (hypr, kitty, quickshell, waybar, rofi, swaync, ml4w/scripts+settings, ml4w-dock, ml4w-statusbar, fastfetch, fish)
- `local/.local/bin/...` (hypr-*, qs-lazy-toggle; cemu-mousepad.py excluded)
- `local/.local/share/...` (ml4w-dock QML source, quickshell-overview, ml4w-dotfiles-settings, applications/quake-kitty.desktop)

Excluded: `ml4w/wallpapers/` (209M), `__pycache__/`, `*.pyc`, `kitty/patches/backup-*/` full copies.

Kitty source patch: `dotfiles/.config/kitty/patches/*.diff` + `apply-native-patch.sh`, requires sudo, version-pinned 0.49.2. See `KITTY_PATCH_STATE.txt`.

Dock QML (`local/.local/share/ml4w-dock/`) + quickshell QML are user-space source (plain copy, no sudo). Only kitty needs sudo re-patch.

Matugen regen (do not fight): `hypr/colors.conf`, `hypr/colors.lua`, `kitty/colors-matugen.conf`, `ml4w-dock/colors.json`.

Restore: `./RESTORE.sh [--dry-run]` — copies back, `chmod +x *.sh/*.py`, prompts for kitty sudo patch, then `hyprctl reload`.
Re-backup: `./BACKUP.sh`

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
